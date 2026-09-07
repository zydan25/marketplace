from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import decimal


class Migration(migrations.Migration):
    dependencies = [("services", "0005_expand_service_field_types")]
    operations = [
        migrations.CreateModel(name="WifiNetwork", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("name", models.CharField(max_length=180)),
            ("location", models.CharField(max_length=300)),
            ("management_percent", models.DecimalField(decimal_places=2, default=0, max_digits=6)),
            ("latitude", models.DecimalField(blank=True, decimal_places=7, max_digits=10, null=True)),
            ("longitude", models.DecimalField(blank=True, decimal_places=7, max_digits=10, null=True)),
            ("description", models.TextField(blank=True)),
            ("is_active", models.BooleanField(default=True)),
            ("created_at", models.DateTimeField(auto_now_add=True)),
            ("updated_at", models.DateTimeField(auto_now=True)),
            ("owner", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="owned_wifi_networks", to=settings.AUTH_USER_MODEL)),
        ], options={"ordering":["name","id"],"indexes":[models.Index(fields=["is_active","name"],name="wifi_network_active_idx")]},),
        migrations.CreateModel(name="WifiDenomination", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("name", models.CharField(max_length=160)),
            ("denomination_number", models.CharField(max_length=80)),
            ("face_value", models.DecimalField(decimal_places=2, max_digits=18)),
            ("sale_price", models.DecimalField(decimal_places=2, max_digits=18)),
            ("is_active", models.BooleanField(default=True)),
            ("created_at", models.DateTimeField(auto_now_add=True)),
            ("updated_at", models.DateTimeField(auto_now=True)),
            ("network", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="denominations", to="services.wifinetwork")),
        ], options={"ordering":["face_value","id"],"constraints":[models.UniqueConstraint(fields=["network","denomination_number"],name="uniq_wifi_network_denom_number")],"indexes":[models.Index(fields=["network","is_active"],name="wifi_denom_network_active_idx")]},),
        migrations.CreateModel(name="WifiCard", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("card_number", models.CharField(max_length=120, unique=True)),
            ("pin", models.CharField(max_length=120)),
            ("status", models.CharField(choices=[("available","متاح"),("sold","مبيع"),("blocked","موقوف")],default="available",max_length=20)),
            ("sold_at", models.DateTimeField(blank=True,null=True)),
            ("sale_journal_id", models.PositiveIntegerField(blank=True,null=True)),
            ("created_at", models.DateTimeField(auto_now_add=True)),
            ("updated_at", models.DateTimeField(auto_now=True)),
            ("denomination", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,related_name="cards",to="services.wifidenomination")),
            ("sold_to", models.ForeignKey(blank=True,null=True,on_delete=django.db.models.deletion.PROTECT,related_name="purchased_wifi_cards",to=settings.AUTH_USER_MODEL)),
        ], options={"ordering":["status","id"],"indexes":[models.Index(fields=["denomination","status"],name="wifi_card_denom_status_idx"),models.Index(fields=["sold_to","sold_at"],name="wifi_card_buyer_idx")]},),
    ]
