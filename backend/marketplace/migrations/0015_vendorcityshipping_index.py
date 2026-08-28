from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("marketplace", "0014_merge_catalog_and_storefront"),
    ]

    operations = [
        migrations.AddIndex(
            model_name="vendorcityshipping",
            index=models.Index(
                fields=["vendor", "city", "is_active"],
                name="marketplace_v_vendor_c_f2b09e_idx",
            ),
        ),
    ]
