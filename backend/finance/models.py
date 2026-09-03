from decimal import Decimal

from django.conf import settings
from django.db import models


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Wallet(TimeStampedModel):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="wallet")
    balance = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    currency = models.CharField(max_length=6, default="YER")
    is_locked = models.BooleanField(default=False)

    class Meta:
        db_table = "marketplace_wallet"


class WalletTransaction(TimeStampedModel):
    class Types(models.TextChoices):
        TOP_UP = "top_up", "شحن رصيد"
        PAYMENT = "payment", "دفع"
        REFUND = "refund", "استرداد"
        REWARD = "reward", "مكافأة"
        WITHDRAWAL = "withdrawal", "سحب"
        ADJUSTMENT = "adjustment", "تسوية"

    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name="transactions")
    transaction_type = models.CharField(max_length=20, choices=Types.choices)
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    balance_after = models.DecimalField(max_digits=14, decimal_places=2)
    reference = models.CharField(max_length=120, blank=True)
    note = models.CharField(max_length=255, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "marketplace_wallettransaction"


class VendorLedgerEntry(models.Model):
    class Types(models.TextChoices):
        SALE = "sale", "بيع"
        COMMISSION = "commission", "عمولة"
        REFUND = "refund", "استرداد"
        PAYOUT = "payout", "سحب"
        ADJUSTMENT = "adjustment", "تسوية"

    created_at = models.DateTimeField(auto_now_add=True)
    vendor = models.ForeignKey("vendors.VendorProfile", on_delete=models.PROTECT, related_name="ledger_entries")
    vendor_order = models.ForeignKey("orders.VendorOrder", on_delete=models.PROTECT, null=True, blank=True, related_name="ledger_entries")
    entry_type = models.CharField(max_length=30, choices=Types.choices)
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    balance_after = models.DecimalField(max_digits=14, decimal_places=2)
    currency = models.CharField(max_length=6, default="YER")
    reference = models.CharField(max_length=160, unique=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "marketplace_vendorledgerentry"


class VendorPayout(TimeStampedModel):
    vendor = models.ForeignKey("vendors.VendorProfile", on_delete=models.PROTECT, related_name="payouts")
    vendor_order = models.ForeignKey("orders.VendorOrder", on_delete=models.PROTECT, related_name="payouts", null=True, blank=True)
    order = models.ForeignKey("orders.Order", on_delete=models.PROTECT, related_name="payouts", null=True, blank=True)
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    currency = models.CharField(max_length=6, default="YER")
    status = models.CharField(max_length=20, choices=[("pending", "معلق"), ("approved", "معتمد"), ("paid", "مدفوع"), ("rejected", "مرفوض")], default="pending")
    reference = models.CharField(max_length=120, blank=True)
    note = models.TextField(blank=True)

    class Meta:
        db_table = "marketplace_vendorpayout"


class CurrencyRate(TimeStampedModel):
    base_currency = models.CharField(max_length=6, default="YER")
    target_currency = models.CharField(max_length=6)
    rate = models.DecimalField(max_digits=18, decimal_places=8, default=Decimal("1.00000000"))
    is_active = models.BooleanField(default=True)
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="currency_rates_updated")

    class Meta:
        db_table = "marketplace_currencyrate"
        constraints = [models.UniqueConstraint(fields=["base_currency", "target_currency"], name="uniq_currency_rate_pair")]
        ordering = ["base_currency", "target_currency"]


class VendorCityShipping(TimeStampedModel):
    vendor = models.ForeignKey("vendors.VendorProfile", on_delete=models.CASCADE, related_name="city_shipping_fees")
    city = models.ForeignKey("catalog.City", on_delete=models.CASCADE, related_name="vendor_shipping_fees")
    fee = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "marketplace_vendorcityshipping"
        constraints = [models.UniqueConstraint(fields=["vendor", "city"], name="uniq_vendor_city_shipping")]
        indexes = [models.Index(fields=["vendor", "city", "is_active"], name="vcs_vendor_city_active_idx")]


__all__ = ["CurrencyRate", "VendorCityShipping", "VendorLedgerEntry", "VendorPayout", "Wallet", "WalletTransaction"]
