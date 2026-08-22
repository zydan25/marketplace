from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models


class VendorOrder(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "قيد الانتظار"
        CONFIRMED = "confirmed", "مؤكد"
        PROCESSING = "processing", "قيد التجهيز"
        SHIPPED = "shipped", "تم الشحن"
        DELIVERED = "delivered", "تم التسليم"
        CANCELLED = "cancelled", "ملغي"
        REFUNDED = "refunded", "مسترد"
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    order = models.ForeignKey("marketplace.Order", on_delete=models.CASCADE, related_name="vendor_orders")
    vendor = models.ForeignKey("marketplace.VendorProfile", on_delete=models.PROTECT, related_name="vendor_orders")
    order_number = models.CharField(max_length=60, unique=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    subtotal = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"), validators=[MinValueValidator(0)])
    shipping_fee = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"), validators=[MinValueValidator(0)])
    discount = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"), validators=[MinValueValidator(0)])
    total = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"), validators=[MinValueValidator(0)])
    commission = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"), validators=[MinValueValidator(0)])
    vendor_net = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"), validators=[MinValueValidator(0)])
    currency = models.CharField(max_length=6, default="YER")
    class Meta:
        ordering = ["-created_at"]
        constraints = [models.UniqueConstraint(fields=["order", "vendor"], name="uniq_vendor_order_per_vendor")]
        indexes = [models.Index(fields=["vendor", "status"]), models.Index(fields=["order", "status"])]


class VendorOrderItem(models.Model):
    vendor_order = models.ForeignKey(VendorOrder, on_delete=models.CASCADE, related_name="items")
    order_item = models.OneToOneField("marketplace.OrderItem", on_delete=models.PROTECT, related_name="vendor_order_item")


class Payment(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "قيد الانتظار"
        AUTHORIZED = "authorized", "مصرح"
        PAID = "paid", "مدفوع"
        FAILED = "failed", "فشل"
        REFUNDED = "refunded", "مسترد"
        PARTIALLY_REFUNDED = "partially_refunded", "مسترد جزئيًا"
        CANCELLED = "cancelled", "ملغي"
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    order = models.OneToOneField("marketplace.Order", on_delete=models.PROTECT, related_name="payment")
    provider = models.CharField(max_length=60, default="manual")
    method = models.CharField(max_length=60, default="cash_on_delivery")
    transaction_id = models.CharField(max_length=160, unique=True, null=True, blank=True)
    amount = models.DecimalField(max_digits=14, decimal_places=2, validators=[MinValueValidator(0)])
    refunded_amount = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"), validators=[MinValueValidator(0)])
    currency = models.CharField(max_length=6, default="YER")
    status = models.CharField(max_length=30, choices=Status.choices, default=Status.PENDING)
    paid_at = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)


class Shipment(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "قيد الانتظار"
        READY = "ready", "جاهز"
        SHIPPED = "shipped", "تم الشحن"
        IN_TRANSIT = "in_transit", "في الطريق"
        DELIVERED = "delivered", "تم التسليم"
        RETURNED = "returned", "مرتجع"
        CANCELLED = "cancelled", "ملغي"
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    vendor_order = models.OneToOneField(VendorOrder, on_delete=models.PROTECT, related_name="shipment")
    carrier = models.CharField(max_length=120, blank=True)
    tracking_number = models.CharField(max_length=160, blank=True)
    status = models.CharField(max_length=30, choices=Status.choices, default=Status.PENDING)
    shipped_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)


class InventoryReservation(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "نشط"
        COMMITTED = "committed", "مثبت"
        RELEASED = "released", "محرر"
        EXPIRED = "expired", "منتهي"
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    expires_at = models.DateTimeField()
    order = models.ForeignKey("marketplace.Order", on_delete=models.CASCADE, related_name="inventory_reservations")
    order_item = models.ForeignKey("marketplace.OrderItem", on_delete=models.PROTECT, null=True, blank=True, related_name="inventory_reservations")
    product = models.ForeignKey("marketplace.Product", on_delete=models.PROTECT, null=True, blank=True, related_name="inventory_reservations")
    variant = models.ForeignKey("marketplace.ProductVariant", on_delete=models.PROTECT, null=True, blank=True, related_name="inventory_reservations")
    quantity = models.PositiveIntegerField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    class Meta:
        indexes = [models.Index(fields=["order", "status"]), models.Index(fields=["order_item", "status"]), models.Index(fields=["expires_at", "status"])]


class VendorLedgerEntry(models.Model):
    class Types(models.TextChoices):
        SALE = "sale", "بيع"
        COMMISSION = "commission", "عمولة"
        REFUND = "refund", "استرداد"
        PAYOUT = "payout", "سحب"
        ADJUSTMENT = "adjustment", "تسوية"
    created_at = models.DateTimeField(auto_now_add=True)
    vendor = models.ForeignKey("marketplace.VendorProfile", on_delete=models.PROTECT, related_name="ledger_entries")
    vendor_order = models.ForeignKey(VendorOrder, on_delete=models.PROTECT, null=True, blank=True, related_name="ledger_entries")
    entry_type = models.CharField(max_length=30, choices=Types.choices)
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    balance_after = models.DecimalField(max_digits=14, decimal_places=2)
    currency = models.CharField(max_length=6, default="YER")
    reference = models.CharField(max_length=160, unique=True)
    metadata = models.JSONField(default=dict, blank=True)


class CouponRedemption(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    coupon = models.ForeignKey("marketplace.Coupon", on_delete=models.PROTECT, related_name="redemptions")
    order = models.OneToOneField("marketplace.Order", on_delete=models.PROTECT, related_name="coupon_redemption")
    user = models.ForeignKey("marketplace.User", on_delete=models.PROTECT, related_name="coupon_redemptions")
    code_snapshot = models.CharField(max_length=50)
    discount_amount = models.DecimalField(max_digits=14, decimal_places=2, validators=[MinValueValidator(0)])
    currency = models.CharField(max_length=6, default="YER")
    class Meta:
        indexes = [models.Index(fields=["coupon", "user"]), models.Index(fields=["created_at"])]
