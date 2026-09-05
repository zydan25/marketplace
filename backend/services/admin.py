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
    ServiceOption,
    ServiceRequestReference,
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
    list_display = ("name", "code", "category", "service_kind", "requires_balance", "pricing_mode", "price", "currency", "is_active")
    list_filter = ("is_active", "service_kind", "requires_balance", "pricing_mode", "currency")
    search_fields = ("name", "code")
    inlines = [ServiceFieldInline, ServiceDistributionInline]


@admin.register(ProviderConnection)
class ProviderConnectionAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "connection_type", "base_url", "userid", "is_active")
    list_filter = ("connection_type", "is_active")
    search_fields = ("name", "code", "base_url", "userid", "domain_name", "username")
    exclude = ("password_encrypted",)
    readonly_fields = ("created_at", "updated_at")


@admin.register(ProviderLink)
class ProviderLinkAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "provider", "operation", "http_method", "request_encoding", "priority", "is_active")
    list_filter = ("http_method", "request_encoding", "is_active")
    search_fields = ("name", "code", "operation", "path_template")


@admin.register(ServiceOption)
class ServiceOptionAdmin(admin.ModelAdmin):
    list_display = ("name", "service", "external_code", "provider_num", "price", "currency", "is_active")
    list_filter = ("is_active", "currency")
    search_fields = ("name", "external_code", "provider_num", "service__code")


@admin.register(ServiceRequestReference)
class ServiceRequestReferenceAdmin(admin.ModelAdmin):
    list_display = ("transid", "provider", "transaction", "request_kind", "created_at")
    list_filter = ("request_kind", "provider")
    search_fields = ("transid", "transaction__id")
    readonly_fields = ("transid", "provider", "transaction", "request_kind", "created_at")


admin.site.register(MainServiceCategory)
admin.site.register(ServiceCategory)
admin.site.register(ServiceDistribution)
admin.site.register(TelecomDenomination)
admin.site.register(TelecomPlan)
admin.site.register(GameProduct)
admin.site.register(DigitalProduct)
admin.site.register(ServiceTransaction)
admin.site.register(ServiceTask)
