from decimal import Decimal

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("services", "0007_telecom_plan_types")]

    operations = [
        migrations.AlterField(
            model_name="wifinetwork",
            name="management_percent",
            field=models.DecimalField(
                decimal_places=2,
                default=0,
                max_digits=6,
                validators=[MinValueValidator(Decimal("0")), MaxValueValidator(Decimal("100"))],
            ),
        ),
    ]
