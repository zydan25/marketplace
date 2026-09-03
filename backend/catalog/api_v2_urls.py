from django.urls import path
from rest_framework.routers import DefaultRouter

from .api import CategoryViewSet, CatalogOptionViewSet, CatalogTreeView, PriceGroupViewSet, ProductImageViewSet, VariantViewSet
from marketplace.public_catalog_api import MarketplaceProductViewSet

router = DefaultRouter()
router.register("categories", CategoryViewSet, basename="category")
router.register("products", MarketplaceProductViewSet, basename="product")
router.register("variants", VariantViewSet, basename="variant")
router.register("product-images", ProductImageViewSet, basename="product-image")
router.register("catalog-options", CatalogOptionViewSet, basename="catalog-option")
router.register("price-groups", PriceGroupViewSet, basename="price-group")

urlpatterns = [path("tree/", CatalogTreeView.as_view(), name="catalog-tree-v2")]
urlpatterns += router.urls
