from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("marketplace", "0016_rename_marketplace_indexes")]
    operations = [
        migrations.CreateModel(
            name="VendorProfile",
            fields=[],
            options={"verbose_name": "التاجر", "verbose_name_plural": "التجار", "ordering": ["-created_at"], "proxy": True},
            bases=("marketplace.vendorprofile",),
        ),
        migrations.CreateModel(
            name="VendorApplication",
            fields=[],
            options={"verbose_name": "طلب تاجر", "verbose_name_plural": "طلبات التجار", "ordering": ["-created_at"], "proxy": True},
            bases=("marketplace.vendorapplication",),
        ),
    ]
