from django.contrib import admin

from .models import InventoryReservation, Order, OrderItem, OrderStatusHistory, Payment, Shipment, VendorOrder, VendorOrderItem


class ReadOnlyDomainAdmin(admin.ModelAdmin):
    readonly_fields = ["created_at", "updated_at"]


@admin.register(Order)
class OrderAdmin(ReadOnlyDomainAdmin):
    list_display = ("order_number", "customer", "status", "payment_status", "total", "currency", "created_at")
    list_filter = ("status", "payment_status", "payment_method", "currency")
    search_fields = ("order_number", "customer__phone", "customer__username")


@admin.register(OrderItem)
class OrderItemAdmin(ReadOnlyDomainAdmin):
    list_display = ("order", "vendor", "product", "quantity", "unit_price", "vendor_net")
    search_fields = ("order__order_number", "product__name", "sku_snapshot", "vendor__store_name")


@admin.register(VendorOrder)
class VendorOrderAdmin(ReadOnlyDomainAdmin):
    list_display = ("order_number", "order", "vendor", "status", "total", "vendor_net")
    list_filter = ("status", "currency")
    search_fields = ("order_number", "order__order_number", "vendor__store_name")


@admin.register(VendorOrderItem)
class VendorOrderItemAdmin(admin.ModelAdmin):
    list_display = ("vendor_order", "order_item")


@admin.register(OrderStatusHistory)
class OrderStatusHistoryAdmin(admin.ModelAdmin):
    list_display = ("order", "old_status", "new_status", "changed_by", "created_at")
    list_filter = ("old_status", "new_status")
    search_fields = ("order__order_number", "note")


@admin.register(Shipment)
class ShipmentAdmin(ReadOnlyDomainAdmin):
    list_display = ("vendor_order", "carrier", "tracking_number", "status", "shipped_at", "delivered_at")
    list_filter = ("status", "carrier")
    search_fields = ("tracking_number", "carrier", "vendor_order__order_number")


@admin.register(InventoryReservation)
class InventoryReservationAdmin(ReadOnlyDomainAdmin):
    list_display = ("order", "product", "variant", "quantity", "status", "expires_at")
    list_filter = ("status",)
    search_fields = ("order__order_number", "product__name", "variant__sku")


@admin.register(Payment)
class PaymentAdmin(ReadOnlyDomainAdmin):
    list_display = ("order", "provider", "method", "amount", "currency", "status", "paid_at")
    list_filter = ("status", "provider", "method", "currency")
    search_fields = ("order__order_number", "transaction_id")
