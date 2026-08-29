from marketplace.models import Category as MarketplaceCategory
from marketplace.models import Product as MarketplaceProduct
from marketplace.models import ProductImage as MarketplaceProductImage
from marketplace.models_extended import PriceGroup as MarketplacePriceGroup
from marketplace.models_extended import ProductVariant as MarketplaceProductVariant
from marketplace.models_extra import CatalogOption as MarketplaceCatalogOption


class Category(MarketplaceCategory):
    class Meta:
        proxy = True
        verbose_name = "فئة"
        verbose_name_plural = "الفئات"


class Product(MarketplaceProduct):
    class Meta:
        proxy = True
        verbose_name = "منتج"
        verbose_name_plural = "المنتجات"


class ProductImage(MarketplaceProductImage):
    class Meta:
        proxy = True
        verbose_name = "صورة منتج"
        verbose_name_plural = "صور المنتجات"


class ProductVariant(MarketplaceProductVariant):
    class Meta:
        proxy = True
        verbose_name = "صنف منتج"
        verbose_name_plural = "أصناف المنتجات"


class CatalogOption(MarketplaceCatalogOption):
    class Meta:
        proxy = True
        verbose_name = "خيار كتالوج"
        verbose_name_plural = "خيارات الكتالوج"


class PriceGroup(MarketplacePriceGroup):
    class Meta:
        proxy = True
        verbose_name = "مجموعة أسعار"
        verbose_name_plural = "مجموعات الأسعار"