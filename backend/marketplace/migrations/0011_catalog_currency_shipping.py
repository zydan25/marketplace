from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
from decimal import Decimal


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
            options={
                "ordering": ["group", "sort_order", "name", "id"],
            },
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
        migrations.AddConstraint(
            model_name="catalogoption",
            constraint=models.UniqueConstraint(fields=("group", "slug", "category"), name="uniq_catalog_option_group_slug_category"),
        ),
        migrations.AddIndex(model_name="catalogoption", index=models.Index(fields=["group", "is_active"], name="marketplace_c_group_i_0e79c0_idx")),
        migrations.AddIndex(model_name="catalogoption", index=models.Index(fields=["category", "group", "is_active"], name="marketplace_c_categor_0be1ef_idx")),
        migrations.AddConstraint(
            model_name="currencyrate",
            constraint=models.UniqueConstraint(fields=("base_currency", "target_currency"), name="uniq_currency_rate_pair"),
        ),
        migrations.AddConstraint(
            model_name="vendorcityshipping",
            constraint=models.UniqueConstraint(fields=("vendor", "city"), name="uniq_vendor_city_shipping"),
        ),
        migrations.AddIndex(model_name="vendorcityshipping", index=models.Index(fields=["vendor", "city", "is_active"], name="marketplace_v_vendor_c_f2b09e_idx")),
    ]
