from decimal import Decimal
from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):
    dependencies=[("marketplace","0005_office_fee")]
    operations=[migrations.CreateModel(name="PlatformLedgerEntry",fields=[("id",models.BigAutoField(auto_created=True,primary_key=True,serialize=False,verbose_name="ID")),("created_at",models.DateTimeField(auto_now_add=True)),("entry_type",models.CharField(max_length=40)),("amount",models.DecimalField(decimal_places=2,max_digits=14)),("currency",models.CharField(default="YER",max_length=6)),("reference",models.CharField(max_length=160,unique=True)),("metadata",models.JSONField(blank=True,default=dict)),("order",models.ForeignKey(blank=True,null=True,on_delete=django.db.models.deletion.PROTECT,related_name="platform_ledger_entries",to="marketplace.order"))])]
