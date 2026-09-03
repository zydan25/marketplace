from marketplace.models import Order as LegacyOrder, OrderItem as LegacyOrderItem
from marketplace.models_extended import OrderStatusHistory as LegacyOrderStatusHistory
from marketplace.marketplace_models import (
    InventoryReservation as LegacyInventoryReservation,
    Payment as LegacyPayment,
    Shipment as LegacyShipment,
    VendorOrder as LegacyVendorOrder,
    VendorOrderItem as LegacyVendorOrderItem,
)


class Order(LegacyOrder):
    class Meta:
        proxy = True
        verbose_name = "طلب"
        verbose_name_plural = "الطلبات"


class OrderItem(LegacyOrderItem):
    class Meta:
        proxy = True
        verbose_name = "عنصر طلب"
        verbose_name_plural = "عناصر الطلبات"


class VendorOrder(LegacyVendorOrder):
    class Meta:
        proxy = True
        verbose_name = "طلب تاجر"
        verbose_name_plural = "طلبات التجار"


class VendorOrderItem(LegacyVendorOrderItem):
    class Meta:
        proxy = True
        verbose_name = "عنصر طلب تاجر"
        verbose_name_plural = "عناصر طلبات التجار"


class OrderStatusHistory(LegacyOrderStatusHistory):
    class Meta:
        proxy = True
        verbose_name = "سجل حالة الطلب"
        verbose_name_plural = "سجل حالات الطلبات"


class Shipment(LegacyShipment):
    class Meta:
        proxy = True
        verbose_name = "شحنة"
        verbose_name_plural = "الشحنات"


class InventoryReservation(LegacyInventoryReservation):
    class Meta:
        proxy = True
        verbose_name = "حجز مخزون"
        verbose_name_plural = "حجوزات المخزون"


class Payment(LegacyPayment):
    class Meta:
        proxy = True
        verbose_name = "دفعة"
        verbose_name_plural = "الدفعات"
