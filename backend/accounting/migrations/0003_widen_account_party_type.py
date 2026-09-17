from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("accounting", "0002_alter_withdrawalrequest_options")]

    operations = [
        migrations.AlterField(
            model_name="account",
            name="party_type",
            field=models.CharField(blank=True, max_length=30),
        ),
    ]
