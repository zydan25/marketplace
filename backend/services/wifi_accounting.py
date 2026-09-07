from decimal import Decimal
from django.db import transaction
from accounting.models import Account, JournalEntry, Wallet
from accounting.services_v2 import ensure_chart, ensure_wallet, wallet_balance, post_entry


@transaction.atomic
def settle_wifi_sale(card, buyer, *, created_by=None):
    denomination = card.denomination
    network = denomination.network
    total = Decimal(denomination.sale_price).quantize(Decimal("0.01"))
    fee = (total * Decimal(network.management_percent) / Decimal("100")).quantize(Decimal("0.01"))
    owner_amount = (total - fee).quantize(Decimal("0.01"))
    if total <= 0 or owner_amount < 0 or fee < 0:
        raise ValueError("قيمة كرت الوايفاي غير صالحة.")
    if buyer.pk == network.owner_id:
        raise ValueError("لا يمكن شراء كرت من الشبكة التابعة لنفس حسابك.")

    buyer_wallet = ensure_wallet(buyer, Wallet.Kinds.CUSTOMER, "YER")
    owner_wallet = ensure_wallet(network.owner, Wallet.Kinds.CUSTOMER, "YER")
    buyer_account = Account.objects.select_for_update().get(pk=buyer_wallet.account_id)
    owner_account = Account.objects.select_for_update().get(pk=owner_wallet.account_id)
    if wallet_balance(buyer_wallet) < total:
        raise ValueError("رصيد العميل غير كافٍ لشراء الكرت.")

    chart = ensure_chart()
    revenue, _ = Account.objects.get_or_create(
        code="600102",
        defaults={
            "name": "إيرادات إدارة شبكات الوايفاي",
            "parent": chart["income"],
            "account_type": Account.Types.INCOME,
            "normal_side": Account.NormalSides.CREDIT,
            "is_group": False,
            "metadata": {"domain": "wifi", "purpose": "management_fee"},
        },
    )
    key = f"wifi:sale:{card.pk}"
    existing = JournalEntry.objects.filter(idempotency_key=key).first()
    if existing:
        return existing, owner_amount, fee

    lines = [{"account": buyer_account, "debit": total, "description": f"شراء كرت وايفاي {card.card_number}"}]
    if owner_amount > 0:
        lines.append({"account": owner_account, "credit": owner_amount, "description": "صافي مستحق صاحب الشبكة"})
    if fee > 0:
        lines.append({"account": revenue, "credit": fee, "description": "نسبة إدارة شبكة الوايفاي"})
    entry = post_entry(
        f"بيع كرت وايفاي {card.card_number}",
        lines,
        source_type="wifi_sale",
        source_id=str(card.pk),
        idempotency_key=key,
        created_by=created_by or buyer,
        metadata={"card_id": card.pk, "network_id": network.pk, "buyer_id": buyer.pk, "owner_id": network.owner_id, "amount": str(total), "fee": str(fee), "owner_amount": str(owner_amount), "currency": "YER"},
    )
    return entry, owner_amount, fee
