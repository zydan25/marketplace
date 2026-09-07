from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("services", "0008_wifi_management_percent_validators")]

    operations = [
        migrations.CreateModel(
            name="ServiceRequestLog",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("direction", models.CharField(default="provider", max_length=20)),
                ("http_status", models.PositiveIntegerField(blank=True, null=True)),
                ("result_code", models.CharField(blank=True, max_length=80)),
                ("description", models.TextField(blank=True)),
                ("request_payload", models.JSONField(blank=True, default=dict)),
                ("response_payload", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("transaction", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="logs", to="services.servicetransaction")),
            ],
        ),
        migrations.RemoveIndex(model_name="providerlink", name="svc_link_provider_priority_idx"),
        migrations.RemoveIndex(model_name="servicetask", name="svc_task_queue_idx"),
        migrations.RemoveIndex(model_name="servicetransaction", name="svc_tx_customer_status_idx"),
        migrations.RemoveIndex(model_name="servicetransaction", name="svc_tx_status_created_idx"),
        migrations.AlterField(
            model_name="servicetask",
            name="kind",
            field=models.CharField(choices=[("submit", "إرسال العملية"), ("status_check", "فحص حالة العملية")], default="submit", max_length=20),
        ),
        migrations.AlterField(
            model_name="wifidenomination",
            name="face_value",
            field=models.DecimalField(max_digits=18, decimal_places=2, validators=[MinValueValidator(Decimal("0"))]),
        ),
        migrations.AlterField(
            model_name="wifidenomination",
            name="sale_price",
            field=models.DecimalField(max_digits=18, decimal_places=2, validators=[MinValueValidator(Decimal("0"))]),
        ),
    ]
