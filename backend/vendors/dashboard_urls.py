from django.urls import path

from .dashboard import (
    application_action,
    application_detail,
    applications,
    export_csv,
    overview,
    vendor_create,
    vendor_detail,
    vendor_status,
    vendor_update,
    vendors,
)

app_name = "vendors-dashboard"

urlpatterns = [
    path("", overview, name="home"),
    path("vendors/", vendors, name="vendors"),
    path("vendors/add/", vendor_create, name="vendor-create"),
    path("vendors/<int:vendor_id>/", vendor_detail, name="vendor-detail"),
    path("vendors/<int:vendor_id>/edit/", vendor_update, name="vendor-update"),
    path("vendors/<int:vendor_id>/status/<str:status>/", vendor_status, name="vendor-status"),
    path("applications/", applications, name="applications"),
    path("applications/<int:application_id>/", application_detail, name="application-detail"),
    path("applications/<int:application_id>/<str:action>/", application_action, name="application-action"),
    path("export.csv", export_csv, name="export"),
]
