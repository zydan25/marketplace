from django.urls import include, path
from rest_framework import serializers, viewsets
from rest_framework.routers import DefaultRouter

from .catalog_api import CatalogOptionViewSet, CatalogTreeView, CurrencyRateViewSet, PreferencesView
from .cms_views import DynamicHomeView
from .models import City, Coupon as CouponModel, PriceGroup
from .secure_auth import SecureLoginView, SecureRegisterView
from .secure_cart import SecureCartCalculateView
from .secure_catalog import SecureCategoryViewSet, SecureDesignThemeViewSet, SecureStorefrontSectionViewSet, SecureVendorViewSet
from .secure_vendor_catalog import VendorProductViewSet
from .secure_communication import SecureConversationViewSet, SecureNotificationViewSet
from .launch_order_api import LaunchOrderViewSet
from .secure_vendor import VendorApplicationViewSet
from .order_chat_api import OrderChatViewSet
from .vendor_finance_api import VendorFinanceViewSet
from .support_api import AdminSupportCloseView, AdminSupportMessageView, AdminSupportView, SupportEmployeesView, SupportMessageView, SupportView
from .serializers import CouponSerializer
from .views import AdminDashboardView, WalletViewSet, me
from .views_extra import AddressViewSet, GiftTransferViewSet, LoanViewSet

class PriceGroupSerializer(serializers.ModelSerializer):
    class Meta: model = PriceGroup; fields = "__all__"
class CitySerializer(serializers.ModelSerializer):
    price_group = PriceGroupSerializer(read_only=True)
    class Meta: model = City; fields = "__all__"
class CityViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = City.objects.filter(is_active=True)
    serializer_class = CitySerializer
class CouponViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = CouponSerializer
    def get_queryset(self): return CouponModel.objects.filter(is_active=True)

router = DefaultRouter()
router.register("vendors", SecureVendorViewSet, basename="vendor")
router.register("vendor-applications", VendorApplicationViewSet, basename="vendor-application")
router.register("categories", SecureCategoryViewSet, basename="category")
router.register("products", VendorProductViewSet, basename="product")
router.register("themes", SecureDesignThemeViewSet, basename="theme")
router.register("storefront-sections", SecureStorefrontSectionViewSet, basename="storefront-section")
router.register("wallets", WalletViewSet, basename="wallet")
router.register("vendor-finance", VendorFinanceViewSet, basename="vendor-finance")
router.register("orders", LaunchOrderViewSet, basename="order")
router.register("notifications", SecureNotificationViewSet, basename="notification")
router.register("conversations", SecureConversationViewSet, basename="conversation")
router.register("order-chats", OrderChatViewSet, basename="order-chat")
router.register("catalog-options", CatalogOptionViewSet, basename="catalog-option")
router.register("currency-rates", CurrencyRateViewSet, basename="currency-rate")
router.register("coupons", CouponViewSet, basename="coupon")
router.register("cities", CityViewSet, basename="city")
router.register("addresses", AddressViewSet, basename="address")
router.register("loans", LoanViewSet, basename="loan")
router.register("gifts", GiftTransferViewSet, basename="gift")

urlpatterns = [
    path("auth/login/", SecureLoginView.as_view(), name="login"),
    path("auth/register/", SecureRegisterView.as_view(), name="register"),
    path("auth/me/", me, name="me"),
    path("cart/calculate/", SecureCartCalculateView.as_view(), name="cart-calculate"),
    path("home/", DynamicHomeView.as_view(), name="home-global"),
    path("stores/<slug:slug>/home/", DynamicHomeView.as_view(), name="home-store"),
    path("catalog/tree/", CatalogTreeView.as_view(), name="catalog-tree"),
    path("preferences/", PreferencesView.as_view(), name="preferences"),
    path("support/", SupportView.as_view(), name="support"),
    path("support/messages/", SupportMessageView.as_view(), name="support-messages"),
    path("support/employees/", SupportEmployeesView.as_view(), name="support-employees"),
    path("admin/support/", AdminSupportView.as_view(), name="admin-support"),
    path("admin/support/<int:conversation_id>/messages/", AdminSupportMessageView.as_view(), name="admin-support-message"),
    path("admin/support/<int:conversation_id>/close/", AdminSupportCloseView.as_view(), name="admin-support-close"),
    path("admin-dashboard/", AdminDashboardView.as_view(), name="admin-dashboard"),
    path("", include(router.urls)),
]
