from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("storefront", "0002_delete_designtheme_delete_storefrontmedia_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="storefrontsection",
            name="sort_order",
            field=models.BigIntegerField(default=0),
        ),
    ]
