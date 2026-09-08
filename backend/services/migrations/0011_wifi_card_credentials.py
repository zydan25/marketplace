from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("services", "0010_align_service_meta")]

    operations = [
        migrations.AlterField(
            model_name="wificard",
            name="pin",
            field=models.CharField(blank=True, default="", max_length=120),
        ),
        migrations.AlterField(
            model_name="wifidenomination",
            name="denomination_number",
            field=models.CharField(blank=True, max_length=80),
        ),
    ]
