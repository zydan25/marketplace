from django.urls import path

from .api import ServiceCatalogAPIView, ServiceDetailAPIView, ServiceRequestAPIView, ServiceTransactionDetailAPIView

urlpatterns = [
    path("catalog/", ServiceCatalogAPIView.as_view(), name="service-catalog"),
    path("services/<int:pk>/", ServiceDetailAPIView.as_view(), name="service-detail"),
    path("requests/", ServiceRequestAPIView.as_view(), name="service-request"),
    path("requests/<uuid:pk>/", ServiceTransactionDetailAPIView.as_view(), name="service-request-detail"),
]
