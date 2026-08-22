from django.urls import include, path
from rest_framework import serializers, viewsets
from rest_framework.routers import DefaultRouter

from .cms_views import DynamicHomeView
from .models import City, Coupon as CouponModel, PriceGroup
from .secure_auth import SecureLoginView, SecureRegisterView
from .secure_catalog import (
    SecureCategoryViewSet,
    SecureDesignThemeViewSet,
    SecureProductViewSet,
    SecureStorefrontSectionViewSet,
    SecureVendorViewSet,
)
from .secure_communication import SecureConversationViewSet, SecureNotificationViewSet
from .secure_order_api import SecureOrderViewSet
from .serializers import CouponSerializer
from .views import AdminDashboardView, CartCalculateView, WalletViewSet, me
from .views_extra import AddressViewSet, GiftTransferViewSet, LoanViewSet


class PriceGroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = PriceGroup
        fields = "__all__"


class CitySerializer(serializers.ModelSerializer):
    price_group = PriceGroupSerializer(read_only=True)

    class Meta:
        model = City
        fields = "__all__"


class CityViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = City.objects.filter(is_active=True)
    serializer_class = CitySerializer


class CouponViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = CouponSerializer

    def get_queryset(self):
        return CouponModel.objects.filter(is_active=True)


router = DefaultRouter()
router.register("vendors", SecureVendorViewSet, basename="vendor")
router.register("categories", SecureCategoryViewSet, basename="category")
router.register("products", SecureProductViewSet, basename="product")
router.register("themes", SecureDesignThemeViewSet, basename="theme")
router.register("storefront-sections", SecureStorefrontSectionViewSet, basename="storefront-section")
router.register("wallets", WalletViewSet, basename="wallet")
router.register("orders", SecureOrderViewSet, basename="order")
router.register("notifications", SecureNotificationViewSet, basename="notification")
router.register("conversations", SecureConversationViewSet, basename="conversation")
router.register("coupons", CouponViewSet, basename="coupon")
router.register("cities", CityViewSet, basename="city")
router.register("addresses", AddressViewSet, basename="address")
router.register("loans", LoanViewSet, basename="loan")
router.register("gifts", GiftTransferViewSet, basename="gift")

urlpatterns = [
    path("auth/login/", SecureLoginView.as_view(), name="login"),
    path("auth/register/", SecureRegisterView.as_view(), name="register"),
    path("auth/me/", me, name="me"),
    path("cart/calculate/", CartCalculateView.as_view(), name="cart-calculate"),
    path("home/", DynamicHomeView.as_view(), name="home-global"),
    path("stores/<slug:slug>/home/", DynamicHomeView.as_view(), name="home-store"),
    path("admin-dashboard/", AdminDashboardView.as_view(), name="admin-dashboard"),
    path("", include(router.urls)),
]
