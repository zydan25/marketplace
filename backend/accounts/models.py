from django.conf import settings
from django.db import models

from marketplace.models import User as MarketplaceUser


class User(MarketplaceUser):
    """Compatibility proxy until the custom AUTH_USER_MODEL is migrated separately."""

    class Meta:
        proxy = True
        verbose_name = "المستخدم"
        verbose_name_plural = "المستخدمون"


class UserPreference(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="preference")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    currency = models.CharField(max_length=6, default="YER")
    notifications_enabled = models.BooleanField(default=True)

    class Meta:
        db_table = "marketplace_userpreference"
        verbose_name = "تفضيل المستخدم"
        verbose_name_plural = "تفضيلات المستخدمين"
