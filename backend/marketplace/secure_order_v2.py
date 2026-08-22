from django.db import transaction
from django.db.models import Count, Sum
from django.utils import timezone
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response

from .marketplace_models import InventoryReservation, Payment, Shipment, VendorOrder
from .models import Order, OrderItem, OrderStatusHistory, Product
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

    def _owned_vendor_orders(self, user):
        if user.role != "vendor":
            raise PermissionDenied("هذه العملية مخصصة للتاجر")
        return VendorOrder.objects.filter(vendor__owner=user).select_related(
            "vendor", "order", "order__customer", "shipment"
        ).prefetch_related("items__order_item__product")

    @staticmethod
    def _serialize_vendor_order(vendor_order):
        return {
            "id": vendor_order.id,
            "order_id": vendor_order.order_id,
            "order_number": vendor_order.order_number,
            "parent_order_number": vendor_order.order.order_number,
            "status": vendor_order.status,
            "subtotal": str(vendor_order.subtotal),
            "shipping_fee": str(vendor_order.shipping_fee),
            "discount": str(vendor_order.discount),
            "total": str(vendor_order.total),
            "commission": str(vendor_order.commission),
            "vendor_net": str(vendor_order.vendor_net),
            "currency": vendor_order.currency,
            "created_at": vendor_order.created_at.isoformat(),
            "updated_at": vendor_order.updated_at.isoformat(),
            "customer": {
                "id": vendor_order.order.customer_id,
                "phone": vendor_order.order.customer.phone,
                "name": vendor_order.order.customer.get_full_name() or vendor_order.order.customer.phone,
            },
            "shipping_address": vendor_order.order.shipping_address,
            "payment_method": vendor_order.order.payment_method,
            "payment_status": vendor_order.order.payment_status,
            "shipment": {
                "id": vendor_order.shipment.id if getattr(vendor_order, "shipment", None) else None,
                "carrier": vendor_order.shipment.carrier if getattr(vendor_order, "shipment", None) else "",
                "tracking_number": vendor_order.shipment.tracking_number if getattr(vendor_order, "shipment", None) else "",
                "status": vendor_order.shipment.status if getattr(vendor_order, "shipment", None) else Shipment.Status.PENDING,
                "shipped_at": vendor_order.shipment.shipped_at.isoformat() if getattr(vendor_order, "shipment", None) and vendor_order.shipment.shipped_at else None,
                "delivered_at": vendor_order.shipment.delivered_at.isoformat() if getattr(vendor_order, "shipment", None) and vendor_order.shipment.delivered_at else None,
            },
            "items": [
                {
                    "id": link.order_item_id,
                    "product_id": link.order_item.product_id,
                    "name": link.order_item.name_snapshot,
                    "sku": link.order_item.sku_snapshot,
                    "quantity": link.order_item.quantity,
                    "unit_price": str(link.order_item.unit_price),
                    "color": link.order_item.color,
                    "size": link.order_item.size,
                    "total": str(link.order_item.vendor_total),
                    "image": link.order_item.product.main_image.url if link.order_item.product.main_image else None,
                }
                for link in vendor_order.items.all()
            ],
        }

    @action(detail=False, methods=["get"])
    def vendor_operations(self, request):
        qs = self._owned_vendor_orders(request.user)
        status_filter = request.query_params.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter)
        query = request.query_params.get("q", "").strip()
        if query:
            qs = qs.filter(order__order_number__icontains=query)
        return Response([self._serialize_vendor_order(item) for item in qs[:100]])

    @action(detail=False, methods=["get"])
    def vendor_dashboard(self, request):
        qs = self._owned_vendor_orders(request.user)
        products = Product.objects.filter(vendor__owner=request.user)
        delivered = qs.filter(status="delivered")
        revenue = delivered.aggregate(value=Sum("vendor_net"))["value"] or 0
        return Response({
            "orders": qs.count(),
            "new_orders": qs.filter(status="pending").count(),
            "processing_orders": qs.filter(status="processing").count(),
            "shipping_orders": qs.filter(status__in=["confirmed", "shipped"]).count(),
            "delivered_orders": delivered.count(),
            "cancelled_orders": qs.filter(status="cancelled").count(),
            "revenue": str(revenue),
            "currency": qs.values_list("currency", flat=True).first() or "YER",
            "products": products.count(),
            "published_products": products.filter(is_published=True).count(),
            "low_stock_products": products.filter(stock__lte=5, stock__gt=0).count(),
            "out_of_stock_products": products.filter(stock=0).count(),
        })

    @action(detail=False, methods=["post"])
    @transaction.atomic
    def update_shipment(self, request):
        vendor_order_id = request.data.get("vendor_order_id")
        vendor_order = self._owned_vendor_orders(request.user).select_for_update().filter(pk=vendor_order_id).first()
        if not vendor_order:
            raise ValidationError({"vendor_order_id": "طلب التاجر غير موجود"})
        shipment, _ = Shipment.objects.select_for_update().get_or_create(vendor_order=vendor_order)
        carrier = str(request.data.get("carrier", shipment.carrier)).strip()[:120]
        tracking = str(request.data.get("tracking_number", shipment.tracking_number)).strip()[:160]
        new_status = str(request.data.get("status", shipment.status))
        allowed = {choice.value for choice in Shipment.Status}
        if new_status not in allowed:
            raise ValidationError({"status": "حالة الشحن غير صالحة"})
        shipment.carrier = carrier
        shipment.tracking_number = tracking
        shipment.status = new_status
        if new_status in {Shipment.Status.SHIPPED, Shipment.Status.IN_TRANSIT} and not shipment.shipped_at:
            shipment.shipped_at = timezone.now()
        if new_status == Shipment.Status.DELIVERED and not shipment.delivered_at:
            shipment.delivered_at = timezone.now()
        shipment.save(update_fields=["carrier", "tracking_number", "status", "shipped_at", "delivered_at", "updated_at"])
        return Response(self._serialize_vendor_order(vendor_order))

    @action(detail=True, methods=["get"])
    def vendor_detail(self, request, pk=None):
        vendor_order = self._owned_vendor_orders(request.user).filter(pk=pk).first()
        if not vendor_order:
            raise PermissionDenied("لا تملك هذا الطلب")
        return Response(self._serialize_vendor_order(vendor_order))

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
