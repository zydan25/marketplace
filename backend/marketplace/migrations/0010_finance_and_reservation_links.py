from django.db import migrations, models
import django.db.models.deletion
from django.core.validators import MinValueValidator


class Migration(migrations.Migration):
    dependencies = [("marketplace", "0009_productvariant_is_active")]

    operations = [
        migrations.AddField(
            model_name="vendorpayout",
            name="vendor_order",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="payouts", to="marketplace.vendororder"),
        ),
        migrations.AddField(
            model_name="inventoryreservation",
            name="order_item",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="inventory_reservations", to="marketplace.orderitem"),
        ),
        migrations.AddIndex(
            model_name="inventoryreservation",
            index=models.Index(fields=["order_item", "status"], name="marketplace_i_order_i_d2a9a8_idx"),
        ),
        migrations.CreateModel(
            name="CouponRedemption",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("code_snapshot", models.CharField(max_length=50)),
                ("discount_amount", models.DecimalField(decimal_places=2, max_digits=14, validators=[MinValueValidator(0)])),
                ("currency", models.CharField(default="YER", max_length=6)),
                ("coupon", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="redemptions", to="marketplace.coupon")),
                ("order", models.OneToOneField(on_delete=django.db.models.deletion.PROTECT, related_name="coupon_redemption", to="marketplace.order")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="coupon_redemptions", to="marketplace.user")),
            ],
            options={"indexes": [models.Index(fields=["coupon", "user"], name="marketplace_c_coupon_u_3e7e20_idx"), models.Index(fields=["created_at"], name="marketplace_c_created_2f5f61_idx")]},
        ),
    ]
