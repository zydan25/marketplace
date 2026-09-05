from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [("accounting", "0001_initial")]

    operations = [
        migrations.AlterModelOptions(
            name="withdrawalrequest",
            options={"ordering": ["-created_at"]},
        ),
    ]
