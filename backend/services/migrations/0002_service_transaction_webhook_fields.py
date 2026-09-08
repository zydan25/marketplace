from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("services", "0001_initial")]

    operations = [
        migrations.AddField(
            model_name="servicetransaction",
            name="webhook_secret_encrypted",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="servicetransaction",
            name="webhook_received_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
