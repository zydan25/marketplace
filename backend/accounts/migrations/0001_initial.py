from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("marketplace", "0016_rename_marketplace_indexes"),
    ]

    operations = [
        migrations.CreateModel(
            name="User",
            fields=[],
            options={
                "verbose_name": "المستخدم",
                "verbose_name_plural": "المستخدمون",
                "proxy": True,
                "indexes": [],
                "constraints": [],
            },
            bases=("marketplace.user",),
        ),
        migrations.CreateModel(
            name="UserPreference",
            fields=[],
            options={
                "verbose_name": "تفضيل المستخدم",
                "verbose_name_plural": "تفضيلات المستخدمين",
                "proxy": True,
                "indexes": [],
                "constraints": [],
            },
            bases=("marketplace.userpreference",),
        ),
    ]
