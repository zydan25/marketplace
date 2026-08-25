from decimal import Decimal
from django.db import models
from django.conf import settings
from django.utils.text import slugify
import uuid


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        abstract = True


class PriceGroup(TimeStampedModel):
    name = models.CharField(max_length=120)
    code = models.CharField(max_length=50, unique=True)
    adjustment_type = models.CharField(max_length=20, choices=[("percentage", "نسبة مئوية"), ("fixed", "مبلغ ثابت")])
    percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    fixed_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)


class City(TimeStampedModel):
    class Meta:
        ordering = ["name"]
        indexes = [models.Index(fields=["is_active", "name"])]
    name = models.CharField(max_length=120)
    price_group = models.ForeignKey(PriceGroup, on_delete=models.SET_NULL, null=True, blank=True)
    shipping_fee = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)


class ProductVariant(TimeStampedModel):
    product = models.ForeignKey("marketplace.Product", on_delete=models.CASCADE, related_name="variants")
    sku = models.CharField(max_length=80, unique=True, blank=True)
    color = models.CharField(max_length=80, blank=True)
    size = models.CharField(max_length=80, blank=True)
    price_override = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    stock = models.PositiveIntegerField(default=0)
    reserved_stock = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        indexes = [models.Index(fields=["product", "stock"]), models.Index(fields=["product", "color", "size"]), models.Index(fields=["product", "is_active"])]

    @property
    def available_stock(self):
        if not self.is_active:
            return 0
        return max(0, self.stock - self.reserved_stock)

    def save(self, *args, **kwargs):
        if not self.sku:
            product_sku = getattr(self.product, "sku", "") or "PRODUCT"
            color = slugify(self.color, allow_unicode=False).replace("-", "")[:20].upper()
            size = slugify(self.size, allow_unicode=False).replace("-", "")[:20].upper()
            dimensions = "-".join(part for part in (color, size) if part)
            base = f"{product_sku}-{dimensions}" if dimensions else f"{product_sku}-VAR"
            base = base[:70]
            candidate = base
            counter = 2
            while ProductVariant.objects.filter(sku=candidate).exclude(pk=self.pk).exists():
                suffix = f"-{counter}"
                candidate = f"{base[:80-len(suffix)]}{suffix}"
                counter += 1
            self.sku = candidate or f"VAR-{uuid.uuid4().hex[:12].upper()}"
        super().save(*args, **kwargs)


class OrderStatusHistory(TimeStampedModel):
    order = models.ForeignKey("marketplace.Order", on_delete=models.CASCADE, related_name="status_history")
    old_status = models.CharField(max_length=50)
    new_status = models.CharField(max_length=50)
    changed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    note = models.TextField(blank=True)


class AuditLog(TimeStampedModel):
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    action = models.CharField(max_length=100)
    model_name = models.CharField(max_length=100)
    object_id = models.CharField(max_length=100)
    old_value = models.JSONField(null=True, blank=True)
    new_value = models.JSONField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
