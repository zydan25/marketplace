from django.urls import path

from .catalog_admin_api import CatalogAdminAPIView
from .catalog_admin_safe import SafeCatalogAdminEntityAPIView
from .secure_catalog import SecureServiceCatalogAPIView, SecureServiceDetailAPIView
from .secure_api import SecureServiceRequestAPIView, SecureServiceTransactionDetailAPIView
from .webhook import SanaacashWebhookAPIView
from .wifi_api import WifiNetworksAPIView, WifiPurchaseAPIView, WifiMyCardsAPIView

urlpatterns = [
    path("catalog/", SecureServiceCatalogAPIView.as_view(), name="service-catalog"),
    path("services/<int:pk>/", SecureServiceDetailAPIView.as_view(), name="service-detail"),
    path("requests/", SecureServiceRequestAPIView.as_view(), name="service-request"),
    path("requests/<uuid:pk>/", SecureServiceTransactionDetailAPIView.as_view(), name="service-request-detail"),
    path("webhook/sanaacash/", SanaacashWebhookAPIView.as_view(), name="sanaacash-webhook"),
    path("wifi/networks/", WifiNetworksAPIView.as_view(), name="wifi-networks"),
    path("wifi/purchase/", WifiPurchaseAPIView.as_view(), name="wifi-purchase"),
    path("wifi/my-cards/", WifiMyCardsAPIView.as_view(), name="wifi-my-cards"),
    path("admin/catalog/", CatalogAdminAPIView.as_view(), name="admin-catalog"),
    path("admin/catalog/<str:entity>/", SafeCatalogAdminEntityAPIView.as_view(), name="admin-catalog-entity"),
]
