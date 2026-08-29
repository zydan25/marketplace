from django.contrib import admin
from django.db import transaction
from django.urls import reverse
from django.utils import timezone
from django.utils.html import format_html

from .models_extra import GiftTransfer, Loan
from .models import Conversation, Coupon, DesignTheme, Message, Notification, Order, OrderItem, Referral, StorefrontSection, VendorPayout, Wallet, WalletTransaction
from .storefront_models import StorefrontMedia
from .marketplace_models import VendorLedgerEntry


@admin.register(DesignTheme)
class DesignThemeAdmin(admin.ModelAdmin):
    list_display = ("name", "vendor", "is_global", "is_active", "updated_at")
    list_filter = ("is_global", "is_active")
    search_fields = ("name",)


@admin.register(StorefrontSection)
class StorefrontSectionAdmin(admin.ModelAdmin):
    list_display = ("title", "section_type", "vendor", "sort_order", "is_visible", "visual_editor")
    list_filter = ("section_type", "is_visible", "vendor")
    search_fields = ("title",)
    ordering = ("sort_order", "id")

    @admin.display(description="المحرر البصري")
    def visual_editor(self, obj):
        return format_html('<a class="button" href="{}">فتح المحرر</a>', reverse("admin-storefront-editor"))


@admin.register(StorefrontMedia)
class StorefrontMediaAdmin(admin.ModelAdmin):
    list_display = ("name", "vendor", "is_active", "target_url", "updated_at")
    list_filter = ("is_active", "vendor")
    search_fields = ("name", "alt_text", "target_url", "vendor__store_name")
    raw_id_fields = ("vendor",)
    readonly_fields = ("created_at", "updated_at")

    def save_model(self, request, obj, form, change):
        obj.full_clean()
        super().save_model(request, obj, form, change)


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
    readonly_fields = ("wallet", "transaction_type", "amount", "balance_after", "reference", "note", "metadata", "created_at", "updated_at")


@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ("code", "discount_percent", "discount_amount", "minimum_order", "usage_limit", "used_count", "is_active", "starts_at", "ends_at")
    list_filter = ("is_active",)
    search_fields = ("code",)
    filter_horizontal = ("assigned_to",)


@admin.register(VendorPayout)
class VendorPayoutAdmin(admin.ModelAdmin):
    list_display = ("vendor", "vendor_order", "order", "amount", "currency", "status", "reference", "created_at")
    list_filter = ("status", "currency")
    search_fields = ("vendor__store_name", "reference")
    actions = ("approve_selected", "reject_selected", "pay_selected")

    @admin.action(description="اعتماد طلبات السحب")
    def approve_selected(self, request, queryset):
        queryset.filter(status="pending").update(status="approved", updated_at=timezone.now())

    @admin.action(description="رفض طلبات السحب")
    def reject_selected(self, request, queryset):
        queryset.filter(status__in=["pending", "approved"]).update(status="rejected", note="رُفض من الإدارة", updated_at=timezone.now())

    @admin.action(description="تسجيل دفع طلبات السحب")
    def pay_selected(self, request, queryset):
        with transaction.atomic():
            for payout in queryset.select_related("vendor").filter(status="approved"):
                if VendorLedgerEntry.objects.filter(reference=f"PAYOUT-{payout.id}").exists():
                    continue
                previous = VendorLedgerEntry.objects.filter(vendor=payout.vendor, currency=payout.currency).order_by("-id").first()
                before = previous.balance_after if previous else 0
                VendorLedgerEntry.objects.create(vendor=payout.vendor, entry_type=VendorLedgerEntry.Types.PAYOUT, amount=-payout.amount, balance_after=before - payout.amount, currency=payout.currency, reference=f"PAYOUT-{payout.id}", metadata={"admin": request.user.phone})
                payout.status = "paid"
                payout.save(update_fields=("status", "updated_at"))


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

from . import admin_marketplace  # noqa: E402,F401
