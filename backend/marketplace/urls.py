from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    AdminDashboardView,
    CategoryViewSet,
    ConversationViewSet,
    DesignThemeViewSet,
    LoginView,
    CartCalculateView,
    NotificationViewSet,
    OrderViewSet,
    ProductViewSet,
    RegisterView,
    StorefrontSectionViewSet,
    VendorViewSet,
    WalletViewSet,
    me,
)
from rest_framework import viewsets
from .models import Coupon as CouponModel
from .views import CouponSerializer
from .cms_views import DynamicHomeView
from rest_framework import serializers
from .models import City, PriceGroup
from .views_extra import AddressViewSet, LoanViewSet, GiftTransferViewSet

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
router.register("vendors", VendorViewSet, basename="vendor")
router.register("categories", CategoryViewSet, basename="category")
router.register("products", ProductViewSet, basename="product")
router.register("themes", DesignThemeViewSet, basename="theme")
router.register("storefront-sections", StorefrontSectionViewSet, basename="storefront-section")
router.register("wallets", WalletViewSet, basename="wallet")
router.register("orders", OrderViewSet, basename="order")
router.register("notifications", NotificationViewSet, basename="notification")
router.register("conversations", ConversationViewSet, basename="conversation")
router.register("coupons", CouponViewSet, basename="coupon")
router.register("cities", CityViewSet, basename="city")
router.register("addresses", AddressViewSet, basename="address")
router.register("loans", LoanViewSet, basename="loan")
router.register("gifts", GiftTransferViewSet, basename="gift")

urlpatterns = [
    path("auth/login/", LoginView.as_view(), name="login"),
    path("auth/register/", RegisterView.as_view(), name="register"),
    path("auth/me/", me, name="me"),
    path("cart/calculate/", CartCalculateView.as_view(), name="cart-calculate"),
    path("home/", DynamicHomeView.as_view(), name="home-global"),
    path("stores/<slug:slug>/home/", DynamicHomeView.as_view(), name="home-store"),
    path("admin-dashboard/", AdminDashboardView.as_view(), name="admin-dashboard"),
    path("", include(router.urls)),
]
