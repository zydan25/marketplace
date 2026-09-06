from decimal import Decimal

from django.db import transaction

from accounting.models import Account, Wallet as AccountingWallet
from accounting.services_v2 import ensure_chart, ensure_wallet as ensure_accounting_wallet, post_entry, wallet_balance

from .models import Wallet, WalletTransaction


ADJUSTMENT_ACCOUNT_CODE = "500002"


def accounting_kind_for_user(user):
    return (
        AccountingWallet.Kinds.VENDOR_AVAILABLE
        if getattr(user, "role", None) == "vendor"
        else AccountingWallet.Kinds.CUSTOMER
    )


def sync_finance_projection(user, currency="YER"):
    currency = str(currency or "YER").upper()
    kind = accounting_kind_for_user(user)
    accounting_wallet = ensure_accounting_wallet(user, kind, currency)
    balance = wallet_balance(accounting_wallet).quantize(Decimal("0.01"))
    projection, _ = Wallet.objects.get_or_create(
        user=user,
        defaults={"currency": currency, "balance": balance},
    )
    changed = []
    if projection.currency != currency:
        projection.currency = currency
        changed.append("currency")
    if projection.balance != balance:
        projection.balance = balance
        changed.append("balance")
    if changed:
        changed.append("updated_at")
        projection._allow_projection_write = True
        projection.save(update_fields=changed)
    return projection


def sync_customer_projection(user, currency="YER"):
    return sync_finance_projection(user, currency)


def _adjustment_account():
    chart = ensure_chart()
    account, _ = Account.objects.get_or_create(
        code=ADJUSTMENT_ACCOUNT_CODE,
        defaults={
            "name": "تسويات أرصدة العملاء والتجار",
            "parent": chart["equity"],
            "account_type": Account.Types.EQUITY,
            "normal_side": Account.NormalSides.CREDIT,
            "is_group": False,
            "metadata": {"domain": "finance", "purpose": "wallet_adjustment"},
        },
    )
    return account


@transaction.atomic
def adjust_user_wallet(
    user,
    amount,
    currency="YER",
    *,
    reference="",
    note="",
    transaction_type=WalletTransaction.Types.ADJUSTMENT,
    created_by=None,
):
    amount = Decimal(str(amount)).quantize(Decimal("0.01"))
    currency = str(currency or "YER").upper()
    if amount == 0:
        raise ValueError("المبلغ يجب ألا يساوي صفرًا.")
    kind = accounting_kind_for_user(user)
    accounting_wallet = ensure_accounting_wallet(user, kind, currency)
    account = Account.objects.select_for_update().get(pk=accounting_wallet.account_id)
    adjustment = Account.objects.select_for_update().get(pk=_adjustment_account().pk)
    current = wallet_balance(accounting_wallet)

    if amount > 0:
        lines = [
            {"account": adjustment, "debit": amount, "description": "تسوية موجبة للرصيد"},
            {"account": account, "credit": amount, "description": "زيادة محفظة العميل/التاجر"},
        ]
    else:
        absolute = -amount
        if current < absolute:
            raise ValueError(f"الرصيد المحاسبي غير كافٍ للتعديل السالب: المتاح {current} {currency}.")
        lines = [
            {"account": account, "debit": absolute, "description": "خفض محفظة العميل/التاجر"},
            {"account": adjustment, "credit": absolute, "description": "تسوية سالبة للرصيد"},
        ]

    key = f"wallet-adjustment:{user.pk}:{currency}:{reference}" if reference else None
    entry = post_entry(
        note or "تسوية رصيد",
        lines,
        source_type="wallet_adjustment",
        source_id=str(user.pk),
        idempotency_key=key,
        created_by=created_by or user,
        metadata={
            "user_id": user.pk,
            "currency": currency,
            "amount": str(amount),
            "reference": reference,
            "wallet_kind": kind,
        },
    )
    projection = sync_finance_projection(user, currency)
    tx = projection.transactions.filter(reference=reference).order_by("-id").first() if reference else None
    if tx is None:
        tx = WalletTransaction.objects.create(
            wallet=projection,
            transaction_type=transaction_type,
            amount=amount,
            balance_after=projection.balance,
            reference=reference,
            note=note,
            metadata={"accounting_journal": entry.number, "source_type": "wallet_adjustment"},
        )
    return entry, projection, tx


def record_projection_transaction(user, amount, currency="YER", *, transaction_type, reference="", note="", metadata=None):
    projection = sync_finance_projection(user, currency)
    if reference:
        existing = projection.transactions.filter(reference=reference).order_by("-id").first()
        if existing:
            return existing
    return WalletTransaction.objects.create(
        wallet=projection,
        transaction_type=transaction_type,
        amount=Decimal(str(amount)).quantize(Decimal("0.01")),
        balance_after=projection.balance,
        reference=reference,
        note=note,
        metadata=metadata or {},
    )


def record_customer_projection_transaction(user, amount, currency="YER", *, transaction_type, reference="", note="", metadata=None):
    return record_projection_transaction(
        user, amount, currency,
        transaction_type=transaction_type,
        reference=reference,
        note=note,
        metadata=metadata,
    )
