from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("services", "0003_service_contract_fields")]

    operations = [
        migrations.AlterField(
            model_name="servicetransaction",
            name="status",
            field=models.CharField(
                choices=[
                    ("accepted", "مقبول ومُحجز"),
                    ("queued", "بانتظار التنفيذ"),
                    ("processing", "قيد التنفيذ"),
                    ("pending_provider", "قيد المعالجة لدى المزود"),
                    ("manual_review", "يحتاج مراجعة تشغيلية"),
                    ("success", "ناجح"),
                    ("failed", "فاشل"),
                    ("refunded", "مُعاد الرصيد"),
                ],
                default="accepted",
                max_length=24,
            ),
        ),
    ]
