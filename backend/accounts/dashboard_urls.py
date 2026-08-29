from django.urls import path

from .dashboard import (
    accounts_dashboard,
    user_action,
    user_create,
    user_detail,
    user_password,
    user_preferences_save,
    user_save,
    users_export_csv,
    users_list,
)


app_name = "accounts-dashboard"

urlpatterns = [
    path("", accounts_dashboard, name="home"),
    path("users/", users_list, name="users"),
    path("users/add/", user_create, name="user-create"),
    path("users/export.csv", users_export_csv, name="users-export"),
    path("users/<int:user_id>/", user_detail, name="user-detail"),
    path("users/<int:user_id>/save/", user_save, name="user-save"),
    path("users/<int:user_id>/action/<slug:action>/", user_action, name="user-action"),
    path("users/<int:user_id>/password/", user_password, name="user-password"),
    path("users/<int:user_id>/preferences/", user_preferences_save, name="user-preferences-save"),
]
