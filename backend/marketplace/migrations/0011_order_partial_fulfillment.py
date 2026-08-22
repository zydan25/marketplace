from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("marketplace", "0010_finance_and_reservation_links")]

    operations = [
        migrations.AlterField(
            model_name="order",
            name="status",
            field=models.CharField(
                choices=[
                    ("pending", "قيد الانتظار"),
                    ("confirmed", "مؤكد"),
                    ("processing", "قيد التجهيز"),
                    ("shipped", "تم الشحن"),
                    ("partially_fulfilled", "منفذ جزئيًا"),
                    ("delivered", "تم التسليم"),
                    ("cancelled", "ملغي"),
                    ("refunded", "مسترد"),
                ],
                default="pending",
                max_length=24,
            ),
        ),
    ]
