from rest_framework.routers import DefaultRouter
from django.urls import path

from .api import MediaViewSet, PublicStorefrontView, SectionViewSet, ThemeViewSet, api_info

router = DefaultRouter()
router.register("themes", ThemeViewSet, basename="storefront-theme")
router.register("sections", SectionViewSet, basename="storefront-section")
router.register("media", MediaViewSet, basename="storefront-media")

urlpatterns = [
    path("", api_info, name="storefront-api-info"),
    path("public/", PublicStorefrontView.as_view(), name="storefront-public"),
    path("public/<slug:vendor_slug>/", PublicStorefrontView.as_view(), name="storefront-public-vendor"),
]
urlpatterns += router.urls
