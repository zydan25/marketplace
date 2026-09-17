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


class VendorCategory(TimeStampedModel):
    vendor = models.ForeignKey(VendorProfile, on_delete=models.CASCADE, related_name="store_categories")
    name = models.CharField(max_length=140)
    slug = models.SlugField(max_length=170)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to="vendor/categories/", blank=True, null=True)
    parent = models.ForeignKey("self", on_delete=models.CASCADE, null=True, blank=True, related_name="children")
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "marketplace_vendorcategory"
        ordering = ["sort_order", "name", "id"]
        constraints = [models.UniqueConstraint(fields=["vendor", "slug"], name="uniq_vendor_category_slug")]
        indexes = [
            models.Index(fields=["vendor", "is_active"], name="vendorcat_vendor_active_idx"),
            models.Index(fields=["vendor", "parent", "sort_order"], name="vendorcat_tree_idx"),
        ]

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.name, allow_unicode=True) or "category"
            candidate = base
            counter = 2
            while type(self).objects.filter(vendor=self.vendor, slug=candidate).exclude(pk=self.pk).exists():
                candidate = f"{base}-{counter}"
                counter += 1
            self.slug = candidate[:170]
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.vendor.store_name} / {self.name}"


class VendorBranch(TimeStampedModel):
    vendor = models.ForeignKey(VendorProfile, on_delete=models.CASCADE, related_name="branches")
    name = models.CharField(max_length=160)
    code = models.CharField(max_length=60)
    manager_name = models.CharField(max_length=160, blank=True)
    phone = models.CharField(max_length=32, blank=True)
    governorate = models.CharField(max_length=100, blank=True)
    address = models.CharField(max_length=255, blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    opening_hours = models.JSONField(default=dict, blank=True)
    is_main = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "marketplace_vendorbranch"
        ordering = ["-is_main", "name", "id"]
        constraints = [models.UniqueConstraint(fields=["vendor", "code"], name="uniq_vendor_branch_code")]
        indexes = [
            models.Index(fields=["vendor", "is_active"], name="vendorbranch_vendor_active_idx"),
            models.Index(fields=["vendor", "is_main"], name="vendorbranch_vendor_main_idx"),
        ]

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.is_main:
            type(self).objects.filter(vendor=self.vendor).exclude(pk=self.pk).update(is_main=False)

    def __str__(self):
        return f"{self.vendor.store_name} / {self.name}"


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
