from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models_extra import GiftTransfer, Loan
from .models import (
    Category,
    Conversation,
    Coupon,
    DesignTheme,
    Message,
    Notification,
    Order,
    OrderItem,
    Product,
    Referral,
    StorefrontSection,
    User,
    VendorPayout,
    VendorProfile,
    Wallet,
    WalletTransaction,
)


@admin.register(User)
class MarketplaceUserAdmin(UserAdmin):
    list_display = ("phone", "get_full_name", "role", "governorate", "is_active", "date_joined")
    list_filter = ("role", "is_active", "is_phone_verified", "governorate")
    search_fields = ("phone", "first_name", "middle_name", "third_name", "last_name", "email")
    fieldsets = UserAdmin.fieldsets + (("ملف السوق", {"fields": ("phone", "role", "middle_name", "third_name", "governorate", "avatar", "is_phone_verified")}),)


@admin.register(VendorProfile)
class VendorProfileAdmin(admin.ModelAdmin):
    list_display = ("store_name", "owner", "status", "commission_percent", "created_at")
    list_filter = ("status",)
    search_fields = ("store_name", "owner__phone", "owner__email")
    prepopulated_fields = {"slug": ("store_name",)}


@admin.register(DesignTheme)
class DesignThemeAdmin(admin.ModelAdmin):
    list_display = ("name", "vendor", "is_global", "is_active", "updated_at")
    list_filter = ("is_global", "is_active")
    search_fields = ("name",)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "parent", "is_active", "sort_order")
    list_filter = ("is_active",)
    search_fields = ("name",)
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "sku", "vendor", "effective_price_display", "stock", "is_published", "is_trending")
    list_filter = ("is_published", "is_trending", "currency", "vendor")
    search_fields = ("name", "sku", "description", "vendor__store_name")
    filter_horizontal = ("categories",)
    prepopulated_fields = {"slug": ("name",)}

    @admin.display(description="السعر الحالي")
    def effective_price_display(self, obj):
        return obj.effective_price


@admin.register(StorefrontSection)
class StorefrontSectionAdmin(admin.ModelAdmin):
    list_display = ("title", "section_type", "vendor", "sort_order", "is_visible")
    list_filter = ("section_type", "is_visible", "vendor")
    search_fields = ("title",)


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ("name_snapshot", "sku_snapshot", "vendor_total", "commission", "vendor_net")


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("order_number", "customer", "status", "payment_status", "total", "currency", "created_at")
    list_filter = ("status", "payment_status", "currency")
    search_fields = ("order_number", "customer__phone")
    readonly_fields = ("order_number", "subtotal", "discount", "total")
    inlines = (OrderItemInline,)


@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = ("user", "balance", "currency", "is_locked", "updated_at")
    list_filter = ("currency", "is_locked")
    search_fields = ("user__phone", "user__email")


@admin.register(WalletTransaction)
class WalletTransactionAdmin(admin.ModelAdmin):
    list_display = ("wallet", "transaction_type", "amount", "balance_after", "reference", "created_at")
    list_filter = ("transaction_type", "created_at")
    search_fields = ("wallet__user__phone", "reference")


@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ("code", "discount_percent", "discount_amount", "is_active", "starts_at", "ends_at")
    list_filter = ("is_active",)
    search_fields = ("code",)
    filter_horizontal = ("assigned_to",)


@admin.register(VendorPayout)
class VendorPayoutAdmin(admin.ModelAdmin):
    list_display = ("vendor", "order", "amount", "status", "created_at")
    list_filter = ("status", "currency")
    search_fields = ("vendor__store_name", "reference")


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("title", "recipient", "product", "is_read", "created_at")
    list_filter = ("is_read", "created_at")
    search_fields = ("title", "body", "recipient__phone")


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ("customer", "vendor", "order", "is_closed", "updated_at")
    list_filter = ("is_closed", "vendor")
    search_fields = ("customer__phone", "subject")


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ("conversation", "sender", "is_read", "created_at")
    list_filter = ("is_read", "created_at")
    search_fields = ("sender__phone", "body")


@admin.register(Referral)
class ReferralAdmin(admin.ModelAdmin):
    list_display = ("inviter", "invitee", "code", "reward_amount", "reward_paid")
    list_filter = ("reward_paid",)
    search_fields = ("code", "inviter__phone", "invitee__phone")


@admin.register(Loan)
class LoanAdmin(admin.ModelAdmin):
    list_display = ("user", "amount", "status", "approved_by", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("user__phone", "reason")
    readonly_fields = ("created_at", "updated_at")


@admin.register(GiftTransfer)
class GiftTransferAdmin(admin.ModelAdmin):
    list_display = ("sender", "receiver", "amount", "status", "receiver_name_snapshot", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("sender__phone", "receiver__phone", "receiver_name_snapshot")
    readonly_fields = ("sender", "receiver", "amount", "receiver_name_snapshot", "created_at", "updated_at")
