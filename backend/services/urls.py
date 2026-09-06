from django.urls import path

from .catalog_admin_api import CatalogAdminAPIView
from .catalog_admin_safe import SafeCatalogAdminEntityAPIView
from .secure_catalog import SecureServiceCatalogAPIView, SecureServiceDetailAPIView
from .secure_api import SecureServiceRequestAPIView, SecureServiceTransactionDetailAPIView
from .webhook import SanaacashWebhookAPIView

urlpatterns = [
    path("catalog/", SecureServiceCatalogAPIView.as_view(), name="service-catalog"),
    path("services/<int:pk>/", SecureServiceDetailAPIView.as_view(), name="service-detail"),
    path("requests/", SecureServiceRequestAPIView.as_view(), name="service-request"),
    path("requests/<uuid:pk>/", SecureServiceTransactionDetailAPIView.as_view(), name="service-request-detail"),
    path("webhook/sanaacash/", SanaacashWebhookAPIView.as_view(), name="sanaacash-webhook"),
    path("admin/catalog/", CatalogAdminAPIView.as_view(), name="admin-catalog"),
    path("admin/catalog/<str:entity>/", SafeCatalogAdminEntityAPIView.as_view(), name="admin-catalog-entity"),
]
