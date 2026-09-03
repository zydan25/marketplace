from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [("marketplace", "0017_seed_global_storefront_themes")]
    operations = [
        migrations.CreateModel(name="Order", fields=[], options={"verbose_name": "طلب", "verbose_name_plural": "الطلبات", "proxy": True}, bases=("marketplace.order",)),
        migrations.CreateModel(name="OrderItem", fields=[], options={"verbose_name": "عنصر طلب", "verbose_name_plural": "عناصر الطلبات", "proxy": True}, bases=("marketplace.orderitem",)),
        migrations.CreateModel(name="VendorOrder", fields=[], options={"verbose_name": "طلب تاجر", "verbose_name_plural": "طلبات التجار", "proxy": True}, bases=("marketplace.vendororder",)),
        migrations.CreateModel(name="VendorOrderItem", fields=[], options={"verbose_name": "عنصر طلب تاجر", "verbose_name_plural": "عناصر طلبات التجار", "proxy": True}, bases=("marketplace.vendororderitem",)),
        migrations.CreateModel(name="OrderStatusHistory", fields=[], options={"verbose_name": "سجل حالة الطلب", "verbose_name_plural": "سجل حالات الطلبات", "proxy": True}, bases=("marketplace.orderstatushistory",)),
        migrations.CreateModel(name="Shipment", fields=[], options={"verbose_name": "شحنة", "verbose_name_plural": "الشحنات", "proxy": True}, bases=("marketplace.shipment",)),
        migrations.CreateModel(name="InventoryReservation", fields=[], options={"verbose_name": "حجز مخزون", "verbose_name_plural": "حجوزات المخزون", "proxy": True}, bases=("marketplace.inventoryreservation",)),
        migrations.CreateModel(name="Payment", fields=[], options={"verbose_name": "دفعة", "verbose_name_plural": "الدفعات", "proxy": True}, bases=("marketplace.payment",)),
    ]
