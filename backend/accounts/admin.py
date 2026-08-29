from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)
class AccountsUserAdmin(UserAdmin):
    list_display = (
        "phone",
        "get_full_name",
        "role",
        "governorate",
        "is_active",
        "date_joined",
    )
    list_filter = (
        "role",
        "is_active",
        "is_phone_verified",
        "governorate",
    )
    search_fields = (
        "phone",
        "first_name",
        "middle_name",
        "third_name",
        "last_name",
        "email",
    )
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
                )
            },
        ),
    )
