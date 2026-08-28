from decimal import Decimal

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


DEFAULT_CATEGORIES = {
    "الإلكترونيات": ["هواتف", "أجهزة لوحية", "كمبيوترات", "تلفزيونات وشاشات", "أجهزة كهربائية منزلية", "إكسسوارات إلكترونية"],
    "الملابس": ["رجالي", "نسائي", "ولادي", "بناتي", "أطفال", "أحذية", "حقائب"],
    "المأكولات": ["أغذية", "مشروبات", "حلويات", "مخبوزات"],
    "المنزل": ["أثاث", "مطبخ", "ديكور", "مستلزمات منزلية"],
    "الجمال والعناية": ["عناية بالبشرة", "عناية بالشعر", "عطور", "مكياج"],
    "الألعاب": ["ألعاب أطفال", "ألعاب إلكترونية", "ألعاب جماعية"],
    "الرياضة": ["ملابس رياضية", "معدات رياضية", "إكسسوارات رياضية"],
    "السيارات": ["قطع غيار", "إكسسوارات سيارات", "زيوت وعناية"],
    "الكتب والتعليم": ["كتب", "قرطاسية", "مستلزمات مدرسية"],
}

DEFAULT_OPTIONS = {
    "condition": ["جديد", "مستخدم"],
    "warranty": ["نعم", "لا"],
    "gender": ["رجالي", "نسائي", "ولادي", "بناتي", "أطفال", "الجميع"],
    "material": ["قطن", "بوليستر", "جلد", "خشب", "معدن", "زجاج", "بلاستيك"],
    "brand": ["Samsung", "Apple", "Xiaomi", "Huawei", "Lenovo", "HP", "Dell", "LG", "Sony", "Nike", "Adidas", "غير ذلك"],
}


def seed_defaults(apps, schema_editor):
    Category = apps.get_model("marketplace", "Category")
    CatalogOption = apps.get_model("marketplace", "CatalogOption")
    for sort, (root_name, children) in enumerate(DEFAULT_CATEGORIES.items()):
        root_slug = root_name.replace(" ", "-")
        root, _ = Category.objects.get_or_create(slug=root_slug, defaults={"name": root_name, "sort_order": sort, "is_active": True})
        for child_sort, child_name in enumerate(children):
            slug = f"{root_slug}-{child_name.replace(' ', '-')}"
            Category.objects.get_or_create(slug=slug, defaults={"name": child_name, "parent_id": root.id, "sort_order": child_sort, "is_active": True})
    for group, names in DEFAULT_OPTIONS.items():
        for sort, name in enumerate(names):
            CatalogOption.objects.get_or_create(group=group, slug=name.lower().replace(" ", "-"), category=None, defaults={"name": name, "sort_order": sort, "is_active": True})


def unseed_defaults(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("marketplace", "0010_finance_and_reservation_links"),
        ("marketplace", "0009_vendor_application"),
    ]

    operations = [
        migrations.CreateModel(
            name="CatalogOption",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("group", models.CharField(max_length=60)),
                ("name", models.CharField(max_length=160)),
                ("slug", models.SlugField(max_length=180)),
                ("sort_order", models.PositiveIntegerField(default=0)),
                ("is_active", models.BooleanField(default=True)),
                ("category", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="catalog_options", to="marketplace.category")),
            ],
            options={"ordering": ["group", "sort_order", "name", "id"]},
        ),
        migrations.CreateModel(
            name="CurrencyRate",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("base_currency", models.CharField(default="YER", max_length=6)),
                ("target_currency", models.CharField(max_length=6)),
                ("rate", models.DecimalField(decimal_places=8, default=Decimal("1.00000000"), max_digits=18)),
                ("is_active", models.BooleanField(default=True)),
                ("updated_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="currency_rates_updated", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["base_currency", "target_currency"]},
        ),
        migrations.CreateModel(
            name="UserPreference",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("currency", models.CharField(default="YER", max_length=6)),
                ("notifications_enabled", models.BooleanField(default=True)),
                ("user", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="preference", to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name="VendorCityShipping",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("fee", models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=12)),
                ("is_active", models.BooleanField(default=True)),
                ("city", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="vendor_shipping_fees", to="marketplace.city")),
                ("vendor", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="city_shipping_fees", to="marketplace.vendorprofile")),
            ],
        ),
        migrations.AddConstraint(model_name="catalogoption", constraint=models.UniqueConstraint(fields=("group", "slug", "category"), name="uniq_catalog_option_group_slug_category")),
        migrations.AddIndex(model_name="catalogoption", index=models.Index(fields=["group", "is_active"], name="marketplace_c_group_i_0e79c0_idx")),
        migrations.AddIndex(model_name="catalogoption", index=models.Index(fields=["category", "group", "is_active"], name="marketplace_c_categor_0be1ef_idx")),
        migrations.AddConstraint(model_name="currencyrate", constraint=models.UniqueConstraint(fields=("base_currency", "target_currency"), name="uniq_currency_rate_pair")),
        migrations.AddConstraint(model_name="vendorcityshipping", constraint=models.UniqueConstraint(fields=("vendor", "city"), name="uniq_vendor_city_shipping")),
        migrations.AddIndex(model_name="vendorcityshipping", index=models.Index(fields=["vendor", "city", "is_active"], name="marketplace_v_vendor_c_f2b09e_idx")),
        migrations.RunPython(seed_defaults, unseed_defaults),
    ]
