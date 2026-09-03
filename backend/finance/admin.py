from django.contrib import admin

from .models import CurrencyRate, VendorCityShipping, VendorLedgerEntry, VendorPayout, Wallet, WalletTransaction


@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = ("user", "balance", "currency", "is_locked", "updated_at")
    list_filter = ("currency", "is_locked")
    search_fields = ("user__phone", "user__username", "user__first_name", "user__last_name")


@admin.register(WalletTransaction)
class WalletTransactionAdmin(admin.ModelAdmin):
    list_display = ("wallet", "transaction_type", "amount", "balance_after", "created_at")
    list_filter = ("transaction_type",)
    search_fields = ("wallet__user__phone", "reference", "note")
    readonly_fields = ("wallet", "transaction_type", "amount", "balance_after", "reference", "note", "metadata", "created_at", "updated_at")


@admin.register(VendorPayout)
class VendorPayoutAdmin(admin.ModelAdmin):
    list_display = ("vendor", "amount", "currency", "status", "reference", "created_at")
    list_filter = ("status", "currency")
    search_fields = ("vendor__store_name", "reference", "note")


@admin.register(VendorLedgerEntry)
class VendorLedgerEntryAdmin(admin.ModelAdmin):
    list_display = ("vendor", "entry_type", "amount", "balance_after", "currency", "reference", "created_at")
    list_filter = ("entry_type", "currency")
    search_fields = ("vendor__store_name", "reference")
    readonly_fields = tuple(field.name for field in VendorLedgerEntry._meta.fields)


@admin.register(CurrencyRate)
class CurrencyRateAdmin(admin.ModelAdmin):
    list_display = ("base_currency", "target_currency", "rate", "is_active", "updated_at")
    list_filter = ("base_currency", "target_currency", "is_active")
    search_fields = ("base_currency", "target_currency")


@admin.register(VendorCityShipping)
class VendorCityShippingAdmin(admin.ModelAdmin):
    list_display = ("vendor", "city", "fee", "is_active", "updated_at")
    list_filter = ("is_active",)
    search_fields = ("vendor__store_name", "city__name")
