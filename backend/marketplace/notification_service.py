from .models import Notification

class NotificationService:
    @staticmethod
    def send_order_status_update(order):
        title = f"تحديث طلب #{order.order_number}"
        body = f"تغيرت حالة طلبك إلى: {order.get_status_display()}"
        
        Notification.objects.create(
            recipient=order.customer,
            title=title,
            body=body,
            audience={"type": "ORDER_STATUS_CHANGED", "order_id": order.id, "order_number": order.order_number}
        )
        
        # إشعار للتجار المرتبطين بالطلب
        vendors = set(item.vendor.owner for item in order.items.select_related("vendor__owner"))
        for vendor_owner in vendors:
            Notification.objects.create(
                recipient=vendor_owner,
                title=f"تحديث طلب #{order.order_number}",
                body=f"تغيرت حالة الطلب إلى: {order.get_status_display()}",
                audience={"type": "VENDOR_ORDER_UPDATE", "order_id": order.id}
            )
