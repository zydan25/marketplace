from decimal import Decimal
import uuid

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils.text import slugify


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class PriceGroup(TimeStampedModel):
    name = models.CharField(max_length=120)
    code = models.CharField(max_length=50, unique=True)
    adjustment_type = models.CharField(max_length=20, choices=[("percentage", "نسبة مئوية"), ("fixed", "مبلغ ثابت")])
    percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    fixed_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "marketplace_pricegroup"


class City(TimeStampedModel):
    name = models.CharField(max_length=120)
    price_group = models.ForeignKey(PriceGroup, on_delete=models.SET_NULL, null=True, blank=True)
    shipping_fee = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "marketplace_city"
        ordering = ["name"]
        indexes = [models.Index(fields=["is_active", "name"])]


class Category(TimeStampedModel):
    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=140, unique=True)
    image = models.ImageField(upload_to="categories/", blank=True, null=True)
    parent = models.ForeignKey("self", on_delete=models.CASCADE, related_name="children", null=True, blank=True)
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "marketplace_category"
        ordering = ["sort_order", "name"]

    def __str__(self):
        return self.name


class Product(TimeStampedModel):
    vendor = models.ForeignKey("vendors.VendorProfile", on_delete=models.CASCADE, related_name="products")
    categories = models.ManyToManyField(Category, related_name="products", blank=True, db_table="marketplace_product_categories")
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
        db_table = "marketplace_product"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["vendor", "is_published"]),
            models.Index(fields=["sku"]),
            models.Index(fields=["vendor", "stock"]),
        ]

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
            while type(self).objects.filter(slug=slug).exclude(pk=self.pk).exists():
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
            while type(self).objects.filter(sku=candidate).exclude(pk=self.pk).exists():
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
        db_table = "marketplace_productimage"
        ordering = ["sort_order", "id"]


class ProductVariant(TimeStampedModel):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="variants")
    sku = models.CharField(max_length=80, unique=True, blank=True)
    color = models.CharField(max_length=80, blank=True)
    size = models.CharField(max_length=80, blank=True)
    price_override = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    stock = models.PositiveIntegerField(default=0)
    reserved_stock = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "marketplace_productvariant"
        indexes = [
            models.Index(fields=["product", "stock"]),
            models.Index(fields=["product", "color", "size"]),
            models.Index(fields=["product", "is_active"]),
        ]

    @property
    def available_stock(self):
        if not self.is_active:
            return 0
        return max(0, self.stock - self.reserved_stock)

    def save(self, *args, **kwargs):
        if not self.sku:
            product_sku = getattr(self.product, "sku", "") or "PRODUCT"
            color = slugify(self.color, allow_unicode=False).replace("-", "")[:20].upper()
            size = slugify(self.size, allow_unicode=False).replace("-", "")[:20].upper()
            dimensions = "-".join(part for part in (color, size) if part)
            base = f"{product_sku}-{dimensions}" if dimensions else f"{product_sku}-VAR"
            base = base[:70]
            candidate = base
            counter = 2
            while type(self).objects.filter(sku=candidate).exclude(pk=self.pk).exists():
                suffix = f"-{counter}"
                candidate = f"{base[:80-len(suffix)]}{suffix}"
                counter += 1
            self.sku = candidate or f"VAR-{uuid.uuid4().hex[:12].upper()}"
        super().save(*args, **kwargs)


class CatalogOption(TimeStampedModel):
    group = models.CharField(max_length=60)
    name = models.CharField(max_length=160)
    slug = models.SlugField(max_length=180)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, null=True, blank=True, related_name="catalog_options")
    sort_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "marketplace_catalogoption"
        ordering = ["group", "sort_order", "name", "id"]
        constraints = [models.UniqueConstraint(fields=["group", "slug", "category"], name="uniq_catalog_option_group_slug_category")]
        indexes = [
            models.Index(fields=["group", "is_active"], name="catopt_grp_active_idx"),
            models.Index(fields=["category", "group", "is_active"], name="catopt_cat_grp_active_idx"),
        ]
