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
    ]
