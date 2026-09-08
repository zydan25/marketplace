from django.urls import path

from .views import dashboard, section_view

urlpatterns = [
    path("", dashboard, name="admin-dashboard-services"),
    path("main/", section_view, {"section": "main"}, name="admin-services-main-categories"),
    path("categories/main/", section_view, {"section": "main"}, name="admin-services-main-alias"),
    path("categories/", section_view, {"section": "categories"}, name="admin-services-categories"),
    path("services/", section_view, {"section": "services"}, name="admin-services-list"),
    path("catalog/services/", section_view, {"section": "services"}, name="admin-services-catalog-services-alias"),
    path("fields/", section_view, {"section": "fields"}, name="admin-services-fields"),
    path("catalog/fields/", section_view, {"section": "fields"}, name="admin-services-catalog-fields-alias"),
    path("resources/", section_view, {"section": "resources"}, name="admin-services-resources"),
    path("catalog/resources/", section_view, {"section": "resources"}, name="admin-services-catalog-resources-alias"),
    path("providers/", section_view, {"section": "providers"}, name="admin-services-provider-setup"),
    path("links/", section_view, {"section": "links"}, name="admin-services-links"),
    path("distribution/", section_view, {"section": "distribution"}, name="admin-services-distribution"),
    path("transactions/", section_view, {"section": "transactions"}, name="admin-services-transactions"),
    path("operations/", section_view, {"section": "operations"}, name="admin-services-operations"),
    path("wifi/", section_view, {"section": "wifi"}, name="admin-services-wifi-management"),
]
