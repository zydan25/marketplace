from django.contrib.auth import get_user_model
from rest_framework import serializers

from catalog.models import Product
from communication.models import OrderChat
from finance.models import VendorPayout
from promotions.models import Coupon
from vendors.models import VendorProfile

from .models import (
    InventoryReservation,
    Order,
    OrderItem,
    OrderStatusHistory,
    Payment,
    Shipment,
    VendorOrder,
    VendorOrderItem,
)

User = get_user_model()


class OrderUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "id", "phone", "email", "first_name", "middle_name", "third_name",
            "last_name", "governorate", "role", "avatar", "points_balance",
        ]
        read_only_fields = fields


class OrderItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)
    product_image = serializers.SerializerMethodField()
    vendor_name = serializers.CharField(source="vendor.store_name", read_only=True)

    class Meta:
        model = OrderItem
        fields = [
            "id", "order", "product", "product_name", "product_image", "vendor", "vendor_name",
            "name_snapshot", "sku_snapshot", "quantity", "unit_price", "color", "size",
            "vendor_total", "commission", "vendor_net",
        ]
        read_only_fields = [
            "id", "order", "vendor", "vendor_name", "product_name", "product_image",
            "name_snapshot", "sku_snapshot", "unit_price", "vendor_total", "commission", "vendor_net",
        ]

    def get_product_image(self, obj):
        if not obj.product or not obj.product.main_image:
            return None
        request = self.context.get("request")
        return request.build_absolute_uri(obj.product.main_image.url) if request else obj.product.main_image.url


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    customer = OrderUserSerializer(read_only=True)
    vendor_count = serializers.IntegerField(source="vendor_orders.count", read_only=True)

    class Meta:
        model = Order
        fields = [
            "id", "order_number", "customer", "status", "subtotal", "shipping_fee", "discount",
            "total", "currency", "shipping_address", "payment_method", "payment_status", "metadata",
            "vendor_count", "items", "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "order_number", "customer", "status", "subtotal", "shipping_fee", "discount", "total",
            "currency", "payment_status", "metadata", "vendor_count", "items", "created_at", "updated_at",
        ]


class VendorOrderSerializer(serializers.ModelSerializer):
    vendor_name = serializers.CharField(source="vendor.store_name", read_only=True)
    parent_order_number = serializers.CharField(source="order.order_number", read_only=True)

    class Meta:
        model = VendorOrder
        fields = [
            "id", "order", "parent_order_number", "vendor", "vendor_name", "order_number", "status",
            "subtotal", "shipping_fee", "discount", "total", "commission", "vendor_net", "currency",
            "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "order", "parent_order_number", "vendor", "vendor_name", "order_number", "status",
            "subtotal", "shipping_fee", "discount", "total", "commission", "vendor_net", "currency",
            "created_at", "updated_at",
        ]


class VendorOrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = VendorOrderItem
        fields = ["id", "vendor_order", "order_item"]
        read_only_fields = fields


class StatusHistorySerializer(serializers.ModelSerializer):
    changed_by = OrderUserSerializer(read_only=True)

    class Meta:
        model = OrderStatusHistory
        fields = ["id", "order", "old_status", "new_status", "changed_by", "note", "created_at", "updated_at"]
        read_only_fields = fields


class ShipmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Shipment
        fields = [
            "id", "vendor_order", "carrier", "tracking_number", "status",
            "shipped_at", "delivered_at", "metadata", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "vendor_order", "created_at", "updated_at"]


class ReservationSerializer(serializers.ModelSerializer):
    class Meta:
        model = InventoryReservation
        fields = [
            "id", "order", "order_item", "product", "variant", "quantity", "status",
            "expires_at", "created_at", "updated_at",
        ]
        read_only_fields = fields


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = [
            "id", "order", "provider", "method", "transaction_id", "amount", "refunded_amount",
            "currency", "status", "paid_at", "metadata", "created_at", "updated_at",
        ]
        read_only_fields = fields


class VendorPayoutSerializer(serializers.ModelSerializer):
    vendor_name = serializers.CharField(source="vendor.store_name", read_only=True)

    class Meta:
        model = VendorPayout
        fields = [
            "id", "vendor", "vendor_name", "vendor_order", "order", "amount", "currency",
            "status", "reference", "note", "created_at", "updated_at",
        ]
        read_only_fields = fields


class CouponLookupSerializer(serializers.ModelSerializer):
    class Meta:
        model = Coupon
        fields = ["id", "code", "discount_percent", "discount_amount", "minimum_order", "starts_at", "ends_at", "is_active"]
        read_only_fields = fields


class OrderChatSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderChat
        fields = ["id", "order", "vendor_order", "customer", "vendor", "subject", "is_closed", "created_at", "updated_at"]
        read_only_fields = fields


class ProductSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ["id", "name", "slug", "sku", "price", "sale_price", "currency", "stock", "reserved_stock", "is_published"]
        read_only_fields = fields


class VendorSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = VendorProfile
        fields = ["id", "store_name", "slug", "status"]
        read_only_fields = fields
