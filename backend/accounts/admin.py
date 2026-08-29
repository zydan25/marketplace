from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User, UserPreference


@admin.register(User)
class AccountsUserAdmin(UserAdmin):
    list_display = (
        "phone",
        "get_full_name",
        "role",
        "governorate",
        "is_active",
        "is_phone_verified",
        "is_staff",
        "date_joined",
    )
    list_filter = (
        "role",
        "is_active",
        "is_phone_verified",
        "is_staff",
        "governorate",
    )
    search_fields = (
        "phone",
        "username",
        "first_name",
        "middle_name",
        "third_name",
        "last_name",
        "email",
    )
    ordering = ("-date_joined",)
    fieldsets = UserAdmin.fieldsets + (
        (
            "ملف السوق",
            {
                "fields": (
                    "phone",
                    "role",
                    "middle_name",
                    "third_name",
                    "governorate",
                    "avatar",
                    "is_phone_verified",
                    "points_balance",
                )
            },
        ),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        (
            "ملف السوق",
            {
                "classes": ("wide",),
                "fields": (
                    "phone",
                    "role",
                    "first_name",
                    "middle_name",
                    "third_name",
                    "last_name",
                    "governorate",
                    "email",
                    "points_balance",
                    "is_phone_verified",
                ),
            },
        ),
    )


@admin.register(UserPreference)
class UserPreferenceAdmin(admin.ModelAdmin):
    list_display = ("user", "currency", "notifications_enabled", "updated_at")
    list_filter = ("currency", "notifications_enabled")
    search_fields = (
        "user__phone",
        "user__username",
        "user__email",
        "user__first_name",
        "user__last_name",
    )
    raw_id_fields = ("user",)
    readonly_fields = ("created_at", "updated_at")
