from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Roles(models.TextChoices):
        CUSTOMER = "customer", "عميل"
        VENDOR = "vendor", "تاجر"
        ADMIN = "admin", "مدير"

    username = models.CharField(max_length=150, unique=True, blank=True, null=True)
    phone = models.CharField(max_length=32, unique=True, null=True, blank=True)
    role = models.CharField(max_length=20, choices=Roles.choices, default=Roles.CUSTOMER)
    first_name = models.CharField(max_length=80, blank=True)
    middle_name = models.CharField(max_length=80, blank=True)
    third_name = models.CharField(max_length=80, blank=True)
    last_name = models.CharField(max_length=80, blank=True)
    governorate = models.CharField(max_length=80, blank=True)
    avatar = models.ImageField(upload_to="avatars/", blank=True, null=True)
    is_phone_verified = models.BooleanField(default=False)
    points_balance = models.PositiveIntegerField(default=0)

    def save(self, *args, **kwargs):
        if not self.username:
            self.username = self.phone or None
        super().save(*args, **kwargs)

    def __str__(self):
        return self.get_full_name() or self.phone or self.username or str(self.pk)


# Compatibility aliases. New code must import models from their owning domain app.
from catalog.models import Category, PriceGroup, City, Product, ProductImage, ProductVariant, CatalogOption  # noqa: E402,F401
from vendors.models import VendorProfile, VendorApplication  # noqa: E402,F401
from storefront.models import DesignTheme, StorefrontSection, StorefrontMedia  # noqa: E402,F401
from orders.models import Order, OrderItem, VendorOrder, VendorOrderItem, OrderStatusHistory, Shipment, InventoryReservation, Payment  # noqa: E402,F401
from finance.models import Wallet, WalletTransaction, VendorPayout, VendorLedgerEntry, CurrencyRate, VendorCityShipping  # noqa: E402,F401
from communication.models import Notification, Conversation, Message  # noqa: E402,F401
from promotions.models import Coupon, CouponRedemption, Referral, Address, Loan, GiftTransfer  # noqa: E402,F401
from .models_extended import AuditLog  # noqa: E402,F401


__all__ = [
    "Address", "AuditLog", "Category", "CatalogOption", "City", "Conversation", "Coupon", "CouponRedemption",
    "CurrencyRate", "DesignTheme", "GiftTransfer", "InventoryReservation", "Loan", "Message", "Notification",
    "Order", "OrderItem", "OrderStatusHistory", "Payment", "PriceGroup", "Product", "ProductImage", "ProductVariant",
    "Referral", "Shipment", "StorefrontMedia", "StorefrontSection", "User", "VendorApplication", "VendorCityShipping",
    "VendorLedgerEntry", "VendorOrder", "VendorOrderItem", "VendorPayout", "VendorProfile", "Wallet", "WalletTransaction",
]
