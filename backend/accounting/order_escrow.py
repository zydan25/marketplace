from decimal import Decimal

from django.db import transaction

from .models import Account, JournalEntry, Wallet
from .services_v2 import account_balance, ensure_chart, ensure_wallet, post_entry, wallet_balance, fund_order


COMMISSION_ACCOUNT_CODE = "600001"


def _commission_account():
    return ensure_chart()["commission_income"]


def fund_marketplace_order(order, *, created_by=None):
    return fund_order(order, created_by=created_by)


@transaction.atomic
def adjust_order_funding(order, previous_vendor_net, previous_commission, *, source_id, created_by=None):
    previous_vendor_net = {int(k): Decimal(str(v)).quantize(Decimal("0.01")) for k, v in (previous_vendor_net or {}).items()}
    previous_commission = Decimal(str(previous_commission or "0.00")).quantize(Decimal("0.01"))
    customer_wallet = ensure_wallet(order.customer, Wallet.Kinds.CUSTOMER, order.currency)
    customer = Account.objects.select_for_update().get(pk=customer_wallet.account_id)
    lines = []
    delta_total = Decimal("0.00")

    vendor_deltas = []
    for vendor_order in order.vendor_orders.select_for_update().select_related("vendor__owner").order_by("id"):
        old = previous_vendor_net.get(vendor_order.id, Decimal("0.00"))
        new = Decimal(vendor_order.vendor_net).quantize(Decimal("0.01"))
        delta = new - old
        if delta:
            pending = ensure_wallet(vendor_order.vendor.owner, Wallet.Kinds.VENDOR_PENDING, order.currency)
            vendor_deltas.append((pending.account_id, delta))
            delta_total += delta

    new_commission = sum((Decimal(v.commission).quantize(Decimal("0.01")) for v in order.vendor_orders.all()), Decimal("0.00"))
    commission_delta = new_commission - previous_commission
    delta_total += commission_delta

    if delta_total > 0:
        lines.append({"account": customer, "debit": delta_total, "description": f"زيادة حجز الطلب {order.order_number}"})
    elif delta_total < 0:
        lines.append({"account": customer, "credit": -delta_total, "description": f"تخفيض حجز الطلب {order.order_number}"})

    for account_id, delta in vendor_deltas:
        account = Account.objects.select_for_update().get(pk=account_id)
        if delta > 0:
            lines.append({"account": account, "credit": delta, "description": f"زيادة مستحقات التاجر للطلب {order.order_number}"})
        else:
            lines.append({"account": account, "debit": -delta, "description": f"خفض مستحقات التاجر للطلب {order.order_number}"})

    if commission_delta > 0:
        lines.append({"account": _commission_account(), "credit": commission_delta, "description": f"زيادة عمولة الطلب {order.order_number}"})
    elif commission_delta < 0:
        lines.append({"account": _commission_account(), "debit": -commission_delta, "description": f"خفض عمولة الطلب {order.order_number}"})

    if not lines:
        return None
    return post_entry(
        f"تعديل حجز الطلب {order.order_number}",
        lines,
        source_type="order_funding_adjustment",
        source_id=str(source_id),
        idempotency_key=f"order:funding-adjust:{order.pk}:{source_id}",
        created_by=created_by,
        metadata={"order_id": order.pk, "source_id": str(source_id), "currency": order.currency},
    )


@transaction.atomic
def release_vendor_amount(vendor_user, amount, currency, *, source_id, created_by=None):
    amount = Decimal(str(amount)).quantize(Decimal("0.01"))
    if amount <= 0:
        return None
    pending = ensure_wallet(vendor_user, Wallet.Kinds.VENDOR_PENDING, currency)
    available = ensure_wallet(vendor_user, Wallet.Kinds.VENDOR_AVAILABLE, currency)
    locked_pending = Account.objects.select_for_update().get(pk=pending.account_id)
    if account_balance(locked_pending) < amount:
        raise ValueError(f"رصيد مستحقات التاجر المعلقة غير كافٍ: المتاح {account_balance(locked_pending)} {currency} والمطلوب {amount}.")
    return post_entry(
        "إطلاق مستحقات التاجر من الحجز",
        [
            {"account": locked_pending, "debit": amount, "description": "خفض المستحق المعلق"},
            {"account": available.account, "credit": amount, "description": "إضافة إلى الرصيد المتاح للتاجر"},
        ],
        source_type="vendor_pending_release",
        source_id=str(source_id),
        idempotency_key=f"vendor-pending:release:{source_id}",
        created_by=created_by,
        metadata={"vendor_id": vendor_user.pk, "currency": currency, "amount": str(amount)},
    )


@transaction.atomic
def refund_disputed_item(order, item, *, created_by=None):
    gross = Decimal(item.vendor_total).quantize(Decimal("0.01"))
    net = Decimal(item.vendor_net).quantize(Decimal("0.01"))
    commission = (gross - net).quantize(Decimal("0.01"))
    if gross <= 0:
        raise ValueError("قيمة القطعة المراد استردادها غير صالحة.")
    pending = ensure_wallet(item.vendor.owner, Wallet.Kinds.VENDOR_PENDING, order.currency)
    customer = ensure_wallet(order.customer, Wallet.Kinds.CUSTOMER, order.currency)
    pending_account = Account.objects.select_for_update().get(pk=pending.account_id)
    customer_account = Account.objects.select_for_update().get(pk=customer.account_id)
    if account_balance(pending_account) < net:
        raise ValueError("لا يوجد رصيد مستحق معلق كافٍ لدى التاجر لإتمام استرداد القطعة؛ تم إيقاف العملية للمراجعة.")
    lines = [
        {"account": pending_account, "debit": net, "description": f"عكس مستحق قطعة {item.id}"},
    ]
    if commission > 0:
        lines.append({"account": _commission_account(), "debit": commission, "description": f"عكس عمولة قطعة {item.id}"})
    lines.append({"account": customer_account, "credit": gross, "description": f"إعادة قيمة القطعة {item.id} للعميل"})
    return post_entry(
        f"استرداد اعتراض القطعة {item.id} للطلب {order.order_number}",
        lines,
        source_type="order_item_dispute_refund",
        source_id=item.id,
        idempotency_key=f"dispute:item:refund:{item.id}",
        created_by=created_by,
        metadata={"order_id": order.pk, "order_item_id": item.id, "gross": str(gross), "net": str(net), "commission": str(commission)},
    )


@transaction.atomic
def reverse_order_funding(order, *, created_by=None):
    customer_wallet = ensure_wallet(order.customer, Wallet.Kinds.CUSTOMER, order.currency)
    customer = Account.objects.select_for_update().get(pk=customer_wallet.account_id)
    lines = []
    total = Decimal("0.00")
    for vendor_order in order.vendor_orders.select_for_update().select_related("vendor__owner").order_by("id"):
        amount = Decimal(vendor_order.vendor_net).quantize(Decimal("0.01"))
        if amount <= 0:
            continue
        pending = ensure_wallet(vendor_order.vendor.owner, Wallet.Kinds.VENDOR_PENDING, order.currency)
        pending_account = Account.objects.select_for_update().get(pk=pending.account_id)
        if account_balance(pending_account) < amount:
            raise ValueError("لا يمكن عكس حجز الطلب لأن مستحقات أحد التجار لم تعد معلقة بالكامل؛ تم إيقاف الرد الآلي.")
        lines.append({"account": pending_account, "debit": amount, "description": f"عكس مستحق طلب ملغي {order.order_number}"})
        total += amount
    commission = sum((Decimal(v.commission).quantize(Decimal("0.01")) for v in order.vendor_orders.all()), Decimal("0.00"))
    if commission > 0:
        lines.append({"account": _commission_account(), "debit": commission, "description": f"عكس عمولة طلب ملغي {order.order_number}"})
        total += commission
    if total <= 0:
        return None
    lines.append({"account": customer, "credit": total, "description": f"إعادة حجز الطلب {order.order_number} للعميل"})
    return post_entry(
        f"عكس تمويل الطلب {order.order_number}",
        lines,
        source_type="order_funding_reversal",
        source_id=order.pk,
        idempotency_key=f"order:funding-reversal:{order.pk}",
        created_by=created_by,
        metadata={"order_id": order.pk, "currency": order.currency, "amount": str(total)},
    )
