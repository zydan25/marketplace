from django.contrib import admin

from .models import Address, Coupon, CouponRedemption, GiftTransfer, Loan, Referral


@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ("code", "discount_percent", "discount_amount", "minimum_order", "used_count", "usage_limit", "is_active")
    list_filter = ("is_active",)
    search_fields = ("code",)


@admin.register(CouponRedemption)
class CouponRedemptionAdmin(admin.ModelAdmin):
    list_display = ("coupon", "order", "user", "discount_amount", "currency", "created_at")
    search_fields = ("code_snapshot", "order__order_number", "user__phone", "coupon__code")


@admin.register(Referral)
class ReferralAdmin(admin.ModelAdmin):
    list_display = ("code", "inviter", "invitee", "reward_amount", "reward_paid", "created_at")
    list_filter = ("reward_paid",)
    search_fields = ("code", "inviter__phone", "invitee__phone", "inviter__username", "invitee__username")


@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = ("user", "title", "city", "district", "phone", "is_default", "updated_at")
    list_filter = ("is_default", "city")
    search_fields = ("user__phone", "title", "district", "street", "phone")


@admin.register(Loan)
class LoanAdmin(admin.ModelAdmin):
    list_display = ("user", "amount", "status", "approved_by", "created_at", "updated_at")
    list_filter = ("status",)
    search_fields = ("user__phone", "user__username", "reason")


@admin.register(GiftTransfer)
class GiftTransferAdmin(admin.ModelAdmin):
    list_display = ("sender", "receiver", "amount", "points", "status", "created_at")
    list_filter = ("status",)
    search_fields = ("sender__phone", "receiver__phone", "receiver_name_snapshot", "message")
