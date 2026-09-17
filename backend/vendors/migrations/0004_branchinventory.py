from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("vendors", "0003_vendorcategory_vendorbranch"),
        ("catalog", "0003_product_store_categories"),
    ]

    operations = [
        migrations.CreateModel(
            name="BranchInventory",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("stock", models.PositiveIntegerField(default=0)),
                ("reserved_stock", models.PositiveIntegerField(default=0)),
                ("branch", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="inventory", to="vendors.vendorbranch")),
                ("product", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="branch_inventory", to="catalog.product")),
                ("variant", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="branch_inventory", to="catalog.productvariant")),
            ],
            options={
                "db_table": "marketplace_branchinventory",
                "ordering": ["-updated_at", "id"],
                "indexes": [
                    models.Index(fields=["branch", "product", "variant"], name="branch_inventory_lookup_idx"),
                ],
            },
        ),
    ]
