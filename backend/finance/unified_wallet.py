from decimal import Decimal

from django.db import transaction

from accounting.models import Account, Wallet as AccountingWallet
from accounting.services_v2 import ensure_chart, ensure_wallet as ensure_accounting_wallet, post_entry, wallet_balance

from .models import Wallet, WalletTransaction


ADJUSTMENT_ACCOUNT_CODE = "700104"


def sync_customer_projection(user, currency="YER"):
    """Keep the legacy finance wallet aligned with the accounting wallet.

    Accounting is the source of truth. The finance wallet is a compatibility
    projection used by older client screens and APIs.
    """
    currency = str(currency or "YER").upper()
    accounting_wallet = ensure_accounting_wallet(user, AccountingWallet.Kinds.CUSTOMER, currency)
    balance = wallet_balance(accounting_wallet).quantize(Decimal("0.01"))
    projection, _ = Wallet.objects.get_or_create(
        user=user,
        defaults={"currency": currency, "balance": balance},
    )
    if projection.currency != currency:
        projection.currency = currency
    if projection.balance != balance:
        projection.balance = balance
    projection.save(update_fields=["currency", "balance", "updated_at"])
    return projection


def _adjustment_account():
    chart = ensure_chart()
    account, _ = Account.objects.get_or_create(
        code=ADJUSTMENT_ACCOUNT_CODE,
        defaults={
            "name": "تسويات أرصدة العملاء",
            "parent": chart["expense"],
            "account_type": Account.Types.EXPENSE,
            "normal_side": Account.NormalSides.DEBIT,
            "is_group": False,
            "metadata": {"domain": "finance", "purpose": "customer_wallet_adjustment"},
        },
    )
    return account


@transaction.atomic
def adjust_customer_wallet(user, amount, currency="YER", *, reference="", note="", transaction_type="adjustment", created_by=None):
    amount = Decimal(str(amount)).quantize(Decimal("0.01"))
    if amount == 0:
        raise ValueError("المبلغ يجب ألا يساوي صفرًا.")
    currency = str(currency or "YER").upper()
    accounting_wallet = ensure_accounting_wallet(user, AccountingWallet.Kinds.CUSTOMER, currency)
    account = accounting_wallet.account.__class__.objects.select_for_update().get(pk=accounting_wallet.account_id)
    adjustment = _adjustment_account()
    if amount > 0:
        lines = [
            {"account": adjustment, "debit": amount, "description": "تعديل موجب لرصيد العميل"},
            {"account": account, "credit": amount, "description": "زيادة رصيد محفظة العميل"},
        ]
    else:
        absolute = -amount
        if wallet_balance(accounting_wallet) < absolute:
            raise ValueError("الرصيد المحاسبي غير كافٍ للتعديل السالب.")
        lines = [
            {"account": account, "debit": absolute, "description": "خفض رصيد محفظة العميل"},
            {"account": adjustment, "credit": absolute, "description": "تسوية سالبة لرصيد العميل"},
        ]
    entry = post_entry(
        note or "تسوية رصيد العميل",
        lines,
        source_type="customer_wallet_adjustment",
        source_id=str(user.pk),
        idempotency_key=f"wallet-adjustment:{user.pk}:{currency}:{reference}" if reference else None,
        created_by=created_by or user,
        metadata={"user_id": user.pk, "currency": currency, "amount": str(amount), "reference": reference},
    )
    projection = sync_customer_projection(user, currency)
    WalletTransaction.objects.create(
        wallet=projection,
        transaction_type=transaction_type,
        amount=amount,
        balance_after=projection.balance,
        reference=reference,
        note=note,
        metadata={"accounting_journal": entry.number, "source_type": "customer_wallet_adjustment"},
    )
    return entry, projection


@transaction.atomic
def record_customer_projection_transaction(user, amount, currency="YER", *, transaction_type, reference="", note="", metadata=None):
    """Record a compatibility WalletTransaction after an accounting operation."""
    projection = sync_customer_projection(user, currency)
    return WalletTransaction.objects.create(
        wallet=projection,
        transaction_type=transaction_type,
        amount=Decimal(str(amount)).quantize(Decimal("0.01")),
        balance_after=projection.balance,
        reference=reference,
        note=note,
        metadata=metadata or {},
    )
