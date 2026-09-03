from django.db import migrations, models
import django.db.models.deletion


MOVED_MODELS = [
    "Address", "CatalogOption", "Category", "Conversation", "Coupon", "CouponRedemption",
    "CurrencyRate", "DesignTheme", "GiftTransfer", "InventoryReservation", "Loan", "Message",
    "Notification", "Order", "OrderItem", "OrderStatusHistory", "Payment", "PriceGroup",
    "Product", "ProductImage", "ProductVariant", "Referral", "Shipment", "StorefrontMedia",
    "StorefrontSection", "UserPreference", "VendorApplication", "VendorCityShipping",
    "VendorLedgerEntry", "VendorOrderItem", "VendorOrder", "VendorPayout", "VendorProfile",
    "Wallet", "WalletTransaction",
]


class Migration(migrations.Migration):
    dependencies = [
        ("marketplace", "0017_seed_global_storefront_themes"),
        ("accounts", "0002_delete_userpreference_userpreference"),
        ("catalog", "0002_delete_catalogoption_delete_category_city_and_more"),
        ("vendors", "0002_delete_vendorapplication_delete_vendorprofile_and_more"),
        ("storefront", "0002_delete_designtheme_delete_storefrontmedia_and_more"),
        ("orders", "0002_delete_inventoryreservation_delete_order_and_more"),
        ("finance", "0002_delete_currencyrate_delete_vendorcityshipping_and_more"),
        ("communication", "0002_delete_conversation_delete_message_and_more"),
        ("promotions", "0002_delete_address_delete_coupon_delete_couponredemption_and_more"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.AlterField(
                    model_name="orderchat",
                    name="order",
                    field=models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="order_chats",
                        to="orders.order",
                    ),
                ),
                migrations.AlterField(
                    model_name="orderchat",
                    name="vendor_order",
                    field=models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="order_chat",
                        to="orders.vendororder",
                    ),
                ),
                migrations.AlterField(
                    model_name="orderchat",
                    name="vendor",
                    field=models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="order_chats",
                        to="vendors.vendorprofile",
                    ),
                ),
                *[migrations.DeleteModel(name=name) for name in MOVED_MODELS],
            ],
        )
    ]
