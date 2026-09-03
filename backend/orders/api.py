from django.db.models import Q
from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import AllowAny, BasePermission, IsAuthenticated
from rest_framework.response import Response

from marketplace.launch_order_api import LaunchOrderViewSet as LegacyOrderViewSet
from marketplace.models import VendorProfile

from .models import InventoryReservation, Order, OrderItem, OrderStatusHistory, Payment, Shipment, VendorOrder, VendorOrderItem


class OrderAccessPermission(BasePermission):
    message = "لا تملك صلاحية الوصول لهذا المورد."

    def has_permission(self, request, view):
        if request.method in ("GET", "HEAD", "OPTIONS"):
            return bool(request.user and request.user.is_authenticated)
        return bool(request.user and request.user.is_authenticated and (request.user.is_staff or getattr(request.user, "role", None) in {"admin", "vendor"}))

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
        read_only_fields = ("id", "created_at", "updated_at")


class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = "__all__"


class VendorOrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = VendorOrder
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at", "order_number", "subtotal", "shipping_fee", "discount", "total", "commission", "vendor_net")


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
        read_only_fields = ("id", "created_at", "updated_at", "shipped_at", "delivered_at")


class ReservationSerializer(serializers.ModelSerializer):
    class Meta:
        model = InventoryReservation
        fields = "__all__"


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = "__all__"


class OrderViewSet(LegacyOrderViewSet):
    """Compatibility-backed order lifecycle retained while ownership moves to orders."""


class OrderItemViewSet(ReadOnlyDomainViewSet):
    serializer_class = OrderItemSerializer

    def get_queryset(self):
        user = self.request.user
        qs = OrderItem.objects.select_related("order", "vendor", "product")
        if user.is_staff or getattr(user, "role", None) == "admin":
            return qs
        return qs.filter(Q(order__customer=user) | Q(vendor__owner=user)).distinct()


class VendorOrderViewSet(viewsets.ModelViewSet):
    serializer_class = VendorOrderSerializer
    permission_classes = [OrderAccessPermission]
    http_method_names = ["get", "patch", "head", "options", "post"]

    def get_queryset(self):
        user = self.request.user
        qs = VendorOrder.objects.select_related("order", "vendor")
        if user.is_staff or getattr(user, "role", None) == "admin":
            return qs
        if getattr(user, "role", None) == "vendor":
            return qs.filter(vendor__owner=user)
        return qs.filter(order__customer=user)

    def create(self, request, *args, **kwargs):
        return Response({"detail": "ينشأ طلب التاجر تلقائيًا ضمن دورة الطلب."}, status=status.HTTP_405_METHOD_NOT_ALLOWED)

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        allowed = {"status"}
        payload = {key: value for key, value in request.data.items() if key in allowed}
        serializer = self.get_serializer(instance, data=payload, partial=True)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def transition(self, request, pk=None):
        instance = self.get_object()
        new_status = str(request.data.get("status", "")).strip()
        valid = {choice[0] for choice in VendorOrder.Status.choices}
        if new_status not in valid:
            return Response({"detail": "حالة الطلب غير صالحة.", "allowed": sorted(valid)}, status=status.HTTP_400_BAD_REQUEST)
        instance.status = new_status
        instance.save(update_fields=["status", "updated_at"])
        return Response(self.get_serializer(instance).data)


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


class ShipmentViewSet(viewsets.ModelViewSet):
    serializer_class = ShipmentSerializer
    permission_classes = [OrderAccessPermission]
    http_method_names = ["get", "patch", "head", "options"]

    def get_queryset(self):
        user = self.request.user
        qs = Shipment.objects.select_related("vendor_order", "vendor_order__order", "vendor_order__vendor")
        if user.is_staff or getattr(user, "role", None) == "admin":
            return qs
        return qs.filter(Q(vendor_order__order__customer=user) | Q(vendor_order__vendor__owner=user)).distinct()

    def update(self, request, *args, **kwargs):
        if not (request.user.is_staff or getattr(request.user, "role", None) in {"admin", "vendor"}):
            return Response({"detail": "تحديث الشحنة متاح للتاجر أو الإدارة."}, status=status.HTTP_403_FORBIDDEN)
        return super().update(request, *args, **kwargs)


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
        "note": "إنشاء الطلبات يحافظ على محرك دورة الطلب الحالي ويُقدَّم الآن من نطاق orders.",
    })
