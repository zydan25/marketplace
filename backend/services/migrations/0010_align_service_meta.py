from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [("services", "0009_align_current_models")]

    operations = [
        migrations.AlterModelOptions(
            name="providerconnection",
            options={"ordering": ["name", "id"]},
        ),
        migrations.AlterModelOptions(
            name="service",
            options={
                "ordering": ["sort_order", "id"],
                "verbose_name": "الخدمة",
                "verbose_name_plural": "الخدمات",
            },
        ),
        migrations.AlterModelOptions(
            name="servicecategory",
            options={"ordering": ["sort_order", "id"]},
        ),
    ]
