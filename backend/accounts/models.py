from django.db import models

from marketplace.models import User as MarketplaceUser


class User(MarketplaceUser):
    """
    Transitional proxy for the existing marketplace_user table.

    Stage 1 intentionally keeps AUTH_USER_MODEL and the physical table
    unchanged. This lets the Accounts app own the account boundary before
    performing a separate, state-only migration of the concrete User model.
    """

    class Meta:
        proxy = True
        verbose_name = "المستخدم"
        verbose_name_plural = "المستخدمون"
