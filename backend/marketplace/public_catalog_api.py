from catalog.api import ProductViewSet


class MarketplaceProductViewSet(ProductViewSet):
    """One product endpoint with an explicit public-vs-management mode.

    Normal list/retrieve requests always represent the public marketplace and
    therefore return published products from active stores, even when the
    caller is logged in as a vendor. Vendor management screens must send
    `mine=1` to receive their own private inventory.
    """

    def get_queryset(self):
        user = self.request.user
        manage_own = self.request.query_params.get("mine") == "1"

        if self.action in {"list", "retrieve"} and not manage_own:
            qs = self.queryset
            if qs is None:
                qs = self.model.objects.all()
            qs = qs.select_related("vendor", "vendor__owner").prefetch_related("categories", "image_items", "variants")
            return qs.filter(is_published=True, vendor__status="active").distinct()

        if not user.is_authenticated:
            return super().get_queryset()

        if user.is_staff or getattr(user, "role", None) == "admin":
            return super().get_queryset()

        if getattr(user, "role", None) == "vendor":
            qs = self.model.objects.select_related("vendor", "vendor__owner").prefetch_related("categories", "image_items", "variants")
            return qs.filter(vendor__owner=user)

        return super().get_queryset()
