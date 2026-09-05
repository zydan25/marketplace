from django.urls import path

from .distribution_views import distribution_matrix_view, provider_setup
from .views import dashboard, section_view

urlpatterns = [
    path("", dashboard, name="admin-dashboard-services"),
    path("categories/main/", section_view, {"section": "main"}, name="admin-services-main-categories"),
    path("categories/", section_view, {"section": "categories"}, name="admin-services-categories"),
    path("catalog/services/", section_view, {"section": "services"}, name="admin-services-list"),
    path("catalog/fields/", section_view, {"section": "fields"}, name="admin-services-fields"),
    path("catalog/resources/", section_view, {"section": "resources"}, name="admin-services-resources"),
    path("providers/", provider_setup, name="admin-services-provider-setup"),
    path("links/", section_view, {"section": "links"}, name="admin-services-links"),
    path("distribution/", distribution_matrix_view, name="admin-services-distribution"),
    path("transactions/", section_view, {"section": "transactions"}, name="admin-services-transactions"),
]
