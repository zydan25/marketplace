from django.urls import path

from .admin_v4 import center, distribution
from .dashboard_resource_catalog_v11 import dashboard_resources
from .operations_dashboard import balances_dashboard, operations_dashboard
from .provider_setup_v3 import provider_setup
from .service_dashboard_home import modern_home
from .settings_admin import settings_center
from .views import section_view
from .wifi_dashboard import wifi_management
from .service_platform_v2 import package_manager_v2, services_v2_home, settings_v2, integration_docs_v2

urlpatterns = [
    path("", modern_home, name="admin-dashboard-services"),
    path("main/", center, {"section": "main"}, name="admin-services-main-categories"),
    path("categories/", center, {"section": "categories"}, name="admin-services-categories"),
    path("categories/main/", center, {"section": "main"}, name="admin-services-categories-main-alias"),
    path("services/", center, {"section": "services"}, name="admin-services-list"),
    path("catalog/services/", center, {"section": "services"}, name="admin-services-catalog-services-alias"),
    path("fields/", center, {"section": "fields"}, name="admin-services-fields"),
    path("catalog/fields/", center, {"section": "fields"}, name="admin-services-catalog-fields-alias"),
    path("resources/", dashboard_resources, name="admin-services-resources"),
    path("catalog/resources/", dashboard_resources, name="admin-services-catalog-resources-alias"),
    path("providers/", provider_setup, name="admin-services-provider-setup"),
    path("links/", section_view, {"section": "links"}, name="admin-services-links"),
    path("distribution/", distribution, name="admin-services-distribution"),
    path("transactions/", section_view, {"section": "transactions"}, name="admin-services-transactions"),
    path("operations/", operations_dashboard, name="admin-services-operations"),
    path("balances/", balances_dashboard, name="admin-services-balances"),
    path("wifi/", wifi_management, name="admin-services-wifi-management"),
    path("settings/", settings_center, name="admin-services-settings"),
    path("v2/", services_v2_home, name="services-v2-home"),
    path("v2/packages/<slug:package_key>/", package_manager_v2, name="services-v2-package-manager"),
    path("v2/settings/", settings_v2, name="services-v2-settings"),
    path("v2/docs/", integration_docs_v2, name="services-v2-docs"),
]
