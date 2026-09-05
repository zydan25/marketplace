from django.contrib import admin

from .models import (
    DigitalProduct,
    GameProduct,
    MainServiceCategory,
    ProviderConnection,
    ProviderLink,
    Service,
    ServiceCategory,
    ServiceDistribution,
    ServiceField,
    ServiceTask,
    ServiceTransaction,
    TelecomDenomination,
    TelecomPlan,
)


class ServiceFieldInline(admin.TabularInline):
    model = ServiceField
    extra = 0


class ServiceDistributionInline(admin.TabularInline):
    model = ServiceDistribution
    extra = 0


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "category", "pricing_mode", "price", "currency", "is_active")
    list_filter = ("is_active", "pricing_mode", "currency")
    search_fields = ("name", "code")
    inlines = [ServiceFieldInline, ServiceDistributionInline]


@admin.register(ProviderConnection)
class ProviderConnectionAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "connection_type", "base_url", "is_active")
    list_filter = ("connection_type", "is_active")
    search_fields = ("name", "code", "base_url", "userid")
    exclude = ("password_encrypted",)
    readonly_fields = ("created_at", "updated_at")


@admin.register(ProviderLink)
class ProviderLinkAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "provider", "operation", "http_method", "priority", "is_active")
    list_filter = ("http_method", "is_active")
    search_fields = ("name", "code", "operation", "path_template")


admin.site.register(MainServiceCategory)
admin.site.register(ServiceCategory)
admin.site.register(ServiceDistribution)
admin.site.register(TelecomDenomination)
admin.site.register(TelecomPlan)
admin.site.register(GameProduct)
admin.site.register(DigitalProduct)
admin.site.register(ServiceTransaction)
admin.site.register(ServiceTask)
