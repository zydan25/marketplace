from decimal import Decimal
from django.db import models
from django.conf import settings
from .models_extended import City, TimeStampedModel

class Address(TimeStampedModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="addresses")
    title = models.CharField(max_length=100)
    city = models.ForeignKey(City, on_delete=models.PROTECT)
    district = models.CharField(max_length=100, blank=True)
    street = models.CharField(max_length=200, blank=True)
    building = models.CharField(max_length=100, blank=True)
    phone = models.CharField(max_length=32)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    is_default = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        if self.is_default:
            Address.objects.filter(user=self.user).update(is_default=False)
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


class CatalogOption(TimeStampedModel):
    """Configurable product attribute option controlled from the marketplace backend."""
    group = models.CharField(max_length=60)
    name = models.CharField(max_length=160)
    slug = models.SlugField(max_length=180)
    category = models.ForeignKey("marketplace.Category", on_delete=models.CASCADE, null=True, blank=True, related_name="catalog_options")
    sort_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["group", "sort_order", "name", "id"]
        constraints = [models.UniqueConstraint(fields=["group", "slug", "category"], name="uniq_catalog_option_group_slug_category")]
        indexes = [models.Index(fields=["group", "is_active"]), models.Index(fields=["category", "group", "is_active"])]


class CurrencyRate(TimeStampedModel):
    base_currency = models.CharField(max_length=6, default="YER")
    target_currency = models.CharField(max_length=6)
    rate = models.DecimalField(max_digits=18, decimal_places=8, default=Decimal("1.00000000"))
    is_active = models.BooleanField(default=True)
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="currency_rates_updated")

    class Meta:
        constraints = [models.UniqueConstraint(fields=["base_currency", "target_currency"], name="uniq_currency_rate_pair")]
        ordering = ["base_currency", "target_currency"]


class UserPreference(TimeStampedModel):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="preference")
    currency = models.CharField(max_length=6, default="YER")
    notifications_enabled = models.BooleanField(default=True)


class VendorCityShipping(TimeStampedModel):
    vendor = models.ForeignKey("marketplace.VendorProfile", on_delete=models.CASCADE, related_name="city_shipping_fees")
    city = models.ForeignKey(City, on_delete=models.CASCADE, related_name="vendor_shipping_fees")
    fee = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["vendor", "city"], name="uniq_vendor_city_shipping")]
        indexes = [models.Index(fields=["vendor", "city", "is_active"])]
