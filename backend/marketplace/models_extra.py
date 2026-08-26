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
        if self.is_default: Address.objects.filter(user=self.user).update(is_default=False)
        super().save(*args, **kwargs)

class Loan(TimeStampedModel):
    class Status(models.TextChoices):
        PENDING = "pending", "قيد الانتظار"; APPROVED = "approved", "موافق عليه"; REJECTED = "rejected", "مرفوض"; PAID = "paid", "مسدد"
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="loans")
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    reason = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="approved_loans")

class GiftTransfer(TimeStampedModel):
    class Status(models.TextChoices):
        PENDING = "pending", "قيد التأكيد"; COMPLETED = "completed", "مكتمل"; CANCELLED = "cancelled", "ملغى"
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="sent_gifts")
    receiver = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="received_gifts")
    amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    points = models.PositiveIntegerField(default=0)
    message = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    receiver_name_snapshot = models.CharField(max_length=255, blank=True)

class WalletHold(TimeStampedModel):
    class Status(models.TextChoices):
        HELD = "held", "معلق"; RELEASED = "released", "مطلق"; REFUNDED = "refunded", "مسترد"; PARTIAL = "partial", "مسترد جزئيًا"; CANCELLED = "cancelled", "ملغي"
    wallet = models.ForeignKey("marketplace.Wallet", on_delete=models.PROTECT, related_name="holds")
    order = models.OneToOneField("marketplace.Order", on_delete=models.PROTECT, related_name="wallet_hold")
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    released_amount = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    refunded_amount = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.HELD)
    note = models.CharField(max_length=255, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

class ServiceCategory(TimeStampedModel):
    name = models.CharField(max_length=160)
    parent = models.ForeignKey("self", on_delete=models.CASCADE, null=True, blank=True, related_name="children")
    image = models.ImageField(upload_to="services/categories/", null=True, blank=True)
    description = models.TextField(blank=True)
    sort_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    class Meta:
        ordering = ["sort_order", "name", "id"]
        constraints = [models.UniqueConstraint(fields=["parent", "name"], name="uniq_service_category_name_per_parent")]

class Service(TimeStampedModel):
    name = models.CharField(max_length=220)
    slug = models.SlugField(max_length=250, unique=True, blank=True)
    category = models.ForeignKey(ServiceCategory, on_delete=models.PROTECT, related_name="services")
    image = models.ImageField(upload_to="services/", null=True, blank=True)
    banner = models.ImageField(upload_to="services/banners/", null=True, blank=True)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    currency = models.CharField(max_length=6, default="YER")
    is_active = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    sort_order = models.PositiveIntegerField(default=0)
    config = models.JSONField(default=dict, blank=True)
    class Meta: ordering = ["sort_order", "name", "id"]
    def save(self, *args, **kwargs):
        if not self.slug:
            from django.utils.text import slugify
            base = slugify(self.name, allow_unicode=True) or "service"; candidate = base; counter = 2
            while Service.objects.filter(slug=candidate).exclude(pk=self.pk).exists(): candidate = f"{base}-{counter}"; counter += 1
            self.slug = candidate
        super().save(*args, **kwargs)

class ServiceField(TimeStampedModel):
    class FieldTypes(models.TextChoices):
        TEXT="text","نص"; TEXTAREA="textarea","وصف"; NUMBER="number","رقم"; PHONE="phone","هاتف"; DATE="date","تاريخ"; SELECT="select","اختيار"; MULTISELECT="multiselect","اختيار متعدد"; IMAGE="image","رفع صورة"; FILE="file","رفع ملف"; CHECKBOX="checkbox","مربع اختيار"
    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name="fields")
    key = models.SlugField(max_length=100); label = models.CharField(max_length=180); field_type = models.CharField(max_length=30, choices=FieldTypes.choices, default=FieldTypes.TEXT)
    placeholder = models.CharField(max_length=220, blank=True); help_text = models.CharField(max_length=300, blank=True); is_required = models.BooleanField(default=False); options = models.JSONField(default=list, blank=True); sort_order = models.PositiveIntegerField(default=0)
    class Meta:
        ordering = ["sort_order", "id"]; constraints = [models.UniqueConstraint(fields=["service", "key"], name="uniq_service_field_key")]

class ServiceSubmission(TimeStampedModel):
    class Status(models.TextChoices):
        PENDING="pending","قيد التنفيذ"; PROCESSING="processing","قيد المعالجة"; COMPLETED="completed","مكتمل"; REJECTED="rejected","مرفوض"; REFUNDED="refunded","مسترد"
    service = models.ForeignKey(Service, on_delete=models.PROTECT, related_name="submissions")
    customer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="service_submissions")
    amount = models.DecimalField(max_digits=14, decimal_places=2); currency = models.CharField(max_length=6, default="YER")
    data = models.JSONField(default=dict, blank=True); status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING); notes = models.TextField(blank=True); reference = models.CharField(max_length=80, unique=True)

class VendorCityShipping(TimeStampedModel):
    vendor = models.ForeignKey("marketplace.VendorProfile", on_delete=models.CASCADE, related_name="city_shipping_fees")
    city = models.ForeignKey(City, on_delete=models.CASCADE, related_name="vendor_shipping_fees")
    fee = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    is_active = models.BooleanField(default=True)
    class Meta:
        constraints = [models.UniqueConstraint(fields=["vendor", "city"], name="uniq_vendor_city_shipping")]

class MarketplaceOffice(TimeStampedModel):
    city = models.OneToOneField(City, on_delete=models.CASCADE, related_name="marketplace_office")
    name = models.CharField(max_length=180)
    address = models.CharField(max_length=255, blank=True)
    phone = models.CharField(max_length=40, blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    image = models.ImageField(upload_to="offices/", null=True, blank=True)
    is_active = models.BooleanField(default=True)

class OrderItemDecision(TimeStampedModel):
    class Status(models.TextChoices):
        PENDING="pending","معلق"; ACCEPTED="accepted","مقبول"; REJECTED="rejected","مرفوض"
    order_item = models.OneToOneField("marketplace.OrderItem", on_delete=models.CASCADE, related_name="decision")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    reason = models.TextField(blank=True)
    decided_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
