from django.urls import path

from .api import ServiceCatalogAPIView, ServiceDetailAPIView
from .secure_api import SecureServiceRequestAPIView, SecureServiceTransactionDetailAPIView
from .webhook import SanaacashWebhookAPIView

urlpatterns = [
    path("catalog/", ServiceCatalogAPIView.as_view(), name="service-catalog"),
    path("services/<int:pk>/", ServiceDetailAPIView.as_view(), name="service-detail"),
    path("requests/", SecureServiceRequestAPIView.as_view(), name="service-request"),
    path("requests/<uuid:pk>/", SecureServiceTransactionDetailAPIView.as_view(), name="service-request-detail"),
    path("webhook/sanaacash/", SanaacashWebhookAPIView.as_view(), name="sanaacash-webhook"),
]
