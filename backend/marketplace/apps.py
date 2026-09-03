from django.apps import AppConfig


class MarketplaceConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "marketplace"

    def ready(self):
        # Compatibility imports retained for legacy module paths and signals.
        from . import marketplace_models  # noqa: F401
        from . import storefront_models  # noqa: F401
        from . import order_chat_models  # noqa: F401
