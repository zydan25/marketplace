from django.urls import path

from .admin_v4 import center, distribution
from .provider_setup_v3 import provider_setup
from .views import section_view

urlpatterns = [
    path("", center, {"section": "overview"}, name="admin-dashboard-services"),
    path("main/", center, {"section": "main"}, name="admin-services-main-categories"),
    path("categories/", center, {"section": "categories"}, name="admin-services-categories"),
    path("categories/main/", center, {"section": "main"}, name="admin-services-categories-main-alias"),
    path("services/", center, {"section": "services"}, name="admin-services-list"),
    path("catalog/services/", center, {"section": "services"}, name="admin-services-catalog-services-alias"),
    path("fields/", center, {"section": "fields"}, name="admin-services-fields"),
    path("catalog/fields/", center, {"section": "fields"}, name="admin-services-catalog-fields-alias"),
    path("resources/", center, {"section": "resources"}, name="admin-services-resources"),
    path("catalog/resources/", center, {"section": "resources"}, name="admin-services-catalog-resources-alias"),
    path("providers/", provider_setup, name="admin-services-provider-setup"),
    path("links/", section_view, {"section": "links"}, name="admin-services-links"),
    path("distribution/", distribution, name="admin-services-distribution"),
    path("transactions/", section_view, {"section": "transactions"}, name="admin-services-transactions"),
]
