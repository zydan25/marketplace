from django.contrib import admin

from .models import Category, CatalogOption, PriceGroup, Product, ProductImage, ProductVariant


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "parent", "is_active", "sort_order", "created_at")
    list_filter = ("is_active",)
    search_fields = ("name", "slug")
    list_editable = ("is_active", "sort_order")
    prepopulated_fields = {"slug": ("name",)}
    autocomplete_fields = ("parent",)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        "name", "sku", "vendor", "effective_price", "stock", "reserved_stock", "available_stock_display",
        "is_published", "is_trending", "updated_at",
    )
    list_filter = ("is_published", "is_trending", "currency", "vendor")
    search_fields = ("name", "sku", "description", "brand", "vendor__store_name")
    filter_horizontal = ("categories",)
    prepopulated_fields = {"slug": ("name",)}
    readonly_fields = ("reserved_stock", "rating", "reviews_count", "sold_count", "created_at", "updated_at")
    list_select_related = ("vendor",)

    @admin.display(description="السعر الحالي", ordering="price")
    def effective_price(self, obj):
        return obj.effective_price

    @admin.display(description="المتاح", ordering="stock")
    def available_stock_display(self, obj):
        return obj.available_stock


@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    list_display = ("product", "sort_order", "is_primary", "alt_text", "updated_at")
    list_filter = ("is_primary",)
    search_fields = ("product__name", "product__sku", "alt_text")
    list_editable = ("sort_order", "is_primary")


@admin.register(ProductVariant)
class ProductVariantAdmin(admin.ModelAdmin):
    list_display = ("product", "sku", "color", "size", "price_override", "stock", "reserved_stock", "available_stock_display", "is_active")
    list_filter = ("is_active", "color", "size")
    search_fields = ("product__name", "product__sku", "sku", "color", "size")
    list_editable = ("price_override", "stock", "is_active")
    autocomplete_fields = ("product",)
    readonly_fields = ("reserved_stock",)

    @admin.display(description="المتاح", ordering="stock")
    def available_stock_display(self, obj):
        return obj.available_stock


@admin.register(CatalogOption)
class CatalogOptionAdmin(admin.ModelAdmin):
    list_display = ("name", "group", "category", "sort_order", "is_active", "updated_at")
    list_filter = ("group", "is_active")
    search_fields = ("name", "slug", "group")
    list_editable = ("sort_order", "is_active")
    autocomplete_fields = ("category",)
    ordering = ("group", "sort_order", "name")


@admin.register(PriceGroup)
class PriceGroupAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "adjustment_type", "percentage", "fixed_amount", "is_active", "updated_at")
    list_filter = ("adjustment_type", "is_active")
    search_fields = ("name", "code")
    list_editable = ("percentage", "fixed_amount", "is_active")
