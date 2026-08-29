from django.db import models

from marketplace.models import User as MarketplaceUser
from marketplace.models_extra import UserPreference as MarketplaceUserPreference


class User(MarketplaceUser):
    """
    Transitional proxy for the existing marketplace_user table.

    The physical table and AUTH_USER_MODEL remain unchanged in the staged
    modularization. The Accounts app can therefore own authentication and
    administration without a destructive schema move.
    """

    class Meta:
        proxy = True
        verbose_name = "المستخدم"
        verbose_name_plural = "المستخدمون"


class UserPreference(MarketplaceUserPreference):
    """Proxy exposing account preferences through the Accounts domain."""

    class Meta:
        proxy = True
        verbose_name = "تفضيل المستخدم"
        verbose_name_plural = "تفضيلات المستخدمين"
