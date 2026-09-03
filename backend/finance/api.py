from django.db.models import Q
from rest_framework import serializers, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import BasePermission, IsAuthenticated
from rest_framework.response import Response

from marketplace.catalog_api import CurrencyRateViewSet as LegacyCurrencyRateViewSet
from marketplace.vendor_finance_api import VendorFinanceViewSet as LegacyVendorFinanceViewSet
from marketplace.vendor_shipping_api import VendorCityShippingViewSet as LegacyShippingViewSet
from marketplace.views import WalletViewSet as LegacyWalletViewSet
from marketplace.models import VendorProfile

from .models import CurrencyRate, Payment, VendorCityShipping, VendorLedgerEntry, VendorPayout, Wallet, WalletTransaction


class FinanceReadWritePermission(BasePermission):
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
        if vendor and vendor.owner_id == request.user.id:
            return True
        if hasattr(obj, "wallet") and obj.wallet.user_id == request.user.id:
            return True
        if hasattr(obj, "user_id") and obj.user_id == request.user.id:
            return True
        return False


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
    class Meta:
        model = VendorPayout
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at")


class LedgerEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = VendorLedgerEntry
        fields = "__all__"


class CurrencyRateSerializer(serializers.ModelSerializer):
    class Meta:
        model = CurrencyRate
        fields = "__all__"


class VendorCityShippingSerializer(serializers.ModelSerializer):
    class Meta:
        model = VendorCityShipping
        fields = "__all__"


class WalletViewSet(LegacyWalletViewSet):
    """Keeps the established wallet behavior under the finance domain."""


class VendorFinanceViewSet(LegacyVendorFinanceViewSet):
    """Keeps established vendor ledger/finance calculations under finance."""


class CurrencyRateViewSet(LegacyCurrencyRateViewSet):
    serializer_class = CurrencyRateSerializer


class VendorCityShippingViewSet(LegacyShippingViewSet):
    serializer_class = VendorCityShippingSerializer


class WalletTransactionViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = WalletTransactionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_staff or getattr(user, "role", None) == "admin":
            return WalletTransaction.objects.select_related("wallet")
        return WalletTransaction.objects.filter(wallet__user=user).select_related("wallet")


class VendorPayoutViewSet(viewsets.ModelViewSet):
    serializer_class = VendorPayoutSerializer
    permission_classes = [FinanceReadWritePermission]
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_queryset(self):
        user = self.request.user
        qs = VendorPayout.objects.select_related("vendor", "order", "vendor_order")
        if user.is_staff or getattr(user, "role", None) == "admin":
            return qs
        return qs.filter(vendor__owner=user)

    def perform_create(self, serializer):
        vendor_id = self.request.data.get("vendor")
        if getattr(self.request.user, "role", None) == "vendor":
            vendor = VendorProfile.objects.filter(owner=self.request.user).first()
            if not vendor:
                raise serializers.ValidationError({"vendor": "لا يوجد متجر مرتبط بالحساب."})
            serializer.save(vendor=vendor)
            return
        serializer.save(vendor_id=vendor_id)


class VendorLedgerEntryViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = LedgerEntrySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        qs = VendorLedgerEntry.objects.select_related("vendor", "vendor_order")
        if user.is_staff or getattr(user, "role", None) == "admin":
            return qs
        return qs.filter(vendor__owner=user)


class PaymentViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = PaymentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        qs = Payment.objects.select_related("order", "order__customer")
        if user.is_staff or getattr(user, "role", None) == "admin":
            return qs
        return qs.filter(Q(order__customer=user) | Q(order__vendor_orders__vendor__owner=user)).distinct()


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def api_info(request):
    return Response({
        "domain": "finance",
        "version": "2",
        "resources": ["wallets", "wallet-transactions", "payments", "vendor-finance", "vendor-payouts", "vendor-ledger", "currency-rates", "vendor-city-shipping"],
    })
