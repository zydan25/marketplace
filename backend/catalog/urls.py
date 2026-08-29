from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .api import CategoryViewSet, CatalogOptionViewSet, CatalogTreeView, PriceGroupViewSet, ProductImageViewSet, ProductViewSet, VariantViewSet

router = DefaultRouter()
router.register("categories", CategoryViewSet, basename="category")
router.register("products", ProductViewSet, basename="product")
router.register("variants", VariantViewSet, basename="variant")
router.register("product-images", ProductImageViewSet, basename="product-image")
router.register("catalog-options", CatalogOptionViewSet, basename="catalog-option")
router.register("price-groups", PriceGroupViewSet, basename="price-group")

urlpatterns = [
    path("catalog/tree/", CatalogTreeView.as_view(), name="catalog-tree"),
    path("", include(router.urls)),
]