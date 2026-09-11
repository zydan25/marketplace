from django.urls import path

from .admin_v4 import center, distribution
from .provider_setup_v3 import provider_setup
from .resource_catalog_v8 import catalog_resources
from .service_admin_v6 import services
from .settings_admin import settings_center
from .service_platform_v2 import package_manager_v2, services_v2_home, settings_v2, integration_docs_v2

urlpatterns = [
    path("", center, name="legacy-services-home"),
    path("main/", center, {"section": "main"}, name="legacy-services-main"),
    path("categories/", center, {"section": "categories"}, name="legacy-services-categories"),
    path("services/", services, name="legacy-services-list"),
    path("fields/", center, {"section": "fields"}, name="legacy-services-fields"),
    path("resources/", catalog_resources, name="legacy-services-resources"),
    path("resources/games-cards/", catalog_resources, {"type": "entertainment"}, name="legacy-services-games-cards"),
    path("catalog/resources/", catalog_resources, name="legacy-services-catalog-resources"),
    path("catalog/games-cards/", catalog_resources, {"type": "entertainment"}, name="legacy-services-catalog-games-cards"),
    path("providers/", provider_setup, name="legacy-services-providers"),
    path("distribution/", distribution, name="legacy-services-distribution"),
    path("settings/", settings_center, name="legacy-services-settings"),
    path("v2/", services_v2_home, name="services-v2-home"),
    path("v2/packages/<slug:package_key>/", package_manager_v2, name="services-v2-package-manager"),
    path("v2/settings/", settings_v2, name="services-v2-settings"),
    path("v2/docs/", integration_docs_v2, name="services-v2-docs"),
]
