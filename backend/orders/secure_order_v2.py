from django.db import transaction
from django.db.models import Sum
from django.utils import timezone
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response

from catalog.models import Product
from finance.models import VendorLedgerEntry

from .models import Order, OrderStatusHistory, Payment, Shipment, VendorOrder
from .secure_order_api import SecureOrderViewSet
from .serializers import OrderSerializer


class SecureOrderV2ViewSet(SecureOrderViewSet):
    """Domain-owned order operations for vendors and administration."""

    def _owned_vendor_orders(self, user):
        if getattr(user, "role", None) != "vendor":
            raise PermissionDenied("هذه العملية مخصصة للتاجر")
        return (
            VendorOrder.objects.filter(vendor__owner=user)
            .select_related("vendor", "order", "order__customer", "shipment")
            .prefetch_related("items__order_item__product")
            .order_by("-created_at")
        )

    @staticmethod
    def _serialize_vendor_order(vendor_order):
        shipment = getattr(vendor_order, "shipment", None)
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
                "id": shipment.id if shipment else None,
                "carrier": shipment.carrier if shipment else "",
                "tracking_number": shipment.tracking_number if shipment else "",
                "status": shipment.status if shipment else Shipment.Status.PENDING,
                "shipped_at": shipment.shipped_at.isoformat() if shipment and shipment.shipped_at else None,
                "delivered_at": shipment.delivered_at.isoformat() if shipment and shipment.delivered_at else None,
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
        new_status = str(request.data.get("status", shipment.status))
        allowed = {choice.value for choice in Shipment.Status}
        if new_status not in allowed:
            raise ValidationError({"status": "حالة الشحن غير صالحة"})
        shipment.carrier = str(request.data.get("carrier", shipment.carrier)).strip()[:120]
        shipment.tracking_number = str(request.data.get("tracking_number", shipment.tracking_number)).strip()[:160]
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

    @staticmethod
    def _record_sale(vendor_order):
        reference = f"SALE-{vendor_order.id}"
        if VendorLedgerEntry.objects.filter(reference=reference).exists():
            return
        previous = (
            VendorLedgerEntry.objects.filter(vendor=vendor_order.vendor, currency=vendor_order.currency)
            .order_by("-id")
            .first()
        )
        balance = (previous.balance_after if previous else 0) + vendor_order.vendor_net
        VendorLedgerEntry.objects.create(
            vendor=vendor_order.vendor,
            vendor_order=vendor_order,
            entry_type=VendorLedgerEntry.Types.SALE,
            amount=vendor_order.vendor_net,
            balance_after=balance,
            currency=vendor_order.currency,
            reference=reference,
            metadata={"source": "orders.secure_order_v2"},
        )

    @action(detail=True, methods=["post"])
    @transaction.atomic
    def update_vendor_status(self, request, pk=None):
        order = self.get_object()
        if getattr(request.user, "role", None) != "vendor":
            raise PermissionDenied("هذه العملية للتاجر فقط")
        vendor_order = order.vendor_orders.select_for_update().filter(vendor__owner=request.user).first()
        if not vendor_order:
            raise PermissionDenied("لا تملك هذا الطلب")
        new_status = str(request.data.get("status", ""))
        allowed = {"confirmed", "processing", "shipped", "delivered", "cancelled"}
        if new_status not in allowed:
            raise ValidationError({"status": "حالة التاجر غير صالحة"})
        if new_status in {"shipped", "delivered"} and order.payment_method != "cash_on_delivery" and getattr(getattr(order, "payment", None), "status", None) != Payment.Status.PAID:
            raise ValidationError({"status": "لا يمكن شحن الطلب قبل تأكيد الدفع"})
        old_status = vendor_order.status
        vendor_order.status = new_status
        vendor_order.save(update_fields=["status", "updated_at"])
        if new_status == "delivered" and old_status != "delivered":
            self._commit_vendor_order_inventory(vendor_order)
            self._record_sale(vendor_order)
            shipment = getattr(vendor_order, "shipment", None)
            if shipment:
                shipment.status = Shipment.Status.DELIVERED
                shipment.delivered_at = shipment.delivered_at or timezone.now()
                shipment.save(update_fields=["status", "delivered_at", "updated_at"])
            if order.payment_method == "cash_on_delivery":
                payment = order.payment
                if payment.status != Payment.Status.PAID:
                    payment.status = Payment.Status.PAID
                    payment.paid_at = timezone.now()
                    payment.save(update_fields=["status", "paid_at", "updated_at"])
                    order.payment_status = "paid"
                    order.save(update_fields=["payment_status", "updated_at"])
        self._sync_parent_status(order)
        return Response({"vendor_order_id": vendor_order.id, "status": vendor_order.status, "order_status": order.status})
