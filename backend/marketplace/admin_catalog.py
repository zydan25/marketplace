from django.contrib import admin

from .models_extended import AuditLog, City, PriceGroup


@admin.register(PriceGroup)
class PriceGroupAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "adjustment_type", "percentage", "fixed_amount", "is_active", "updated_at")
    list_filter = ("adjustment_type", "is_active")
    search_fields = ("name", "code")


@admin.register(City)
class CityAdmin(admin.ModelAdmin):
    list_display = ("name", "price_group", "shipping_fee", "is_active", "updated_at")
    list_filter = ("is_active", "price_group")
    search_fields = ("name",)
    autocomplete_fields = ("price_group",)


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("created_at", "actor", "action", "model_name", "object_id", "ip_address")
    list_filter = ("action", "model_name", "created_at")
    search_fields = ("actor__phone", "model_name", "object_id", "action")
    readonly_fields = tuple(field.name for field in AuditLog._meta.fields)
