from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("communication", "0002_delete_conversation_delete_message_and_more"),
        ("orders", "0002_delete_inventoryreservation_delete_order_and_more"),
        ("vendors", "0002_delete_vendorapplication_delete_vendorprofile_and_more"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.CreateModel(
                    name="OrderChat",
                    fields=[
                        ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                        ("subject", models.CharField(blank=True, max_length=180)),
                        ("is_closed", models.BooleanField(default=False)),
                        ("created_at", models.DateTimeField(auto_now_add=True)),
                        ("updated_at", models.DateTimeField(auto_now=True)),
                        ("customer", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="order_chats_as_customer", to=settings.AUTH_USER_MODEL)),
                        ("order", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="order_chats", to="orders.order")),
                        ("vendor", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="order_chats", to="vendors.vendorprofile")),
                        ("vendor_order", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="order_chat", to="orders.vendororder")),
                    ],
                    options={
                        "db_table": "marketplace_orderchat",
                        "ordering": ["-updated_at", "-id"],
                        "constraints": [models.UniqueConstraint(fields=("order", "vendor"), name="uniq_order_chat_per_vendor")],
                        "indexes": [
                            models.Index(fields=["customer", "updated_at"], name="marketplace_custome_4646f8_idx"),
                            models.Index(fields=["vendor", "updated_at"], name="marketplace_vendor__b38893_idx"),
                            models.Index(fields=["order", "vendor"], name="marketplace_order_i_65fe02_idx"),
                        ],
                    },
                ),
                migrations.CreateModel(
                    name="OrderChatMessage",
                    fields=[
                        ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                        ("body", models.TextField(blank=True)),
                        ("attachment", models.ImageField(blank=True, null=True, upload_to="order_chats/")),
                        ("is_read", models.BooleanField(default=False)),
                        ("created_at", models.DateTimeField(auto_now_add=True)),
                        ("chat", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="messages", to="communication.orderchat")),
                        ("sender", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="order_chat_messages", to=settings.AUTH_USER_MODEL)),
                    ],
                    options={
                        "db_table": "marketplace_orderchatmessage",
                        "ordering": ["created_at", "id"],
                        "indexes": [
                            models.Index(fields=["chat", "created_at"], name="marketplace_chat_id_2cd04e_idx"),
                            models.Index(fields=["chat", "is_read"], name="marketplace_chat_id_650094_idx"),
                        ],
                    },
                ),
            ],
        )
    ]
