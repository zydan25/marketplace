from django.urls import path

from .admin_v4 import center, distribution
from .provider_setup_v3 import provider_setup
from .resource_admin_v6 import resources

urlpatterns = [
    path("", center, name="legacy-services-home"),
    path("main/", center, {"section": "main"}, name="legacy-services-main"),
    path("categories/", center, {"section": "categories"}, name="legacy-services-categories"),
    path("services/", center, {"section": "services"}, name="legacy-services-list"),
    path("fields/", center, {"section": "fields"}, name="legacy-services-fields"),
    path("resources/", resources, name="legacy-services-resources"),
    path("providers/", provider_setup, name="legacy-services-providers"),
    path("distribution/", distribution, name="legacy-services-distribution"),
]
