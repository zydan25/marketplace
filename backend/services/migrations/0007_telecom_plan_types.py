from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("services", "0006_wifi_kiosk")]
    operations = [
        migrations.CreateModel(
            name="TelecomPlanType",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("code", models.CharField(max_length=80)),
                ("name", models.CharField(max_length=160)),
                ("description", models.TextField(blank=True)),
                ("sort_order", models.PositiveIntegerField(default=0)),
                ("is_active", models.BooleanField(default=True)),
                ("service", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="plan_types", to="services.service")),
                ("plans", models.ManyToManyField(blank=True, related_name="plan_types", to="services.telecomplan")),
            ],
            options={
                "ordering": ["sort_order", "id"],
                "indexes": [models.Index(fields=["service", "is_active"], name="svc_plan_type_active_idx")],
                "constraints": [models.UniqueConstraint(fields=["service", "code"], name="uniq_service_plan_type_code")],
            },
        ),
    ]
