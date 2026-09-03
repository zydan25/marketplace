from django.db import migrations


MOVED_MODELS = [
    "Address",
    "CatalogOption",
    "Category",
    "City",
    "Conversation",
    "Coupon",
    "CouponRedemption",
    "CurrencyRate",
    "DesignTheme",
    "GiftTransfer",
    "InventoryReservation",
    "Loan",
    "Message",
    "Notification",
    "Order",
    "OrderChat",
    "OrderChatMessage",
    "OrderItem",
    "OrderStatusHistory",
    "Payment",
    "PriceGroup",
    "Product",
    "ProductImage",
    "ProductVariant",
    "Referral",
    "Shipment",
    "StorefrontMedia",
    "StorefrontSection",
    "UserPreference",
    "VendorApplication",
    "VendorCityShipping",
    "VendorLedgerEntry",
    "VendorOrder",
    "VendorOrderItem",
    "VendorPayout",
    "VendorProfile",
    "Wallet",
    "WalletTransaction",
]


class Migration(migrations.Migration):
    dependencies = [
        ("marketplace", "0017_seed_global_storefront_themes"),
        ("accounts", "0001_initial"),
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
            state_operations=[migrations.DeleteModel(name=name) for name in MOVED_MODELS],
        )
    ]
