from decimal import Decimal

from django.db import transaction

from .models import JournalEntry, JournalLine, Wallet
from .services_v2 import account_balance, ensure_chart, ensure_wallet, post_entry


def _money(value):
    return Decimal(str(value or "0")).quantize(Decimal("0.01"))


def _release_key(vendor_order_id, suffix):
    return f"vendor-order:release:{vendor_order_id}:{suffix}"


def _fund_order_lines(order):
    from orders.models import VendorOrder

    customer = ensure_wallet(order.customer, Wallet.Kinds.CUSTOMER, order.currency)
    vendor_orders = list(VendorOrder.objects.select_related("vendor__owner").filter(order=order).order_by("id"))
    order_total = _money(order.total)
    lines = [{"account": customer.account, "debit": order_total, "description": f"خصم/حجز طلب {order.order_number}"}]
    allocated = Decimal("0.00")
    commission = Decimal("0.00")
    for vendor_order in vendor_orders:
        net = _money(vendor_order.vendor_net)
        commission += _money(vendor_order.commission)
        allocated += net
        if net > 0:
            pending = ensure_wallet(vendor_order.vendor.owner, Wallet.Kinds.VENDOR_PENDING, order.currency)
            lines.append({"account": pending.account, "credit": net, "description": f"مستحق معلق للطلب {vendor_order.order_number}"})
    if commission > 0:
        lines.append({"account": ensure_chart()["commission_income"], "credit": commission, "description": f"عمولة طلب {order.order_number}"})
    if allocated + commission != order_total:
        raise ValueError(f"لا يمكن ترحيل الطلب محاسبيًا: صافي التاجر {allocated} + العمولة {commission} != إجمالي الطلب {order_total}.")
    return lines


def fund_order_revision(order, revision, *, created_by=None):
    key = f"order:fund:{order.pk}:revision:{int(revision)}"
    existing = JournalEntry.objects.filter(idempotency_key=key).first()
    if existing:
        return existing
    return post_entry(
        f"إعادة تمويل الطلب {order.order_number} - تعديل {revision}",
        _fund_order_lines(order),
        source_type="order",
        source_id=order.pk,
        idempotency_key=key,
        created_by=created_by,
        metadata={"order_total": str(_money(order.total)), "currency": order.currency, "revision": int(revision)},
    )


def release_vendor_amount(vendor_user, amount, currency, *, vendor_order_id, release_key, item_ids=None, created_by=None):
    amount = _money(amount)
    if amount <= 0:
        return None
    pending = ensure_wallet(vendor_user, Wallet.Kinds.VENDOR_PENDING, currency)
    available = ensure_wallet(vendor_user, Wallet.Kinds.VENDOR_AVAILABLE, currency)
    if account_balance(pending.account) < amount:
        raise ValueError("الرصيد المعلق للتاجر غير كافٍ لإتمام التسوية.")
    return post_entry(
        f"إطلاق مستحقات الطلب {vendor_order_id}",
        [
            {"account": pending.account, "debit": amount, "description": f"تسوية الطلب {vendor_order_id}"},
            {"account": available.account, "credit": amount, "description": f"إضافة المستحق المتاح {vendor_order_id}"},
        ],
        source_type="vendor_order_release",
        source_id=vendor_order_id,
        idempotency_key=_release_key(vendor_order_id, release_key),
        created_by=created_by,
        metadata={"vendor_order_id": vendor_order_id, "amount": str(amount), "item_ids": [int(x) for x in (item_ids or [])]},
    )


def item_release_exists(vendor_order_id, item_id):
    return JournalEntry.objects.filter(
        idempotency_key=_release_key(vendor_order_id, f"item:{item_id}"),
        status=JournalEntry.Status.POSTED,
    ).exists()


def refunded_item_net(item_id):
    entries = JournalEntry.objects.filter(source_type="order_item_refund", source_id=str(item_id), status=JournalEntry.Status.POSTED).prefetch_related("lines__account")
    total = Decimal("0.00")
    for entry in entries:
        for line in entry.lines.all():
            if line.account.party_type in {"wallet:vendor_available", "wallet:vendor_pending"}:
                total += _money(line.debit)
    return _money(total)


def order_item_refunded(item_id):
    return JournalEntry.objects.filter(source_type="order_item_refund", source_id=str(item_id), status=JournalEntry.Status.POSTED).exists()


def refund_order_item(order, item, *, created_by=None):
    customer = ensure_wallet(order.customer, Wallet.Kinds.CUSTOMER, order.currency)
    vendor_kind = Wallet.Kinds.VENDOR_AVAILABLE if item_release_exists(item.vendor_order_id, item.id) else Wallet.Kinds.VENDOR_PENDING
    vendor_wallet = ensure_wallet(item.vendor.owner, vendor_kind, order.currency)
    vendor_net = _money(item.vendor_net)
    commission = _money(item.commission)
    refund = _money(item.vendor_total)
    if vendor_net + commission != refund:
        raise ValueError("بيانات القطعة لا تتطابق محاسبيًا مع قيمتها المستردة.")
    return post_entry(
        f"استرداد قطعة من الطلب {order.order_number}",
        [
            {"account": vendor_wallet.account, "debit": vendor_net, "description": f"عكس مستحق القطعة {item.id}"},
            {"account": ensure_chart()["commission_income"], "debit": commission, "description": f"عكس عمولة القطعة {item.id}"},
            {"account": customer.account, "credit": refund, "description": f"إعادة قيمة القطعة {item.id} للعميل"},
        ],
        source_type="order_item_refund",
        source_id=item.id,
        idempotency_key=f"order:item-refund:{item.id}",
        created_by=created_by,
        metadata={"order_id": order.id, "order_item_id": item.id, "vendor_wallet_kind": vendor_kind, "refund": str(refund)},
    )


@transaction.atomic
def reverse_funding_journal(order, entry, *, created_by=None, reason="عكس تمويل الطلب"):
    if not entry:
        return None
    key = f"order:fund-reversal:{order.pk}:{entry.id}"
    existing = JournalEntry.objects.filter(idempotency_key=key).first()
    if existing:
        return existing
    lines = []
    for line in entry.lines.select_related("account").all():
        if line.debit > 0:
            lines.append({"account": line.account, "credit": line.debit, "description": f"عكس القيد {entry.number}"})
        elif line.credit > 0:
            lines.append({"account": line.account, "debit": line.credit, "description": f"عكس القيد {entry.number}"})
    return post_entry(
        f"{reason} {order.order_number}",
        lines,
        source_type="order_funding_reversal",
        source_id=order.pk,
        idempotency_key=key,
        created_by=created_by,
        metadata={"reversal_of": entry.number, "order_id": order.pk, "currency": order.currency},
    )


def current_funding_journal(order):
    metadata = order.metadata or {}
    number = ((metadata.get("accounting_funding") or {}).get("journal"))
    if number:
        entry = JournalEntry.objects.filter(number=number, status=JournalEntry.Status.POSTED).first()
        if entry:
            return entry
    return JournalEntry.objects.filter(source_type="order", source_id=str(order.pk), status=JournalEntry.Status.POSTED).order_by("-id").first()


def reverse_current_funding(order, *, created_by=None, reason="عكس تمويل الطلب"):
    entry = current_funding_journal(order)
    return reverse_funding_journal(order, entry, created_by=created_by, reason=reason)


def order_has_settlements(order):
    item_ids = [str(x) for x in order.items.values_list("id", flat=True)]
    vendor_order_ids = [str(x) for x in order.vendor_orders.values_list("id", flat=True)]
    return JournalEntry.objects.filter(
        status=JournalEntry.Status.POSTED,
        source_type__in=["vendor_order_release", "order_item_refund"],
        source_id__in=vendor_order_ids + item_ids,
    ).exists()


def release_order_items(order, *, created_by=None):
    released = Decimal("0.00")
    for vendor_order in order.vendor_orders.select_related("vendor__owner").all():
        for link in vendor_order.items.select_related("order_item").all():
            item = link.order_item
            if order_item_refunded(item.id) or item_release_exists(vendor_order.id, item.id):
                continue
            amount = _money(item.vendor_net)
            if amount <= 0:
                continue
            entry = release_vendor_amount(
                vendor_order.vendor.owner,
                amount,
                vendor_order.currency,
                vendor_order_id=vendor_order.id,
                release_key=f"item:{item.id}",
                item_ids=[item.id],
                created_by=created_by,
            )
            if entry:
                released += amount
        target = _money(vendor_order.vendor_net)
        released_by_items = sum(
            (_money(link.order_item.vendor_net) for link in vendor_order.items.select_related("order_item").all() if item_release_exists(vendor_order.id, link.order_item.id)),
            Decimal("0.00"),
        )
        refunded_net = sum((refunded_item_net(link.order_item.id) for link in vendor_order.items.select_related("order_item").all()), Decimal("0.00"))
        residual = max(Decimal("0.00"), target - released_by_items - refunded_net)
        if residual > 0:
            entry = release_vendor_amount(
                vendor_order.vendor.owner,
                residual,
                vendor_order.currency,
                vendor_order_id=vendor_order.id,
                release_key="residual",
                item_ids=[],
                created_by=created_by,
            )
            if entry:
                released += residual
    return released
