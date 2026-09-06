from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("services", "0004_alter_servicetransaction_status")]

    operations = [
        migrations.AlterField(
            model_name="servicefield",
            name="field_type",
            field=models.CharField(
                choices=[
                    ("text", "نص"),
                    ("number", "رقم"),
                    ("decimal", "رقم عشري"),
                    ("date", "تاريخ"),
                    ("phone", "هاتف"),
                    ("select", "اختيار"),
                    ("boolean", "نعم/لا"),
                    ("email", "بريد إلكتروني"),
                    ("image", "صورة"),
                    ("audio", "صوت"),
                    ("json", "بيانات JSON"),
                ],
                default="text",
                max_length=12,
            ),
        ),
    ]
