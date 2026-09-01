from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("marketplace", "0010_storefront_media"),
        ("marketplace", "0010_finance_and_reservation_links"),
    ]

    operations = [
        migrations.AddField(
            model_name="storefrontmedia",
            name="sort_order",
            field=models.PositiveIntegerField(db_index=True, default=0),
        ),
    ]
