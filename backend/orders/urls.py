from django.urls import path
from rest_framework.routers import DefaultRouter

from .api import (
    OrderItemViewSet,
    OrderViewSet,
    PaymentViewSet,
    ReservationViewSet,
    ShipmentViewSet,
    StatusHistoryViewSet,
    VendorOrderItemViewSet,
    VendorOrderViewSet,
    api_info,
)

router = DefaultRouter()
router.register("orders", OrderViewSet, basename="order")
router.register("order-items", OrderItemViewSet, basename="order-item")
router.register("vendor-orders", VendorOrderViewSet, basename="vendor-order")
router.register("vendor-order-items", VendorOrderItemViewSet, basename="vendor-order-item")
router.register("status-history", StatusHistoryViewSet, basename="order-status-history")
router.register("shipments", ShipmentViewSet, basename="shipment")
router.register("inventory-reservations", ReservationViewSet, basename="inventory-reservation")
router.register("payments", PaymentViewSet, basename="payment")

urlpatterns = [path("", api_info, name="orders-api-info")]
urlpatterns += router.urls
