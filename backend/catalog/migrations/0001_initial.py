from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("marketplace", "0016_rename_marketplace_indexes"),
    ]

    operations = [
        migrations.CreateModel(
            name="Category",
            fields=[],
            options={"verbose_name": "فئة", "verbose_name_plural": "الفئات", "proxy": True},
            bases=("marketplace.category",),
        ),
        migrations.CreateModel(
            name="Product",
            fields=[],
            options={"verbose_name": "منتج", "verbose_name_plural": "المنتجات", "proxy": True},
            bases=("marketplace.product",),
        ),
        migrations.CreateModel(
            name="ProductImage",
            fields=[],
            options={"verbose_name": "صورة منتج", "verbose_name_plural": "صور المنتجات", "proxy": True},
            bases=("marketplace.productimage",),
        ),
        migrations.CreateModel(
            name="ProductVariant",
            fields=[],
            options={"verbose_name": "صنف منتج", "verbose_name_plural": "أصناف المنتجات", "proxy": True},
            bases=("marketplace.productvariant",),
        ),
        migrations.CreateModel(
            name="CatalogOption",
            fields=[],
            options={"verbose_name": "خيار كتالوج", "verbose_name_plural": "خيارات الكتالوج", "proxy": True},
            bases=("marketplace.catalogoption",),
        ),
        migrations.CreateModel(
            name="PriceGroup",
            fields=[],
            options={"verbose_name": "مجموعة أسعار", "verbose_name_plural": "مجموعات الأسعار", "proxy": True},
            bases=("marketplace.pricegroup",),
        ),
    ]