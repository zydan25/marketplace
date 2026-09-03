from decimal import Decimal

from django.conf import settings
from django.db import models


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Coupon(TimeStampedModel):
    code = models.CharField(max_length=50, unique=True)
    discount_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    discount_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    minimum_order = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    usage_limit = models.PositiveIntegerField(null=True, blank=True)
    used_count = models.PositiveIntegerField(default=0)
    starts_at = models.DateTimeField(null=True, blank=True)
    ends_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    assigned_to = models.ManyToManyField(settings.AUTH_USER_MODEL, blank=True, related_name="coupons", db_table="marketplace_coupon_assigned_to")

    class Meta:
        db_table = "marketplace_coupon"


class CouponRedemption(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    coupon = models.ForeignKey(Coupon, on_delete=models.PROTECT, related_name="redemptions")
    order = models.OneToOneField("orders.Order", on_delete=models.PROTECT, related_name="coupon_redemption")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="coupon_redemptions")
    code_snapshot = models.CharField(max_length=50)
    discount_amount = models.DecimalField(max_digits=14, decimal_places=2)
    currency = models.CharField(max_length=6, default="YER")

    class Meta:
        db_table = "marketplace_couponredemption"
        indexes = [models.Index(fields=["coupon", "user"]), models.Index(fields=["created_at"])]


class Referral(TimeStampedModel):
    inviter = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="referrals_sent")
    invitee = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="referral_source")
    code = models.CharField(max_length=32, unique=True)
    reward_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    reward_paid = models.BooleanField(default=False)

    class Meta:
        db_table = "marketplace_referral"


class Address(TimeStampedModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="addresses")
    title = models.CharField(max_length=100)
    city = models.ForeignKey("catalog.City", on_delete=models.PROTECT)
    district = models.CharField(max_length=100, blank=True)
    street = models.CharField(max_length=200, blank=True)
    building = models.CharField(max_length=100, blank=True)
    phone = models.CharField(max_length=32)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    is_default = models.BooleanField(default=False)

    class Meta:
        db_table = "marketplace_address"

    def save(self, *args, **kwargs):
        if self.is_default:
            type(self).objects.filter(user=self.user).update(is_default=False)
        super().save(*args, **kwargs)


class Loan(TimeStampedModel):
    class Status(models.TextChoices):
        PENDING = "pending", "قيد الانتظار"
        APPROVED = "approved", "موافق عليه"
        REJECTED = "rejected", "مرفوض"
        PAID = "paid", "مسدد"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="loans")
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    reason = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="approved_loans")

    class Meta:
        db_table = "marketplace_loan"


class GiftTransfer(TimeStampedModel):
    class Status(models.TextChoices):
        PENDING = "pending", "قيد التأكيد"
        COMPLETED = "completed", "مكتمل"
        CANCELLED = "cancelled", "ملغى"

    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="sent_gifts")
    receiver = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="received_gifts")
    amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    points = models.PositiveIntegerField(default=0)
    message = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    receiver_name_snapshot = models.CharField(max_length=255, blank=True)

    class Meta:
        db_table = "marketplace_gifttransfer"


__all__ = ["Address", "Coupon", "CouponRedemption", "GiftTransfer", "Loan", "Referral"]
