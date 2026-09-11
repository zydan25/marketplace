from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("services", "0012_service_settings")]

    operations = [
        migrations.AddField(
            model_name="telecomplantype",
            name="parent",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="children",
                to="services.telecomplantype",
            ),
        ),
        migrations.AddIndex(
            model_name="telecomplantype",
            index=models.Index(
                fields=["service", "parent", "is_active"],
                name="svc_plan_type_tree_idx",
            ),
        ),
    ]
