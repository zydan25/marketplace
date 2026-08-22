from django.contrib import admin
from django.utils import timezone

from .marketplace_models import CouponRedemption, InventoryReservation, Payment, Shipment, VendorApplication, VendorLedgerEntry, VendorOrder, VendorOrderItem
from .models import VendorProfile
from .order_chat_models import OrderChat, OrderChatMessage


@admin.register(VendorApplication)
class VendorApplicationAdmin(admin.ModelAdmin):
    list_display = ("store_name", "applicant", "phone", "status", "created_at", "reviewed_at")
    list_filter = ("status", "created_at")
    search_fields = ("store_name", "phone", "applicant__phone", "applicant__email")
    readonly_fields = ("applicant", "created_at", "updated_at", "reviewed_by", "reviewed_at")
    actions = ("approve_selected", "reject_selected")

    @admin.action(description="اعتماد التجار المحددين")
    def approve_selected(self, request, queryset):
        for application in queryset.filter(status=VendorApplication.Status.PENDING).select_related("applicant"):
            user = application.applicant
            user.role = "vendor"
            user.save(update_fields=["role"])
            VendorProfile.objects.get_or_create(owner=user, defaults={"store_name": application.store_name, "description": application.description, "phone": application.phone, "address": application.address, "status": "active"})
            application.status = VendorApplication.Status.APPROVED
            application.reviewed_by = request.user
            application.reviewed_at = timezone.now()
            application.save(update_fields=["status", "reviewed_by", "reviewed_at", "updated_at"])

    @admin.action(description="رفض طلبات التجار المحددين")
    def reject_selected(self, request, queryset):
        queryset.filter(status=VendorApplication.Status.PENDING).update(status=VendorApplication.Status.REJECTED, reviewed_by=request.user, reviewed_at=timezone.now())


class VendorOrderItemInline(admin.TabularInline):
    model = VendorOrderItem
    extra = 0
    readonly_fields = ("order_item",)


@admin.register(VendorOrder)
class VendorOrderAdmin(admin.ModelAdmin):
    list_display = ("order_number", "vendor", "order", "status", "total", "vendor_net", "currency", "created_at")
    list_filter = ("status", "currency", "created_at")
    search_fields = ("order_number", "vendor__store_name", "order__order_number")
    readonly_fields = ("order", "vendor", "order_number", "subtotal", "shipping_fee", "discount", "total", "commission", "vendor_net", "currency")
    inlines = (VendorOrderItemInline,)


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("order", "provider", "method", "amount", "currency", "status", "paid_at")
    list_filter = ("provider", "method", "status", "currency")
    search_fields = ("order__order_number", "transaction_id")
    readonly_fields = ("order", "provider", "method", "transaction_id", "amount", "refunded_amount", "currency", "status", "paid_at", "metadata")


@admin.register(Shipment)
class ShipmentAdmin(admin.ModelAdmin):
    list_display = ("vendor_order", "carrier", "tracking_number", "status", "shipped_at", "delivered_at")
    list_filter = ("status", "carrier")
    search_fields = ("vendor_order__order_number", "tracking_number", "carrier")


@admin.register(InventoryReservation)
class InventoryReservationAdmin(admin.ModelAdmin):
    list_display = ("order", "order_item", "product", "variant", "quantity", "status", "expires_at")
    list_filter = ("status", "created_at")
    search_fields = ("order__order_number", "product__name", "variant__sku")
    readonly_fields = ("order", "order_item", "product", "variant", "quantity", "created_at", "updated_at", "expires_at")


@admin.register(VendorLedgerEntry)
class VendorLedgerEntryAdmin(admin.ModelAdmin):
    list_display = ("vendor", "vendor_order", "entry_type", "amount", "balance_after", "currency", "reference", "created_at")
    list_filter = ("entry_type", "currency", "created_at")
    search_fields = ("vendor__store_name", "reference", "vendor_order__order_number")
    readonly_fields = tuple(field.name for field in VendorLedgerEntry._meta.fields)


@admin.register(CouponRedemption)
class CouponRedemptionAdmin(admin.ModelAdmin):
    list_display = ("coupon", "code_snapshot", "user", "order", "discount_amount", "currency", "created_at")
    list_filter = ("currency", "created_at")
    search_fields = ("code_snapshot", "coupon__code", "user__phone", "order__order_number")
    readonly_fields = tuple(field.name for field in CouponRedemption._meta.fields)


@admin.register(OrderChat)
class OrderChatAdmin(admin.ModelAdmin):
    list_display = ("order", "vendor", "customer", "is_closed", "updated_at")
    list_filter = ("is_closed", "vendor")
    search_fields = ("order__order_number", "vendor__store_name", "customer__phone")
    readonly_fields = ("order", "vendor_order", "vendor", "customer", "created_at", "updated_at")
    ordering = ("-updated_at",)


@admin.register(OrderChatMessage)
class OrderChatMessageAdmin(admin.ModelAdmin):
    list_display = ("chat", "sender", "is_read", "created_at")
    list_filter = ("is_read", "created_at")
    search_fields = ("chat__order__order_number", "sender__phone", "body")
    readonly_fields = ("chat", "sender", "created_at")
