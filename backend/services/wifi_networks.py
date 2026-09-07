from decimal import Decimal
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models


class WifiNetwork(models.Model):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="owned_wifi_networks")
    name = models.CharField(max_length=180)
    location = models.CharField(max_length=300)
    management_percent = models.DecimalField(max_digits=6, decimal_places=2, default=0, validators=[MinValueValidator(Decimal("0")), MaxValueValidator(Decimal("100"))])
    latitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    longitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name", "id"]
        indexes = [models.Index(fields=["is_active", "name"], name="wifi_network_active_idx")]

    def __str__(self):
        return self.name
