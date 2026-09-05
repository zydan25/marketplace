from decimal import Decimal

from django.db import transaction

from accounting.models import Account, JournalEntry, Wallet
from accounting.services_v2 import ensure_chart, ensure_wallet, wallet_balance, post_entry


def ensure_service_accounts():
    chart = ensure_chart()
    pending, _ = Account.objects.get_or_create(
        code="400901", defaults={"name": "تسويات الخدمات المعلقة", "parent": chart["suppliers"], "account_type": Account.Types.LIABILITY, "normal_side": Account.NormalSides.CREDIT, "is_group": False, "metadata": {"domain": "services", "purpose": "customer_reservation"}}
    )
    revenue, _ = Account.objects.get_or_create(
        code="600101", defaults={"name": "إيرادات الخدمات", "parent": chart["income"], "account_type": Account.Types.INCOME, "normal_side": Account.NormalSides.CREDIT, "is_group": False, "metadata": {"domain": "services"}}
    )
    return {"pending": pending, "revenue": revenue}


@transaction.atomic
def reserve_service_funds(service_transaction):
    amount = Decimal(service_transaction.customer_amount).quantize(Decimal("0.01"))
    customer_wallet = ensure_wallet(service_transaction.customer, Wallet.Kinds.CUSTOMER, service_transaction.currency)
    customer_wallet = Wallet.objects.select_for_update().select_related("account").get(pk=customer_wallet.pk)
    if wallet_balance(customer_wallet) < amount:
        raise ValueError("رصيد العميل غير كافٍ لتنفيذ الخدمة.")
    accounts = ensure_service_accounts()
    key = f"service:reserve:{service_transaction.id}"
    existing = JournalEntry.objects.filter(idempotency_key=key).first()
    if existing:
        return existing
    return post_entry(
        f"حجز مبلغ خدمة {service_transaction.service.code}",
        [{"account": customer_wallet.account, "debit": amount}, {"account": accounts["pending"], "credit": amount}],
        source_type="service_reservation", source_id=service_transaction.id, idempotency_key=key,
        created_by=service_transaction.customer, metadata={"service_transaction": str(service_transaction.id), "currency": service_transaction.currency},
    )


@transaction.atomic
def settle_service(service_transaction):
    amount = Decimal(service_transaction.customer_amount).quantize(Decimal("0.01"))
    accounts = ensure_service_accounts()
    key = f"service:settle:{service_transaction.id}"
    existing = JournalEntry.objects.filter(idempotency_key=key).first()
    if existing:
        return existing
    return post_entry(f"تسوية خدمة ناجحة {service_transaction.service.code}", [{"account": accounts["pending"], "debit": amount}, {"account": accounts["revenue"], "credit": amount}], source_type="service_settlement", source_id=service_transaction.id, idempotency_key=key, metadata={"service_transaction": str(service_transaction.id), "currency": service_transaction.currency})


@transaction.atomic
def refund_service(service_transaction):
    amount = Decimal(service_transaction.customer_amount).quantize(Decimal("0.01"))
    customer_wallet = ensure_wallet(service_transaction.customer, Wallet.Kinds.CUSTOMER, service_transaction.currency)
    accounts = ensure_service_accounts()
    key = f"service:refund:{service_transaction.id}"
    existing = JournalEntry.objects.filter(idempotency_key=key).first()
    if existing:
        return existing
    return post_entry(f"إعادة مبلغ خدمة فاشلة {service_transaction.service.code}", [{"account": accounts["pending"], "debit": amount}, {"account": customer_wallet.account, "credit": amount}], source_type="service_refund", source_id=service_transaction.id, metadata={"service_transaction": str(service_transaction.id), "currency": service_transaction.currency}, idempotency_key=key)
