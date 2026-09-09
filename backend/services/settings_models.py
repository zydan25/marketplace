from django.core.validators import MinValueValidator
from django.db import models


class ServiceSetting(models.Model):
    """Central configuration that maps stable setting keys to real Service IDs.

    Core service settings may be left unconfigured until the matching Service
    exists; the API marks them as unconfigured instead of inventing an ID.
    """

    class Types(models.TextChoices):
        SERVICE = "service", "خدمة"
        TEXT = "text", "نص"
        JSON = "json", "JSON"
        BOOLEAN = "boolean", "نعم/لا"

    key = models.SlugField(max_length=140, unique=True)
    name = models.CharField(max_length=220)
    group = models.SlugField(max_length=80, default="general")
    description = models.TextField(blank=True)
    setting_type = models.CharField(max_length=12, choices=Types.choices, default=Types.SERVICE)
    service = models.ForeignKey(
        "services.Service",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="service_settings",
    )
    value = models.JSONField(null=True, blank=True)
    is_system = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0, validators=[MinValueValidator(0)])
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["group", "sort_order", "id"]
        verbose_name = "إعداد خدمة"
        verbose_name_plural = "إعدادات الخدمات"
        indexes = [
            models.Index(fields=["group", "is_active", "sort_order"], name="svc_setting_group_idx"),
            models.Index(fields=["service", "is_active"], name="svc_setting_service_idx"),
        ]

    def __str__(self):
        return self.name

    @property
    def service_id_value(self):
        return self.service_id
