from django.core.validators import MinValueValidator
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("services", "0002_service_transaction_webhook_fields")]

    operations = [
        migrations.AddField(
            model_name="service",
            name="service_kind",
            field=models.CharField(
                choices=[
                    ("query", "استعلام بدون خصم"),
                    ("catalog", "كتالوج/عرض بدون خصم"),
                    ("purchase", "عملية مدفوعة"),
                ],
                default="purchase",
                max_length=12,
            ),
        ),
        migrations.AddField(
            model_name="service",
            name="requires_balance",
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name="providerlink",
            name="request_encoding",
            field=models.CharField(
                choices=[
                    ("query", "Query parameters"),
                    ("form", "Form body"),
                    ("json", "JSON body"),
                ],
                default="query",
                max_length=10,
            ),
        ),
        migrations.AddField(
            model_name="servicetransaction",
            name="provider_transid",
            field=models.PositiveBigIntegerField(blank=True, null=True, unique=True),
        ),
        migrations.CreateModel(
            name="ServiceRequestReference",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("transid", models.PositiveBigIntegerField(unique=True)),
                ("request_kind", models.CharField(default="service", max_length=40)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("provider", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="request_references", to="services.providerconnection")),
                ("transaction", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="provider_references", to="services.servicetransaction")),
            ],
            options={"ordering": ["-created_at", "-id"]},
        ),
        migrations.AddIndex(
            model_name="servicerequestreference",
            index=models.Index(fields=["provider", "created_at"], name="svc_ref_provider_created_idx"),
        ),
        migrations.CreateModel(
            name="ServiceOption",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=180)),
                ("external_code", models.CharField(blank=True, max_length=120)),
                ("provider_num", models.CharField(blank=True, max_length=120)),
                ("price", models.DecimalField(decimal_places=2, default=0, max_digits=18, validators=[MinValueValidator(0)])),
                ("currency", models.CharField(default="YER", max_length=6)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("sort_order", models.PositiveIntegerField(default=0)),
                ("is_active", models.BooleanField(default=True)),
                ("service", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="options", to="services.service")),
            ],
            options={"ordering": ["sort_order", "id"]},
        ),
        migrations.AddConstraint(
            model_name="serviceoption",
            constraint=models.UniqueConstraint(fields=["service", "external_code", "provider_num", "name"], name="uniq_service_option_identity"),
        ),
        migrations.AddIndex(
            model_name="serviceoption",
            index=models.Index(fields=["service", "is_active"], name="svc_option_active_idx"),
        ),
    ]
