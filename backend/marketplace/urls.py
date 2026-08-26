from django.urls import include, path
from rest_framework import serializers, viewsets
from rest_framework.routers import DefaultRouter
from .cms_views import DynamicHomeView
from .models import City, Coupon as CouponModel, PriceGroup
from .secure_auth import SecureLoginView, SecureRegisterView
from .secure_cart import SecureCartCalculateView
from .secure_catalog import SecureCategoryViewSet, SecureDesignThemeViewSet, SecureProductViewSet, SecureStorefrontSectionViewSet, SecureVendorViewSet
from .secure_communication import SecureConversationViewSet, SecureNotificationViewSet
from .secure_order_v2 import SecureOrderV2ViewSet
from .secure_vendor import VendorApplicationViewSet
from .order_chat_api import OrderChatViewSet
from .vendor_finance_api import VendorFinanceViewSet
from .serializers import CouponSerializer
from .views import AdminDashboardView, WalletViewSet, me
from .views_extra import AddressViewSet, GiftTransferViewSet, LoanViewSet
from .service_api import ServiceCategoryViewSet, ServiceViewSet, ServiceSubmissionViewSet
from .engagement_api import FavoriteViewSet, ProductCommentViewSet
from .password_reset_api import PasswordResetWhatsAppRequestView, PasswordResetConfirmView

class PriceGroupSerializer(serializers.ModelSerializer):
    class Meta: model = PriceGroup; fields = "__all__"
class CitySerializer(serializers.ModelSerializer):
    price_group = PriceGroupSerializer(read_only=True)
    class Meta: model = City; fields = "__all__"
class CityViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = City.objects.filter(is_active=True); serializer_class = CitySerializer
class CouponViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = CouponSerializer
    def get_queryset(self): return CouponModel.objects.filter(is_active=True)

router = DefaultRouter()
router.register("vendors", SecureVendorViewSet, basename="vendor")
router.register("vendor-applications", VendorApplicationViewSet, basename="vendor-application")
router.register("categories", SecureCategoryViewSet, basename="category")
router.register("products", SecureProductViewSet, basename="product")
router.register("themes", SecureDesignThemeViewSet, basename="theme")
router.register("storefront-sections", SecureStorefrontSectionViewSet, basename="storefront-section")
router.register("wallets", WalletViewSet, basename="wallet")
router.register("vendor-finance", VendorFinanceViewSet, basename="vendor-finance")
router.register("orders", SecureOrderV2ViewSet, basename="order")
router.register("notifications", SecureNotificationViewSet, basename="notification")
router.register("conversations", SecureConversationViewSet, basename="conversation")
router.register("order-chats", OrderChatViewSet, basename="order-chat")
router.register("coupons", CouponViewSet, basename="coupon")
router.register("cities", CityViewSet, basename="city")
router.register("addresses", AddressViewSet, basename="address")
router.register("loans", LoanViewSet, basename="loan")
router.register("gifts", GiftTransferViewSet, basename="gift")
router.register("service-categories", ServiceCategoryViewSet, basename="service-category")
router.register("services", ServiceViewSet, basename="service")
router.register("service-submissions", ServiceSubmissionViewSet, basename="service-submission")
router.register("favorites", FavoriteViewSet, basename="favorite")
router.register("product-comments", ProductCommentViewSet, basename="product-comment")

urlpatterns = [
    path("auth/login/", SecureLoginView.as_view(), name="login"),
    path("auth/register/", SecureRegisterView.as_view(), name="register"),
    path("auth/me/", me, name="me"),
    path("auth/password-reset/whatsapp/", PasswordResetWhatsAppRequestView.as_view(), name="password-reset-whatsapp"),
    path("auth/reset-password/<str:token>/", PasswordResetConfirmView.as_view(), name="password-reset-confirm"),
    path("cart/calculate/", SecureCartCalculateView.as_view(), name="cart-calculate"),
    path("home/", DynamicHomeView.as_view(), name="home-global"),
    path("stores/<slug:slug>/home/", DynamicHomeView.as_view(), name="home-store"),
    path("admin-dashboard/", AdminDashboardView.as_view(), name="admin-dashboard"),
    path("", include(router.urls)),
]
