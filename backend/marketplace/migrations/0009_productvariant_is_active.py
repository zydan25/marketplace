from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("marketplace", "0008_inventory_reservations_indexes")]

    operations = [
        migrations.AddField(
            model_name="productvariant",
            name="is_active",
            field=models.BooleanField(default=True),
        ),
        migrations.AddIndex(
            model_name="productvariant",
            index=models.Index(fields=["product", "is_active"], name="marketplace_pv_product_a_2b9f5c_idx"),
        ),
    ]
