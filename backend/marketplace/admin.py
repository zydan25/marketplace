from django.contrib import admin

from .models import User
from .models_extended import AuditLog


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ("username", "phone", "role", "is_active", "is_staff", "is_phone_verified", "date_joined")
    list_filter = ("role", "is_active", "is_staff", "is_phone_verified")
    search_fields = ("username", "phone", "email", "first_name", "last_name")
    ordering = ("-date_joined",)


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("created_at", "actor", "action", "model_name", "object_id", "ip_address")
    list_filter = ("action", "model_name", "created_at")
    search_fields = ("actor__phone", "model_name", "object_id", "action")
    readonly_fields = tuple(field.name for field in AuditLog._meta.fields)


from . import admin_marketplace  # noqa: E402,F401
