from django.conf import settings
from django.db import models
from django.utils import timezone
from .wifi_denominations import WifiDenomination


class WifiCard(models.Model):
    class Status(models.TextChoices):
        AVAILABLE = "available", "متاح"
        SOLD = "sold", "مبيع"
        BLOCKED = "blocked", "موقوف"

    denomination = models.ForeignKey(WifiDenomination, on_delete=models.PROTECT, related_name="cards")
    card_number = models.CharField(max_length=120, unique=True)
    pin = models.CharField(max_length=120)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.AVAILABLE)
    sold_to = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT, related_name="purchased_wifi_cards")
    sold_at = models.DateTimeField(null=True, blank=True)
    sale_journal_id = models.PositiveIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["status", "id"]
        indexes = [
            models.Index(fields=["denomination", "status"], name="wifi_card_denom_status_idx"),
            models.Index(fields=["sold_to", "sold_at"], name="wifi_card_buyer_idx"),
        ]

    def __str__(self):
        return self.card_number
