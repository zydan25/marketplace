from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Order(TimeStampedModel):
    class Status(models.TextChoices):
        PENDING = "pending", "قيد الانتظار"
        CONFIRMED = "confirmed", "مؤكد"
        PROCESSING = "processing", "قيد التجهيز"
        SHIPPED = "shipped", "تم الشحن"
        PARTIALLY_FULFILLED = "partially_fulfilled", "منفذ جزئيًا"
        DELIVERED = "delivered", "تم التسليم"
        CANCELLED = "cancelled", "ملغي"
        REFUNDED = "refunded", "مسترد"

    customer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="orders")
    order_number = models.CharField(max_length=40, unique=True)
    status = models.CharField(max_length=24, choices=Status.choices, default=Status.PENDING)
    subtotal = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    shipping_fee = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    discount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    currency = models.CharField(max_length=6, default="YER")
    shipping_address = models.JSONField(default=dict, blank=True)
    payment_method = models.CharField(max_length=40, default="cash_on_delivery")
    payment_status = models.CharField(max_length=20, default="pending")
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "marketplace_order"
        ordering = ["-created_at"]


class OrderItem(TimeStampedModel):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    vendor = models.ForeignKey("vendors.VendorProfile", on_delete=models.PROTECT, related_name="order_items")
    product = models.ForeignKey("catalog.Product", on_delete=models.PROTECT, related_name="order_items")
    name_snapshot = models.CharField(max_length=220)
    sku_snapshot = models.CharField(max_length=80)
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=14, decimal_places=2)
    color = models.CharField(max_length=80, blank=True)
    size = models.CharField(max_length=80, blank=True)
    vendor_total = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    commission = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    vendor_net = models.DecimalField(max_digits=14, decimal_places=2, default=0)

    class Meta:
        db_table = "marketplace_orderitem"


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
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="vendor_orders")
    vendor = models.ForeignKey("vendors.VendorProfile", on_delete=models.PROTECT, related_name="vendor_orders")
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
        db_table = "marketplace_vendororder"
        ordering = ["-created_at"]
        constraints = [models.UniqueConstraint(fields=["order", "vendor"], name="uniq_vendor_order_per_vendor")]
        indexes = [
            models.Index(fields=["vendor", "status"], name="marketplace_vendor__ad2742_idx"),
            models.Index(fields=["order", "status"], name="marketplace_order_i_55497d_idx"),
        ]


class VendorOrderItem(models.Model):
    vendor_order = models.ForeignKey(VendorOrder, on_delete=models.CASCADE, related_name="items")
    order_item = models.OneToOneField(OrderItem, on_delete=models.PROTECT, related_name="vendor_order_item")

    class Meta:
        db_table = "marketplace_vendororderitem"


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
    order = models.OneToOneField(Order, on_delete=models.PROTECT, related_name="payment")
    provider = models.CharField(max_length=60, default="manual")
    method = models.CharField(max_length=60, default="cash_on_delivery")
    transaction_id = models.CharField(max_length=160, unique=True, null=True, blank=True)
    amount = models.DecimalField(max_digits=14, decimal_places=2, validators=[MinValueValidator(0)])
    refunded_amount = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"), validators=[MinValueValidator(0)])
    currency = models.CharField(max_length=6, default="YER")
    status = models.CharField(max_length=30, choices=Status.choices, default=Status.PENDING)
    paid_at = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "marketplace_payment"


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

    class Meta:
        db_table = "marketplace_shipment"


class InventoryReservation(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "نشط"
        COMMITTED = "committed", "مثبت"
        RELEASED = "released", "محرر"
        EXPIRED = "expired", "منتهي"

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    expires_at = models.DateTimeField()
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="inventory_reservations")
    order_item = models.ForeignKey(OrderItem, on_delete=models.PROTECT, related_name="inventory_reservations", null=True, blank=True)
    product = models.ForeignKey("catalog.Product", on_delete=models.PROTECT, null=True, blank=True, related_name="inventory_reservations")
    variant = models.ForeignKey("catalog.ProductVariant", on_delete=models.PROTECT, null=True, blank=True, related_name="inventory_reservations")
    quantity = models.PositiveIntegerField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)

    class Meta:
        db_table = "marketplace_inventoryreservation"
        indexes = [
            models.Index(fields=["order", "status"], name="marketplace_order_i_511a97_idx"),
            models.Index(fields=["expires_at", "status"], name="marketplace_expires_8e06c7_idx"),
        ]


class OrderStatusHistory(TimeStampedModel):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="status_history")
    old_status = models.CharField(max_length=50)
    new_status = models.CharField(max_length=50)
    changed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    note = models.TextField(blank=True)

    class Meta:
        db_table = "marketplace_orderstatushistory"


__all__ = [
    "InventoryReservation", "Order", "OrderItem", "OrderStatusHistory", "Payment", "Shipment", "VendorOrder", "VendorOrderItem",
]
