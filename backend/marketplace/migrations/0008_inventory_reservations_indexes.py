from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("marketplace", "0007_marketplace_scaling")]

    operations = [
        migrations.AddField(
            model_name="product",
            name="reserved_stock",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddIndex(
            model_name="product",
            index=models.Index(fields=["vendor", "stock"], name="marketplace_p_vendor_s_4d4e9e_idx"),
        ),
        migrations.AddIndex(
            model_name="city",
            index=models.Index(fields=["is_active", "name"], name="marketplace_c_active_n_1f1f2a_idx"),
        ),
        migrations.AddIndex(
            model_name="productvariant",
            index=models.Index(fields=["product", "stock"], name="marketplace_pv_product_s_8b8b3c_idx"),
        ),
        migrations.AddIndex(
            model_name="productvariant",
            index=models.Index(fields=["product", "color", "size"], name="marketplace_pv_dims_55be61_idx"),
        ),
    ]
