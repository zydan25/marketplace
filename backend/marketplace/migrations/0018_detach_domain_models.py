from django.db import migrations


MOVED_MODELS = [
    "Category",
    "Conversation",
    "Coupon",
    "Message",
    "Order",
    "OrderItem",
    "Product",
    "ProductImage",
    "Notification",
    "Referral",
    "VendorProfile",
    "VendorPayout",
    "StorefrontSection",
    "Wallet",
    "WalletTransaction",
    "PriceGroup",
    "City",
    "ProductVariant",
    "OrderStatusHistory",
    "Address",
    "GiftTransfer",
    "Loan",
    "VendorOrder",
    "VendorOrderItem",
    "Payment",
    "Shipment",
    "InventoryReservation",
    "VendorLedgerEntry",
    "CouponRedemption",
    "VendorApplication",
    "StorefrontMedia",
    "CatalogOption",
    "CurrencyRate",
    "UserPreference",
    "VendorCityShipping",
]


class Migration(migrations.Migration):
    dependencies = [("marketplace", "0017_seed_global_storefront_themes")]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[migrations.DeleteModel(name=name) for name in MOVED_MODELS],
        )
    ]
