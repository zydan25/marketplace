from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [("marketplace", "0011_catalog_currency_shipping")]

    operations = [
        migrations.AlterModelOptions(
            name="storefrontmedia",
            options={"ordering": ["sort_order", "-updated_at", "id"]},
        ),
    ]
