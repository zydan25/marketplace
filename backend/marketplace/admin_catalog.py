from django.contrib import admin

from .models_extended import AuditLog, City
from .models_extra import CurrencyRate, VendorCityShipping


@admin.register(City)
class CityAdmin(admin.ModelAdmin):
    list_display = ("name", "price_group", "shipping_fee", "is_active", "updated_at")
    list_filter = ("is_active", "price_group")
    search_fields = ("name",)


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("created_at", "actor", "action", "model_name", "object_id", "ip_address")
    list_filter = ("action", "model_name", "created_at")
    search_fields = ("actor__phone", "model_name", "object_id", "action")
    readonly_fields = tuple(field.name for field in AuditLog._meta.fields)


@admin.register(CurrencyRate)
class CurrencyRateAdmin(admin.ModelAdmin):
    list_display = ("base_currency", "target_currency", "rate", "is_active", "updated_by", "updated_at")
    list_filter = ("is_active", "base_currency", "target_currency")
    search_fields = ("base_currency", "target_currency")
    list_editable = ("rate", "is_active")
    readonly_fields = ("created_at", "updated_at")


@admin.register(VendorCityShipping)
class VendorCityShippingAdmin(admin.ModelAdmin):
    list_display = ("vendor", "city", "fee", "is_active", "updated_at")
    list_filter = ("is_active", "city")
    list_editable = ("fee", "is_active")
    readonly_fields = ("created_at", "updated_at")
