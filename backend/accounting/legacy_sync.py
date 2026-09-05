from decimal import Decimal

from django.db import transaction

from finance.models import VendorPayout

from .models import JournalEntry, Wallet
from .services_v2 import ensure_chart, ensure_wallet, post_entry


@transaction.atomic
def sync_vendor_pending(user, currency="YER"):
    """Mirror only pre-accounting pending payouts into the accounting pending wallet."""
    wallet = ensure_wallet(user, Wallet.Kinds.VENDOR_PENDING, currency)
    payouts = VendorPayout.objects.select_related("vendor", "vendor__owner", "order").filter(vendor__owner=user, currency=currency, status="pending")
    for payout in payouts:
        # New accounting-backed orders already have a real pending journal; never mirror them as opening balances.
        if payout.order_id and (payout.order.metadata or {}).get("accounting_funding"):
            continue
        key = f"legacy:vendor-pending:{payout.id}"
        amount = Decimal(payout.amount).quantize(Decimal("0.01"))
        if amount <= 0 or JournalEntry.objects.filter(idempotency_key=key).exists():
            continue
        post_entry(
            f"ترحيل مستحق معلق سابق للطلب {payout.vendor_order_id or payout.order_id}",
            [
                {"account": ensure_chart()["opening_equity"], "debit": amount},
                {"account": wallet.account, "credit": amount},
            ],
            source_type="legacy_vendor_pending",
            source_id=payout.id,
            idempotency_key=key,
            metadata={"legacy_payout_id": payout.id, "order_id": payout.order_id, "vendor_order_id": payout.vendor_order_id, "currency": currency},
        )
    return wallet
