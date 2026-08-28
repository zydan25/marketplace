from django.apps import AppConfig


class MarketplaceConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "marketplace"

    def ready(self):
        from . import marketplace_models  # noqa: F401
        from . import storefront_models  # noqa: F401
        from . import order_chat_models  # noqa: F401
        from . import secure_catalog
        from . import admin_catalog  # noqa: F401
        from .secure_vendor_catalog import VendorDesignThemeViewSet, VendorProductViewSet, VendorStorefrontSectionViewSet

        # Replace the compatibility classes before Django URL configuration imports them.
        secure_catalog.SecureProductViewSet = VendorProductViewSet
        secure_catalog.SecureDesignThemeViewSet = VendorDesignThemeViewSet
        secure_catalog.SecureStorefrontSectionViewSet = VendorStorefrontSectionViewSet
