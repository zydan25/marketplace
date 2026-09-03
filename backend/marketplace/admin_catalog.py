from django.contrib import admin

from .models_extended import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("created_at", "actor", "action", "model_name", "object_id", "ip_address")
    list_filter = ("action", "model_name", "created_at")
    search_fields = ("actor__phone", "model_name", "object_id", "action")
    readonly_fields = tuple(field.name for field in AuditLog._meta.fields)
