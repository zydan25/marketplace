from django.conf import settings
from django.db import models

from catalog.models import City, PriceGroup, ProductVariant
from orders.models import OrderStatusHistory


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class AuditLog(TimeStampedModel):
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    action = models.CharField(max_length=100)
    model_name = models.CharField(max_length=100)
    object_id = models.CharField(max_length=100)
    old_value = models.JSONField(null=True, blank=True)
    new_value = models.JSONField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        db_table = "marketplace_auditlog"
        verbose_name = "سجل تدقيق"
        verbose_name_plural = "سجلات التدقيق"


__all__ = ["AuditLog", "City", "PriceGroup", "ProductVariant", "OrderStatusHistory", "TimeStampedModel"]
