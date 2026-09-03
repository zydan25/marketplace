from django.db.models import Q
from rest_framework import serializers, viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, BasePermission, IsAuthenticated
from rest_framework.response import Response

from marketplace.vendor_finance_api import VendorFinanceViewSet as LegacyVendorFinanceViewSet
from marketplace.views import WalletViewSet as LegacyWalletViewSet
from marketplace.models import VendorProfile

from .models import CurrencyRate, Payment, VendorCityShipping, VendorLedgerEntry, VendorPayout, Wallet, WalletTransaction


class FinanceWritePermission(BasePermission):
    message = "لا تملك صلاحية تعديل هذا المورد المالي."

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.method in ("GET", "HEAD", "OPTIONS"):
            return True
        return request.user.is_staff or getattr(request.user, "role", None) in {"admin", "vendor"}

    def has_object_permission(self, request, view, obj):
        if request.user.is_staff or getattr(request.user, "role", None) == "admin":
            return True
        vendor = getattr(obj, "vendor", None)
        return bool(vendor and vendor.owner_id == request.user.id)


class AdminWritePermission(BasePermission):
    message = "هذه العملية متاحة للإدارة فقط."

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.method in ("GET", "HEAD", "OPTIONS"):
            return True
        return request.user.is_staff or getattr(request.user, "role", None) == "admin"


class WalletSerializer(serializers.ModelSerializer):
    class Meta:
        model = Wallet
        fields = "__all__"


class WalletTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = WalletTransaction
        fields = "__all__"


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = "__all__"


class VendorPayoutSerializer(serializers.ModelSerializer):
    vendor_name = serializers.CharField(source="vendor.store_name", read_only=True)

    class Meta:
        model = VendorPayout
        fields = (
            "id", "vendor", "vendor_name", "vendor_order", "order", "amount",
            "currency", "status", "reference", "note", "created_at", "updated_at",
        )
        read_only_fields = (
            "id", "vendor", "vendor_name", "vendor_order", "order", "amount",
            "currency", "status", "reference", "note", "created_at", "updated_at",
        )


class LedgerEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = VendorLedgerEntry
        fields = "__all__"


class CurrencyRateSerializer(serializers.ModelSerializer):
    class Meta:
        model = CurrencyRate
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at", "updated_by")


class VendorCityShippingSerializer(serializers.ModelSerializer):
    vendor = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = VendorCityShipping
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at", "vendor")


class WalletViewSet(LegacyWalletViewSet):
    """Established wallet behavior exposed under the finance domain."""


class VendorFinanceViewSet(LegacyVendorFinanceViewSet):
    """Established vendor ledger and payout workflow exposed under finance."""


class CurrencyRateViewSet(viewsets.ModelViewSet):
    serializer_class = CurrencyRateSerializer
    permission_classes = [AdminWritePermission]
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_queryset(self):
        if self.request.user.is_staff or getattr(self.request.user, "role", None) == "admin":
            return CurrencyRate.objects.all()
        return CurrencyRate.objects.filter(is_active=True)

    def perform_create(self, serializer):
        serializer.save(updated_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)


class VendorCityShippingViewSet(viewsets.ModelViewSet):
    serializer_class = VendorCityShippingSerializer
    permission_classes = [FinanceWritePermission]
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_queryset(self):
        user = self.request.user
        qs = VendorCityShipping.objects.select_related("vendor", "city")
        if user.is_staff or getattr(user, "role", None) == "admin":
            return qs
        if getattr(user, "role", None) == "vendor":
            return qs.filter(vendor__owner=user)
        return qs.none()

    def perform_create(self, serializer):
        user = self.request.user
        if getattr(user, "role", None) == "vendor" and not user.is_staff:
            vendor = VendorProfile.objects.filter(owner=user, status="active").first()
            if not vendor:
                raise serializers.ValidationError({"vendor": "لا يوجد متجر نشط مرتبط بالحساب."})
            serializer.save(vendor=vendor)
            return
        vendor_id = self.request.data.get("vendor")
        vendor = VendorProfile.objects.filter(pk=vendor_id).first()
        if not vendor:
            raise serializers.ValidationError({"vendor": "التاجر غير موجود."})
        serializer.save(vendor=vendor)

    def perform_update(self, serializer):
        instance = serializer.instance
        if getattr(self.request.user, "role", None) == "vendor" and not self.request.user.is_staff:
            serializer.save(vendor=instance.vendor)
        else:
            serializer.save()


class WalletTransactionViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = WalletTransactionSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "head", "options"]

    def get_queryset(self):
        user = self.request.user
        if user.is_staff or getattr(user, "role", None) == "admin":
            return WalletTransaction.objects.select_related("wallet")
        return WalletTransaction.objects.filter(wallet__user=user).select_related("wallet")


class VendorPayoutViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = VendorPayoutSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "head", "options"]

    def get_queryset(self):
        user = self.request.user
        qs = VendorPayout.objects.select_related("vendor", "order", "vendor_order")
        if user.is_staff or getattr(user, "role", None) == "admin":
            return qs
        if getattr(user, "role", None) == "vendor":
            return qs.filter(vendor__owner=user)
        return qs.filter(vendor_order__order__customer=user)


class VendorLedgerEntryViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = LedgerEntrySerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "head", "options"]

    def get_queryset(self):
        user = self.request.user
        qs = VendorLedgerEntry.objects.select_related("vendor", "vendor_order")
        if user.is_staff or getattr(user, "role", None) == "admin":
            return qs
        return qs.filter(vendor__owner=user)


class PaymentViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = PaymentSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "head", "options"]

    def get_queryset(self):
        user = self.request.user
        qs = Payment.objects.select_related("order", "order__customer")
        if user.is_staff or getattr(user, "role", None) == "admin":
            return qs
        return qs.filter(Q(order__customer=user) | Q(order__vendor_orders__vendor__owner=user)).distinct()


@api_view(["GET"])
@permission_classes([AllowAny])
def api_info(request):
    return Response({
        "domain": "finance",
        "version": "2",
        "resources": ["wallets", "wallet-transactions", "payments", "vendor-finance", "vendor-payouts", "vendor-ledger", "currency-rates", "vendor-city-shipping"],
        "write_rules": {
            "wallets": "domain actions only",
            "vendor-payouts": "read only; request via vendor-finance/request_payout",
            "currency-rates": "admin only",
            "vendor-city-shipping": "vendor owns its rows; admin may manage all",
        },
    })
