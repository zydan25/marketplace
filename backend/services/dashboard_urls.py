from django.urls import path

from .distribution_views import distribution_matrix_view, provider_setup
from .views import dashboard

urlpatterns = [
    path("", dashboard, name="admin-dashboard-services"),
    path("providers/", provider_setup, name="admin-services-provider-setup"),
    path("distribution/", distribution_matrix_view, name="admin-services-distribution"),
]
