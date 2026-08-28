from django.contrib import admin

from .models_extended import AuditLog, City, PriceGroup
from .models_extra import CatalogOption, CurrencyRate, UserPreference, VendorCityShipping


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


@admin.register(CatalogOption)
class CatalogOptionAdmin(admin.ModelAdmin):
    list_display = ("name", "group", "category", "sort_order", "is_active", "updated_at")
    list_filter = ("group", "is_active")
    search_fields = ("name", "slug")
    list_editable = ("sort_order", "is_active")
    ordering = ("group", "sort_order", "name")


@admin.register(CurrencyRate)
class CurrencyRateAdmin(admin.ModelAdmin):
    list_display = ("base_currency", "target_currency", "rate", "is_active", "updated_by", "updated_at")
    list_filter = ("is_active", "base_currency", "target_currency")
    search_fields = ("base_currency", "target_currency")
    list_editable = ("rate", "is_active")
    readonly_fields = ("created_at", "updated_at")


@admin.register(UserPreference)
class UserPreferenceAdmin(admin.ModelAdmin):
    list_display = ("user", "currency", "notifications_enabled", "updated_at")
    list_filter = ("currency", "notifications_enabled")
    readonly_fields = ("created_at", "updated_at")


@admin.register(VendorCityShipping)
class VendorCityShippingAdmin(admin.ModelAdmin):
    list_display = ("vendor", "city", "fee", "is_active", "updated_at")
    list_filter = ("is_active", "city")
    list_editable = ("fee", "is_active")
    readonly_fields = ("created_at", "updated_at")
