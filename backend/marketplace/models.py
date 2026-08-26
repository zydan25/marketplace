import uuid
from decimal import Decimal
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.utils.text import slugify
from .models_extended import PriceGroup, City, ProductVariant, OrderStatusHistory, AuditLog
from .models_extra import Address, Loan, GiftTransfer


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        abstract = True


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


class VendorProfile(TimeStampedModel):
    owner = models.OneToOneField(User, on_delete=models.CASCADE, related_name="vendor_profile")
    store_name = models.CharField(max_length=180)
    slug = models.SlugField(max_length=200, unique=True, blank=True)
    description = models.TextField(blank=True)
    logo = models.ImageField(upload_to="vendor/logos/", blank=True, null=True)
    cover = models.ImageField(upload_to="vendor/covers/", blank=True, null=True)
    phone = models.CharField(max_length=32, blank=True)
    address = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=20, choices=[("pending", "قيد المراجعة"), ("active", "نشط"), ("suspended", "موقوف")], default="pending")
    commission_percent = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("10.00"), validators=[MinValueValidator(0), MaxValueValidator(100)])
    settings = models.JSONField(default=dict, blank=True)
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.store_name, allow_unicode=True)
        super().save(*args, **kwargs)
    def __str__(self):
        return self.store_name


class DesignTheme(TimeStampedModel):
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name="design_themes", null=True, blank=True)
    vendor = models.OneToOneField(VendorProfile, on_delete=models.CASCADE, related_name="theme", null=True, blank=True)
    name = models.CharField(max_length=120)
    is_global = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    tokens = models.JSONField(default=dict, blank=True)
    layout = models.JSONField(default=dict, blank=True)
    sections = models.JSONField(default=list, blank=True)
    class Meta:
        ordering = ["-is_global", "-updated_at"]
    def __str__(self):
        return self.name


class Category(TimeStampedModel):
    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=140, unique=True)
    image = models.ImageField(upload_to="categories/", blank=True, null=True)
    parent = models.ForeignKey("self", on_delete=models.CASCADE, related_name="children", null=True, blank=True)
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)
    class Meta:
        ordering = ["sort_order", "name"]
    def __str__(self):
        return self.name


class Product(TimeStampedModel):
    vendor = models.ForeignKey(VendorProfile, on_delete=models.CASCADE, related_name="products")
    categories = models.ManyToManyField(Category, related_name="products", blank=True)
    sku = models.CharField(max_length=80, unique=True, blank=True)
    name = models.CharField(max_length=220)
    slug = models.SlugField(max_length=240, unique=True, blank=True)
    description = models.TextField(blank=True)
    brand = models.CharField(max_length=120, blank=True)
    material = models.CharField(max_length=180, blank=True)
    shipping_note = models.CharField(max_length=255, blank=True)
    return_policy = models.CharField(max_length=255, blank=True)
    price = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    sale_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(0)])
    currency = models.CharField(max_length=6, default="YER")
    stock = models.PositiveIntegerField(default=0)
    reserved_stock = models.PositiveIntegerField(default=0)
    colors = models.JSONField(default=list, blank=True)
    sizes = models.JSONField(default=list, blank=True)
    hashtags = models.JSONField(default=list, blank=True)
    details = models.JSONField(default=dict, blank=True)
    main_image = models.ImageField(upload_to="products/", blank=True, null=True)
    images = models.JSONField(default=list, blank=True)
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=Decimal("0.00"), validators=[MinValueValidator(0), MaxValueValidator(5)])
    reviews_count = models.PositiveIntegerField(default=0)
    is_published = models.BooleanField(default=False)
    is_trending = models.BooleanField(default=False)
    sold_count = models.PositiveIntegerField(default=0)
    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["vendor", "is_published"]), models.Index(fields=["sku"]), models.Index(fields=["vendor", "stock"])]
    @property
    def available_stock(self):
        return max(0, self.stock - self.reserved_stock)
    @property
    def effective_price(self):
        return self.sale_price if self.sale_price is not None else self.price
    @property
    def discount_percent(self):
        if not self.sale_price or self.price <= 0 or self.sale_price >= self.price:
            return 0
        return round((1 - self.sale_price / self.price) * 100)
    def save(self, *args, **kwargs):
        if not self.slug and self.name:
            base_slug = slugify(self.name, allow_unicode=True)
            if not base_slug:
                base_slug = f"product-{uuid.uuid4().hex[:8]}"
            slug = base_slug[:240]
            counter = 2
            while Product.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                suffix = f"-{counter}"
                slug = f"{base_slug[:240 - len(suffix)]}{suffix}"
                counter += 1
            self.slug = slug
        if not self.sku:
            base_sku = slugify(self.name, allow_unicode=False).replace("-", "")[:55].upper()
            if not base_sku:
                base_sku = "PRODUCT"
            base_sku = f"SKU-{base_sku}"
            candidate = base_sku[:80]
            counter = 2
            while Product.objects.filter(sku=candidate).exclude(pk=self.pk).exists():
                suffix = f"-{counter}"
                candidate = f"{base_sku[:80 - len(suffix)]}{suffix}"
                counter += 1
            self.sku = candidate
        super().save(*args, **kwargs)
    def __str__(self):
        return f"{self.name} ({self.sku})"


class ProductImage(TimeStampedModel):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="image_items")
    image = models.ImageField(upload_to="products/gallery/")
    alt_text = models.CharField(max_length=180, blank=True)
    sort_order = models.PositiveIntegerField(default=0)
    is_primary = models.BooleanField(default=False)
    class Meta:
        ordering = ["sort_order", "id"]


class StorefrontSection(TimeStampedModel):
    class SectionTypes(models.TextChoices):
        HERO = "hero", "عرض رئيسي"
        CATEGORY = "category", "فئات"
        PRODUCT_GRID = "product_grid", "شبكة منتجات"
        TREND = "trend", "ترند"
        BANNER = "banner", "بانر"
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name="storefront_sections")
    vendor = models.ForeignKey(VendorProfile, on_delete=models.CASCADE, related_name="storefront_sections", null=True, blank=True)
    title = models.CharField(max_length=180, blank=True)
    section_type = models.CharField(max_length=30, choices=SectionTypes.choices)
    config = models.JSONField(default=dict, blank=True)
    sort_order = models.PositiveIntegerField(default=0)
    is_visible = models.BooleanField(default=True)
    class Meta:
        ordering = ["sort_order", "id"]


class Wallet(TimeStampedModel):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="wallet")
    balance = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"), validators=[MinValueValidator(0)])
    currency = models.CharField(max_length=6, default="YER")
    is_locked = models.BooleanField(default=False)


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


class Coupon(TimeStampedModel):
    code = models.CharField(max_length=50, unique=True)
    discount_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0, validators=[MinValueValidator(0), MaxValueValidator(100)])
    discount_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    minimum_order = models.DecimalField(max_digits=12, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    usage_limit = models.PositiveIntegerField(null=True, blank=True)
    used_count = models.PositiveIntegerField(default=0)
    starts_at = models.DateTimeField(null=True, blank=True)
    ends_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    assigned_to = models.ManyToManyField(User, blank=True, related_name="coupons")


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
    customer = models.ForeignKey(User, on_delete=models.PROTECT, related_name="orders")
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
        ordering = ["-created_at"]


class OrderItem(TimeStampedModel):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    vendor = models.ForeignKey(VendorProfile, on_delete=models.PROTECT, related_name="order_items")
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name="order_items")
    name_snapshot = models.CharField(max_length=220)
    sku_snapshot = models.CharField(max_length=80)
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=14, decimal_places=2)
    color = models.CharField(max_length=80, blank=True)
    size = models.CharField(max_length=80, blank=True)
    vendor_total = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    commission = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    vendor_net = models.DecimalField(max_digits=14, decimal_places=2, default=0)


class VendorPayout(TimeStampedModel):
    vendor = models.ForeignKey(VendorProfile, on_delete=models.PROTECT, related_name="payouts")
    vendor_order = models.ForeignKey("marketplace.VendorOrder", on_delete=models.PROTECT, related_name="payouts", null=True, blank=True)
    order = models.ForeignKey(Order, on_delete=models.PROTECT, related_name="payouts", null=True, blank=True)
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    currency = models.CharField(max_length=6, default="YER")
    status = models.CharField(max_length=20, choices=[("pending", "معلق"), ("approved", "معتمد"), ("paid", "مدفوع"), ("rejected", "مرفوض")], default="pending")
    reference = models.CharField(max_length=120, blank=True)
    note = models.TextField(blank=True)


class Notification(TimeStampedModel):
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name="notifications", null=True, blank=True)
    title = models.CharField(max_length=180)
    body = models.TextField()
    image = models.ImageField(upload_to="notifications/", blank=True, null=True)
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, blank=True, related_name="notifications")
    is_read = models.BooleanField(default=False)
    audience = models.JSONField(default=dict, blank=True)


class Conversation(TimeStampedModel):
    customer = models.ForeignKey(User, on_delete=models.CASCADE, related_name="customer_conversations")
    vendor = models.ForeignKey(VendorProfile, on_delete=models.CASCADE, related_name="conversations", null=True, blank=True)
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name="conversation", null=True, blank=True)
    subject = models.CharField(max_length=180, blank=True)
    is_closed = models.BooleanField(default=False)


class Message(TimeStampedModel):
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey(User, on_delete=models.PROTECT, related_name="sent_messages")
    body = models.TextField(blank=True)
    attachment = models.ImageField(upload_to="messages/", blank=True, null=True)
    is_read = models.BooleanField(default=False)


class Referral(TimeStampedModel):
    inviter = models.ForeignKey(User, on_delete=models.CASCADE, related_name="referrals_sent")
    invitee = models.OneToOneField(User, on_delete=models.CASCADE, related_name="referral_source")
    code = models.CharField(max_length=32, unique=True)
    reward_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    reward_paid = models.BooleanField(default=False)

from .marketplace_models import (  # noqa: E402,F401
    CouponRedemption,
    InventoryReservation,
    Payment,
    Shipment,
    VendorLedgerEntry,
    VendorOrder,
    VendorOrderItem,
    PlatformLedgerEntry,
)
from .engagement_models import Favorite, ProductComment, PasswordResetRequest
