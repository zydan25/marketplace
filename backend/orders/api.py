from django.db.models import Q
from rest_framework import serializers, viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, BasePermission
from rest_framework.response import Response

from marketplace.launch_order_api import LaunchOrderViewSet as LegacyOrderViewSet

from .models import InventoryReservation, Order, OrderItem, OrderStatusHistory, Payment, Shipment, VendorOrder, VendorOrderItem


class OrderAccessPermission(BasePermission):
    message = "لا تملك صلاحية الوصول لهذا المورد."

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        user = request.user
        if user.is_staff or getattr(user, "role", None) == "admin":
            return True
        if hasattr(obj, "customer_id") and obj.customer_id == user.id:
            return True
        vendor = getattr(obj, "vendor", None)
        if vendor and vendor.owner_id == user.id:
            return True
        if hasattr(obj, "order") and obj.order.customer_id == user.id:
            return True
        if hasattr(obj, "vendor_order") and obj.vendor_order.vendor.owner_id == user.id:
            return True
        return False


class ReadOnlyDomainViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [OrderAccessPermission]


class OrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at", "customer", "order_number", "status", "subtotal", "shipping_fee", "discount", "total", "currency", "payment_status")


class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = "__all__"


class VendorOrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = VendorOrder
        fields = "__all__"


class VendorOrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = VendorOrderItem
        fields = "__all__"


class StatusHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderStatusHistory
        fields = "__all__"


class ShipmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Shipment
        fields = "__all__"


class ReservationSerializer(serializers.ModelSerializer):
    class Meta:
        model = InventoryReservation
        fields = "__all__"


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = "__all__"


class OrderViewSet(LegacyOrderViewSet):
    """Compatibility-backed order lifecycle; sensitive state changes stay in domain actions."""


class OrderItemViewSet(ReadOnlyDomainViewSet):
    serializer_class = OrderItemSerializer

    def get_queryset(self):
        user = self.request.user
        qs = OrderItem.objects.select_related("order", "vendor", "product")
        if user.is_staff or getattr(user, "role", None) == "admin":
            return qs
        return qs.filter(Q(order__customer=user) | Q(vendor__owner=user)).distinct()


class VendorOrderViewSet(ReadOnlyDomainViewSet):
    serializer_class = VendorOrderSerializer

    def get_queryset(self):
        user = self.request.user
        qs = VendorOrder.objects.select_related("order", "vendor")
        if user.is_staff or getattr(user, "role", None) == "admin":
            return qs
        if getattr(user, "role", None) == "vendor":
            return qs.filter(vendor__owner=user)
        return qs.filter(order__customer=user)


class VendorOrderItemViewSet(ReadOnlyDomainViewSet):
    serializer_class = VendorOrderItemSerializer

    def get_queryset(self):
        user = self.request.user
        qs = VendorOrderItem.objects.select_related("vendor_order", "order_item")
        if user.is_staff or getattr(user, "role", None) == "admin":
            return qs
        if getattr(user, "role", None) == "vendor":
            return qs.filter(vendor_order__vendor__owner=user)
        return qs.filter(vendor_order__order__customer=user)


class StatusHistoryViewSet(ReadOnlyDomainViewSet):
    serializer_class = StatusHistorySerializer

    def get_queryset(self):
        user = self.request.user
        qs = OrderStatusHistory.objects.select_related("order", "changed_by")
        if user.is_staff or getattr(user, "role", None) == "admin":
            return qs
        return qs.filter(Q(order__customer=user) | Q(order__vendor_orders__vendor__owner=user)).distinct()


class ShipmentViewSet(ReadOnlyDomainViewSet):
    serializer_class = ShipmentSerializer

    def get_queryset(self):
        user = self.request.user
        qs = Shipment.objects.select_related("vendor_order", "vendor_order__order", "vendor_order__vendor")
        if user.is_staff or getattr(user, "role", None) == "admin":
            return qs
        return qs.filter(Q(vendor_order__order__customer=user) | Q(vendor_order__vendor__owner=user)).distinct()


class ReservationViewSet(ReadOnlyDomainViewSet):
    serializer_class = ReservationSerializer

    def get_queryset(self):
        user = self.request.user
        qs = InventoryReservation.objects.select_related("order", "order_item", "product", "variant")
        if user.is_staff or getattr(user, "role", None) == "admin":
            return qs
        return qs.filter(Q(order__customer=user) | Q(order_item__vendor__owner=user)).distinct()


class PaymentViewSet(ReadOnlyDomainViewSet):
    serializer_class = PaymentSerializer

    def get_queryset(self):
        user = self.request.user
        qs = Payment.objects.select_related("order", "order__customer")
        if user.is_staff or getattr(user, "role", None) == "admin":
            return qs
        return qs.filter(order__customer=user)


@api_view(["GET"])
@permission_classes([AllowAny])
def api_info(request):
    return Response({
        "domain": "orders",
        "version": "2",
        "resources": ["orders", "order-items", "vendor-orders", "vendor-order-items", "status-history", "shipments", "inventory-reservations", "payments"],
        "write_rules": "تغيير حالة الطلب والشحن والمخزون يتم فقط عبر دورة الطلب الآمنة.",
    })
