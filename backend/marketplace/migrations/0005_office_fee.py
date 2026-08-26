from decimal import Decimal
from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies=[("marketplace","0004_engagement")]
    operations=[migrations.AddField(model_name="marketplaceoffice",name="office_fee",field=models.DecimalField(decimal_places=2,default=Decimal("0.00"),max_digits=12))]
