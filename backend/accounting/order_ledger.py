from decimal import Decimal

from django.db import transaction
from django.db.models import Sum

from .models import Account, JournalEntry, JournalLine, Wallet
from .services_v2 import account_balance, ensure_chart, ensure_wallet, post_entry


def _money(value):
    return Decimal(str(value or "0")).quantize(Decimal("0.01"))


def _release_key(vendor_order_id, suffix):
    return f"vendor-order:release:{vendor_order_id}:{suffix}"


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


def released_vendor_amount(vendor_order_id):
    wallet_kinds = Wallet.Kinds.VENDOR_AVAILABLE
    entries = JournalEntry.objects.filter(source_type="vendor_order_release", source_id=str(vendor_order_id), status=JournalEntry.Status.POSTED)
    account_ids = list(Wallet.objects.filter(kind=wallet_kinds, account__journal_lines__entry__in=entries).values_list("account_id", flat=True).distinct())
    if not account_ids:
        return Decimal("0.00")
    return _money(JournalLine.objects.filter(entry__in=entries, account_id__in=account_ids).aggregate(total=Sum("credit"))["total"])


def item_release_exists(vendor_order_id, item_id):
    return JournalEntry.objects.filter(
        idempotency_key=_release_key(vendor_order_id, f"item:{item_id}"),
        status=JournalEntry.Status.POSTED,
    ).exists()


def refunded_item_net(item_id):
    entries = JournalEntry.objects.filter(source_type="order_item_refund", source_id=str(item_id), status=JournalEntry.Status.POSTED)
    if not entries.exists():
        return Decimal("0.00")
    amount = JournalLine.objects.filter(entry__in=entries, account__party_type__startswith="wallet:vendor_available").aggregate(total=Sum("debit"))["total"]
    pending_amount = JournalLine.objects.filter(entry__in=entries, account__party_type__startswith="wallet:vendor_pending").aggregate(total=Sum("debit"))["total"]
    return _money((amount or 0) + (pending_amount or 0))


def order_item_refunded(item_id):
    return JournalEntry.objects.filter(source_type="order_item_refund", source_id=str(item_id), status=JournalEntry.Status.POSTED).exists()


def _item_refund_entry(order, item, *, created_by=None):
    customer = ensure_wallet(order.customer, Wallet.Kinds.CUSTOMER, order.currency)
    vendor_user = item.vendor.owner
    released = item_release_exists(item.vendor_order_id, item.id)
    vendor_kind = Wallet.Kinds.VENDOR_AVAILABLE if released else Wallet.Kinds.VENDOR_PENDING
    vendor_wallet = ensure_wallet(vendor_user, vendor_kind, order.currency)
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
def refund_order_item(order, item, *, created_by=None):
    return _item_refund_entry(order, item, created_by=created_by)


@transaction.atomic
def reverse_order_funding(order, *, created_by=None, reason="عكس تمويل الطلب"):
    original = JournalEntry.objects.filter(idempotency_key=f"order:fund:{order.pk}", status=JournalEntry.Status.POSTED).prefetch_related("lines__account").first()
    if not original:
        return None
    key = f"order:fund-reversal:{order.pk}"
    if JournalEntry.objects.filter(idempotency_key=key).exists():
        return JournalEntry.objects.get(idempotency_key=key)
    lines = []
    for line in original.lines.all():
        if line.debit > 0:
            lines.append({"account": line.account, "credit": line.debit, "description": f"عكس القيد {original.number}"})
        elif line.credit > 0:
            lines.append({"account": line.account, "debit": line.credit, "description": f"عكس القيد {original.number}"})
    return post_entry(
        f"{reason} {order.order_number}",
        lines,
        source_type="order_funding_reversal",
        source_id=order.pk,
        idempotency_key=key,
        created_by=created_by,
        metadata={"reversal_of": original.number, "order_id": order.pk, "currency": order.currency},
    )


def order_downstream_journals_exist(order):
    return JournalEntry.objects.filter(
        status=JournalEntry.Status.POSTED,
    ).filter(
        source_type__in=["vendor_order_release", "order_item_refund"],
        source_id__in=[str(order.id)] + [str(v.id) for v in order.vendor_orders.all()],
    ).exists() or JournalEntry.objects.filter(source_type="order_item_refund", source_id__in=[str(i.id) for i in order.items.all()]).exists()


def release_order_remaining(order, *, created_by=None):
    released_entries = 0
    for vendor_order in order.vendor_orders.select_related("vendor__owner").all():
        item_ids = list(vendor_order.items.values_list("order_item_id", flat=True))
        target = _money(vendor_order.vendor_net)
        refunded_net = sum((refunded_item_net(item_id) for item_id in item_ids), Decimal("0.00"))
        already_released = Decimal("0.00")
        for item_id in item_ids:
            if item_release_exists(vendor_order.id, item_id):
                item = vendor_order.items.select_related("order_item").get(order_item_id=item_id).order_item
                already_released += _money(item.vendor_net)
        residual = max(Decimal("0.00"), target - already_released - refunded_net)
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
            released_entries += 1 if entry else 0
    return released_entries


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
    release_order_remaining(order, created_by=created_by)
    return released
