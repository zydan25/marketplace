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
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="sent_gifts")
    receiver = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="received_gifts")
    amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    points = models.PositiveIntegerField(default=0)
    message = models.TextField(blank=True)
