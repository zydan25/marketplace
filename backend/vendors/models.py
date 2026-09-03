from decimal import Decimal

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils.text import slugify


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class VendorProfile(TimeStampedModel):
    owner = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="vendor_profile")
    store_name = models.CharField(max_length=180)
    slug = models.SlugField(max_length=200, unique=True, blank=True)
    description = models.TextField(blank=True)
    logo = models.ImageField(upload_to="vendor/logos/", blank=True, null=True)
    cover = models.ImageField(upload_to="vendor/covers/", blank=True, null=True)
    phone = models.CharField(max_length=32, blank=True)
    address = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=20, choices=[("pending", "قيد المراجعة"), ("active", "نشط"), ("suspended", "موقوف")], default="pending")
    commission_percent = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("10.00"), validators=[MinValueValidator(0), MaxValueValidator(100)])
    settings = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "marketplace_vendorprofile"
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.store_name, allow_unicode=True)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.store_name


class VendorApplication(TimeStampedModel):
    class Status(models.TextChoices):
        PENDING = "pending", "قيد المراجعة"
        APPROVED = "approved", "مقبول"
        REJECTED = "rejected", "مرفوض"

    applicant = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="vendor_application")
    store_name = models.CharField(max_length=180)
    description = models.TextField(blank=True)
    phone = models.CharField(max_length=32)
    address = models.CharField(max_length=255, blank=True)
    documents = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    review_note = models.TextField(blank=True)
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="vendor_applications_reviewed")
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "marketplace_vendorapplication"
        ordering = ["-created_at"]
