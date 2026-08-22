from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings


class Migration(migrations.Migration):
    dependencies = [("marketplace", "0011_order_partial_fulfillment")]

    operations = [
        migrations.CreateModel(
            name="OrderChat",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("subject", models.CharField(blank=True, max_length=180)),
                ("is_closed", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("customer", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="order_chats_as_customer", to=settings.AUTH_USER_MODEL)),
                ("order", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="order_chats", to="marketplace.order")),
                ("vendor", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="order_chats", to="marketplace.vendorprofile")),
                ("vendor_order", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="order_chat", to="marketplace.vendororder")),
            ],
            options={"ordering": ["-updated_at", "-id"], "constraints": [models.UniqueConstraint(fields=["order", "vendor"], name="uniq_order_chat_per_vendor")], "indexes": [models.Index(fields=["customer", "updated_at"], name="marketplace_o_customer_19c8cc_idx"), models.Index(fields=["vendor", "updated_at"], name="marketplace_o_vendor_08fb2f_idx"), models.Index(fields=["order", "vendor"], name="marketplace_o_order_v_0b3ab4_idx")]},
        ),
        migrations.CreateModel(
            name="OrderChatMessage",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("body", models.TextField(blank=True)),
                ("attachment", models.ImageField(blank=True, null=True, upload_to="order_chats/")),
                ("is_read", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("chat", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="messages", to="marketplace.orderchat")),
                ("sender", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="order_chat_messages", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["created_at", "id"], "indexes": [models.Index(fields=["chat", "created_at"], name="marketplace_o_chat_id_c7b8dd_idx"), models.Index(fields=["chat", "is_read"], name="marketplace_o_chat_is_82b49d_idx")]},
        ),
    ]
