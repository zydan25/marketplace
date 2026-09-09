from django.urls import path

from .catalog_admin_api import CatalogAdminAPIView
from .catalog_admin_safe import SafeCatalogAdminEntityAPIView
from .customer_reports_api import CustomerServiceProviderCheckAPIView, CustomerServiceReportsAPIView
from .secure_catalog import SecureServiceCatalogAPIView, SecureServiceDetailAPIView
from .secure_api import SecureServiceRequestAPIView, SecureServiceTransactionDetailAPIView
from .settings_api import ServiceSettingDetailAPIView, ServiceSettingServiceAPIView, ServiceSettingsAPIView
from .webhook import SanaacashWebhookAPIView
from .wifi_api import WifiNetworksAPIView, WifiPurchaseAPIView, WifiMyCardsAPIView

urlpatterns = [
    path("catalog/", SecureServiceCatalogAPIView.as_view(), name="service-catalog"),
    path("settings/", ServiceSettingsAPIView.as_view(), name="service-settings"),
    path("settings/<slug:key>/", ServiceSettingDetailAPIView.as_view(), name="service-setting-detail"),
    path("settings/<slug:key>/service/", ServiceSettingServiceAPIView.as_view(), name="service-setting-service"),
    path("services/<int:pk>/", SecureServiceDetailAPIView.as_view(), name="service-detail"),
    path("requests/", SecureServiceRequestAPIView.as_view(), name="service-request"),
    path("requests/<uuid:pk>/", SecureServiceTransactionDetailAPIView.as_view(), name="service-request-detail"),
    path("requests/<uuid:pk>/provider-check/", CustomerServiceProviderCheckAPIView.as_view(), name="service-request-provider-check"),
    path("reports/", CustomerServiceReportsAPIView.as_view(), name="customer-service-reports"),
    path("webhook/sanaacash/", SanaacashWebhookAPIView.as_view(), name="sanaacash-webhook"),
    path("wifi/networks/", WifiNetworksAPIView.as_view(), name="wifi-networks"),
    path("wifi/purchase/", WifiPurchaseAPIView.as_view(), name="wifi-purchase"),
    path("wifi/my-cards/", WifiMyCardsAPIView.as_view(), name="wifi-my-cards"),
    path("admin/catalog/", CatalogAdminAPIView.as_view(), name="admin-catalog"),
    path("admin/catalog/<str:entity>/", SafeCatalogAdminEntityAPIView.as_view(), name="admin-catalog-entity"),
]
