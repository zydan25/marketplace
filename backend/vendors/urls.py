from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .api import VendorApplicationViewSet, VendorViewSet

router = DefaultRouter()
router.register("vendors", VendorViewSet, basename="vendor")
router.register("vendor-applications", VendorApplicationViewSet, basename="vendor-application")

urlpatterns = [path("", include(router.urls))]
