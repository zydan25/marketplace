from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("marketplace", "0017_seed_global_storefront_themes"),
    ]

    operations = [
        migrations.AddField(
            model_name="storefrontmedia",
            name="sort_order",
            field=models.PositiveIntegerField(db_index=True, default=0),
        ),
    ]
