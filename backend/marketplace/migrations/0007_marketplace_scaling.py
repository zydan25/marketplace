from django.db import migrations, models
import django.db.models.deletion
from django.core.validators import MinValueValidator
from decimal import Decimal


class Migration(migrations.Migration):
    dependencies = [("marketplace", "0006_user_points_balance")]

    operations = [
        migrations.CreateModel(
            name="VendorOrder",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("order_number", models.CharField(max_length=60, unique=True)),
                ("status", models.CharField(choices=[("pending", "قيد الانتظار"), ("confirmed", "مؤكد"), ("processing", "قيد التجهيز"), ("shipped", "تم الشحن"), ("delivered", "تم التسليم"), ("cancelled", "ملغي"), ("refunded", "مسترد")], default="pending", max_length=20)),
                ("subtotal", models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=14, validators=[MinValueValidator(0)])),
                ("shipping_fee", models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=14, validators=[MinValueValidator(0)])),
                ("discount", models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=14, validators=[MinValueValidator(0)])),
                ("total", models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=14, validators=[MinValueValidator(0)])),
                ("commission", models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=14, validators=[MinValueValidator(0)])),
                ("vendor_net", models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=14, validators=[MinValueValidator(0)])),
                ("currency", models.CharField(default="YER", max_length=6)),
                ("order", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="vendor_orders", to="marketplace.order")),
                ("vendor", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="vendor_orders", to="marketplace.vendorprofile")),
            ],
            options={"ordering": ["-created_at"], "indexes": [models.Index(fields=["vendor", "status"], name="marketplace_v_vendor_i_7f0d8a_idx"), models.Index(fields=["order", "status"], name="marketplace_v_order_s_0b3aef_idx")], "constraints": [models.UniqueConstraint(fields=("order", "vendor"), name="uniq_vendor_order_per_vendor")]},
        ),
        migrations.CreateModel(
            name="Payment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("provider", models.CharField(default="manual", max_length=60)),
                ("method", models.CharField(default="cash_on_delivery", max_length=60)),
                ("transaction_id", models.CharField(blank=True, max_length=160, null=True, unique=True)),
                ("amount", models.DecimalField(decimal_places=2, max_digits=14, validators=[MinValueValidator(0)])),
                ("refunded_amount", models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=14, validators=[MinValueValidator(0)])),
                ("currency", models.CharField(default="YER", max_length=6)),
                ("status", models.CharField(choices=[("pending", "قيد الانتظار"), ("authorized", "مصرح"), ("paid", "مدفوع"), ("failed", "فشل"), ("refunded", "مسترد"), ("partially_refunded", "مسترد جزئيًا"), ("cancelled", "ملغي")], default="pending", max_length=30)),
                ("paid_at", models.DateTimeField(blank=True, null=True)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("order", models.OneToOneField(on_delete=django.db.models.deletion.PROTECT, related_name="payment", to="marketplace.order")),
            ],
        ),
        migrations.CreateModel(
            name="Shipment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("carrier", models.CharField(blank=True, max_length=120)),
                ("tracking_number", models.CharField(blank=True, max_length=160)),
                ("status", models.CharField(choices=[("pending", "قيد الانتظار"), ("ready", "جاهز"), ("shipped", "تم الشحن"), ("in_transit", "في الطريق"), ("delivered", "تم التسليم"), ("returned", "مرتجع"), ("cancelled", "ملغي")], default="pending", max_length=30)),
                ("shipped_at", models.DateTimeField(blank=True, null=True)),
                ("delivered_at", models.DateTimeField(blank=True, null=True)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("vendor_order", models.OneToOneField(on_delete=django.db.models.deletion.PROTECT, related_name="shipment", to="marketplace.vendororder")),
            ],
        ),
        migrations.CreateModel(
            name="InventoryReservation",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("expires_at", models.DateTimeField()),
                ("quantity", models.PositiveIntegerField()),
                ("status", models.CharField(choices=[("active", "نشط"), ("committed", "مثبت"), ("released", "محرر"), ("expired", "منتهي")], default="active", max_length=20)),
                ("order", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="inventory_reservations", to="marketplace.order")),
                ("product", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="inventory_reservations", to="marketplace.product")),
                ("variant", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="inventory_reservations", to="marketplace.productvariant")),
            ],
            options={"indexes": [models.Index(fields=["order", "status"], name="marketplace_i_order_s_2c1774_idx"), models.Index(fields=["expires_at", "status"], name="marketplace_i_expires_4ea06b_idx")]},
        ),
        migrations.CreateModel(
            name="VendorLedgerEntry",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("entry_type", models.CharField(choices=[("sale", "بيع"), ("commission", "عمولة"), ("refund", "استرداد"), ("payout", "سحب"), ("adjustment", "تسوية")], max_length=30)),
                ("amount", models.DecimalField(decimal_places=2, max_digits=14)),
                ("balance_after", models.DecimalField(decimal_places=2, max_digits=14)),
                ("currency", models.CharField(default="YER", max_length=6)),
                ("reference", models.CharField(max_length=160, unique=True)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("vendor", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="ledger_entries", to="marketplace.vendorprofile")),
                ("vendor_order", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="ledger_entries", to="marketplace.vendororder")),
            ],
        ),
        migrations.CreateModel(
            name="VendorOrderItem",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("order_item", models.OneToOneField(on_delete=django.db.models.deletion.PROTECT, related_name="vendor_order_item", to="marketplace.orderitem")),
                ("vendor_order", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="items", to="marketplace.vendororder")),
            ],
        ),
    ]
