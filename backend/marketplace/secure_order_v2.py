from django.db import transaction
from django.utils import timezone
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response

from .marketplace_models import InventoryReservation, Payment, Shipment
from .models import Order, OrderStatusHistory
from .secure_order_api import SecureOrderViewSet
from .serializers import OrderSerializer


class SecureOrderV2ViewSet(SecureOrderViewSet):
    @staticmethod
    def _sync_parent_status(order):
        statuses = list(order.vendor_orders.values_list("status", flat=True))
        if not statuses:
            return
        delivered = all(status == "delivered" for status in statuses)
        cancelled = all(status == "cancelled" for status in statuses)
        has_partial = any(status in {"delivered", "cancelled"} for status in statuses) and not delivered and not cancelled
        if delivered:
            parent = Order.Status.DELIVERED
        elif cancelled:
            parent = Order.Status.CANCELLED
        elif has_partial:
            parent = Order.Status.PARTIALLY_FULFILLED
        elif any(status == "shipped" for status in statuses):
            parent = Order.Status.SHIPPED
        elif any(status == "processing" for status in statuses):
            parent = Order.Status.PROCESSING
        elif any(status == "confirmed" for status in statuses):
            parent = Order.Status.CONFIRMED
        else:
            parent = Order.Status.PENDING
        if order.status != parent:
            old_status = order.status
            order.status = parent
            order.save(update_fields=["status", "updated_at"])
            OrderStatusHistory.objects.create(order=order, old_status=old_status, new_status=parent, changed_by=None)

    @action(detail=True, methods=["post"])
    @transaction.atomic
    def update_status(self, request, pk=None):
        order = self.get_object()
        user = request.user
        new_status = str(request.data.get("status", ""))

        if user.role == "vendor":
            vendor_order = order.vendor_orders.filter(vendor__owner=user).select_for_update().first()
            if not vendor_order:
                raise PermissionDenied("لا تملك هذا الطلب")
            if new_status in {"shipped", "delivered"} and order.payment_method != "cash_on_delivery" and getattr(getattr(order, "payment", None), "status", None) != Payment.Status.PAID:
                raise ValidationError({"status": "لا يمكن شحن الطلب قبل تأكيد الدفع"})
            if new_status not in {"confirmed", "processing", "shipped", "delivered", "cancelled"}:
                raise ValidationError({"status": "حالة التاجر غير صالحة"})

            old_status = vendor_order.status
            vendor_order.status = new_status
            vendor_order.save(update_fields=["status", "updated_at"])

            if new_status == "delivered" and old_status != "delivered":
                self._commit_vendor_order_inventory(vendor_order)
                shipment = getattr(vendor_order, "shipment", None)
                if shipment:
                    shipment.status = Shipment.Status.DELIVERED
                    shipment.delivered_at = timezone.now()
                    shipment.save(update_fields=["status", "delivered_at", "updated_at"])

                if order.payment_method == "cash_on_delivery":
                    all_delivered = all(status == "delivered" for status in order.vendor_orders.exclude(pk=vendor_order.pk).values_list("status", flat=True))
                    payment = order.payment
                    if all_delivered:
                        payment.status = Payment.Status.PAID
                        payment.paid_at = timezone.now()
                        payment.save(update_fields=["status", "paid_at", "updated_at"])
                        order.payment_status = "paid"
                        order.save(update_fields=["payment_status", "updated_at"])

            self._sync_parent_status(order)
            return Response({"vendor_order_id": vendor_order.id, "status": vendor_order.status, "order_status": order.status})

        if not (user.is_staff or user.role == "admin"):
            raise PermissionDenied("لا تملك صلاحية تغيير حالة الطلب")
        if new_status not in {choice.value for choice in Order.Status}:
            raise ValidationError({"status": "حالة الطلب غير صالحة"})

        old_status = order.status
        order.status = new_status
        order.save(update_fields=["status", "updated_at"])
        OrderStatusHistory.objects.create(order=order, old_status=old_status, new_status=new_status, changed_by=user)

        if new_status == Order.Status.CANCELLED:
            for reservation in order.inventory_reservations.select_for_update().filter(status__in=[InventoryReservation.Status.ACTIVE, InventoryReservation.Status.COMMITTED]):
                if reservation.variant_id:
                    variant = reservation.variant
                    if reservation.status == InventoryReservation.Status.ACTIVE:
                        variant.reserved_stock = max(0, variant.reserved_stock - reservation.quantity)
                    else:
                        variant.stock += reservation.quantity
                    variant.save(update_fields=["reserved_stock", "stock", "updated_at"])
                elif reservation.product_id:
                    product = reservation.product
                    if reservation.status == InventoryReservation.Status.ACTIVE:
                        product.reserved_stock = max(0, product.reserved_stock - reservation.quantity)
                    else:
                        product.stock += reservation.quantity
                    product.save(update_fields=["reserved_stock", "stock", "updated_at"])
                reservation.status = InventoryReservation.Status.RELEASED
                reservation.save(update_fields=["status", "updated_at"])
        return Response(OrderSerializer(order, context={"request": request}).data)
