from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
from django.db import models


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class DesignTheme(TimeStampedModel):
    owner = models.ForeignKey("marketplace.User", on_delete=models.CASCADE, related_name="design_themes", null=True, blank=True)
    vendor = models.OneToOneField("vendors.VendorProfile", on_delete=models.CASCADE, related_name="theme", null=True, blank=True)
    name = models.CharField(max_length=120)
    is_global = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    tokens = models.JSONField(default=dict, blank=True)
    layout = models.JSONField(default=dict, blank=True)
    sections = models.JSONField(default=list, blank=True)

    class Meta:
        db_table = "marketplace_designtheme"
        ordering = ["-is_global", "-updated_at"]


class StorefrontSection(TimeStampedModel):
    class SectionTypes(models.TextChoices):
        HERO = "hero", "عرض رئيسي"
        CATEGORY = "category", "فئات"
        PRODUCT_GRID = "product_grid", "شبكة منتجات"
        TREND = "trend", "ترند"
        BANNER = "banner", "بانر"

    owner = models.ForeignKey("marketplace.User", on_delete=models.CASCADE, related_name="storefront_sections")
    vendor = models.ForeignKey("vendors.VendorProfile", on_delete=models.CASCADE, related_name="storefront_sections", null=True, blank=True)
    title = models.CharField(max_length=180, blank=True)
    section_type = models.CharField(max_length=30, choices=SectionTypes.choices)
    config = models.JSONField(default=dict, blank=True)
    sort_order = models.PositiveIntegerField(default=0)
    is_visible = models.BooleanField(default=True)

    class Meta:
        db_table = "marketplace_storefrontsection"
        ordering = ["sort_order", "id"]


class StorefrontMedia(TimeStampedModel):
    name = models.CharField(max_length=180)
    image = models.ImageField(upload_to="storefront/")
    alt_text = models.CharField(max_length=180, blank=True)
    target_url = models.CharField(max_length=500, blank=True)
    vendor = models.ForeignKey("vendors.VendorProfile", on_delete=models.CASCADE, null=True, blank=True, related_name="storefront_media")
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0, db_index=True)

    class Meta:
        db_table = "marketplace_storefrontmedia"
        ordering = ["sort_order", "-updated_at", "id"]
        indexes = [models.Index(fields=["vendor", "is_active"])]

    def clean(self):
        if self.target_url.startswith("http"):
            URLValidator()(self.target_url)
        elif self.target_url and not self.target_url.startswith("/"):
            raise ValidationError({"target_url": "استخدم رابطًا داخليًا يبدأ بـ / أو رابط HTTP/HTTPS."})

    def __str__(self):
        return self.name
