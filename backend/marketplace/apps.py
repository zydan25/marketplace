from django.apps import AppConfig


class MarketplaceConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "marketplace"

    def ready(self):
        from . import marketplace_models  # noqa: F401
        from . import storefront_models  # noqa: F401
