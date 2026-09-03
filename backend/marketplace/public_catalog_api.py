from catalog.api import ProductViewSet
from catalog.models import Product


class MarketplaceProductViewSet(ProductViewSet):
    """Public marketplace products and explicit vendor inventory mode."""

    def get_queryset(self):
        user = self.request.user
        manage_own = self.request.query_params.get("mine") == "1"

        if self.action in {"list", "retrieve"} and not manage_own:
            return Product.objects.select_related("vendor", "vendor__owner").prefetch_related(
                "categories", "image_items", "variants"
            ).filter(is_published=True, vendor__status="active").distinct()

        if not user.is_authenticated:
            return super().get_queryset()
        if user.is_staff or getattr(user, "role", None) == "admin":
            return super().get_queryset()
        if getattr(user, "role", None) == "vendor":
            return Product.objects.select_related("vendor", "vendor__owner").prefetch_related(
                "categories", "image_items", "variants"
            ).filter(vendor__owner=user)
        return super().get_queryset()
