from decimal import Decimal
from django.core.validators import MinValueValidator
from django.db import models
from .wifi_networks import WifiNetwork


class WifiDenomination(models.Model):
    network = models.ForeignKey(WifiNetwork, on_delete=models.CASCADE, related_name="denominations")
    name = models.CharField(max_length=160)
    denomination_number = models.CharField(max_length=80)
    face_value = models.DecimalField(max_digits=18, decimal_places=2, validators=[MinValueValidator(Decimal("0"))])
    sale_price = models.DecimalField(max_digits=18, decimal_places=2, validators=[MinValueValidator(Decimal("0"))])
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["face_value", "id"]
        constraints = [models.UniqueConstraint(fields=["network", "denomination_number"], name="uniq_wifi_network_denom_number")]
        indexes = [models.Index(fields=["network", "is_active"], name="wifi_denom_network_active_idx")]

    def __str__(self):
        return f"{self.network.name} - {self.name}"
