from django.contrib import messages
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from communication.models import Conversation, Message
from orders.models import Order
from marketplace.dashboard import dashboard_access_required

ORDERS_URL = "/admin/dashboard/control/orders/"


def _ajax(request):
    return request.headers.get("X-Requested-With") == "XMLHttpRequest"


def _order(pk):
    return get_object_or_404(
        Order.objects.select_related("customer", "payment").prefetch_related(
            "items__product__categories",
            "items__vendor",
            "items__vendor__store_categories",
            "vendor_orders__vendor",
            "vendor_orders__items__order_item__product",
            "vendor_orders__shipment",
            "status_history__changed_by",
            "inventory_reservations__product",
            "inventory_reservations__variant",
            "conversation__messages__sender",
            "order_chats__vendor",
            "order_chats__vendor_order",
            "order_chats__messages__sender",
        ),
        pk=pk,
    )


@dashboard_access_required
@require_http_methods(["GET"])
def order_detail(request, order_id):
    import json
    order = _order(order_id)
    return render(request, "admin/control/inner/order_detail_v6.html", {
        "order": order,
        "chats": list(order.order_chats.all()),
        "conversation": getattr(order, "conversation", None),
        "shipping_address_json": json.dumps(order.shipping_address or {}, ensure_ascii=False, indent=2),
        "metadata_json": json.dumps(order.metadata or {}, ensure_ascii=False, indent=2),
        "statuses": Order._meta.get_field("status").choices,
    })


@dashboard_access_required
@require_http_methods(["GET", "POST"])
def order_customer_message(request, order_id):
    order = get_object_or_404(Order.objects.select_related("customer"), pk=order_id)
    if request.method == "POST":
        body = request.POST.get("body", "").strip()
        attachment = request.FILES.get("attachment")
        if not body and not attachment:
            messages.error(request, "اكتب رسالة أو أرفق صورة قبل الإرسال.")
        else:
            conversation, _ = Conversation.objects.get_or_create(
                order=order,
                defaults={"customer": order.customer, "subject": f"محادثة الطلب {order.order_number}"},
            )
            Message.objects.create(conversation=conversation, sender=request.user, body=body, attachment=attachment)
            conversation.is_closed = False
            conversation.save(update_fields=["is_closed", "updated_at"])
            messages.success(request, "تم إرسال الرسالة إلى محادثة العميل.")
    if _ajax(request):
        return order_detail(request, order.pk)
    return redirect(f"{ORDERS_URL}{order.pk}/detail/#customer-chat")
