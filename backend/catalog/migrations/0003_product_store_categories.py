from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0002_delete_catalogoption_delete_category_city_and_more"),
        ("vendors", "0003_vendorcategory_vendorbranch"),
    ]

    operations = [
        migrations.AddField(
            model_name="product",
            name="store_categories",
            field=models.ManyToManyField(blank=True, db_table="marketplace_product_store_categories", related_name="products", to="vendors.vendorcategory"),
        ),
    ]
