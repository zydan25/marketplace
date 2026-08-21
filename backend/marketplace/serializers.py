from rest_framework import serializers
from .models import (
    Category,
    Conversation,
    Coupon,
    DesignTheme,
    Message,
    Notification,
    Order,
    OrderItem,
    Product,
    StorefrontSection,
    User,
    VendorProfile,
    Wallet,
    WalletTransaction,
)


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "phone", "email", "first_name", "middle_name", "third_name", "last_name", "governorate", "role", "avatar"]
        read_only_fields = ["id", "role"]


class VendorSerializer(serializers.ModelSerializer):
    owner = UserSerializer(read_only=True)
    logo_url = serializers.SerializerMethodField()
    cover_url = serializers.SerializerMethodField()

    class Meta:
        model = VendorProfile
        fields = ["id", "owner", "store_name", "slug", "description", "logo_url", "cover_url", "phone", "address", "status", "commission_percent", "settings"]
        read_only_fields = ["id", "slug", "status", "commission_percent"]

    def get_logo_url(self, obj):
        return obj.logo.url if obj.logo else None

    def get_cover_url(self, obj):
        return obj.cover.url if obj.cover else None


class DesignThemeSerializer(serializers.ModelSerializer):
    class Meta:
        model = DesignTheme
        fields = ["id", "name", "vendor", "is_global", "is_active", "tokens", "layout", "sections"]
        read_only_fields = ["id", "is_global"]


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name", "slug", "image", "parent", "is_active", "sort_order"]


class ProductSerializer(serializers.ModelSerializer):
    vendor = VendorSerializer(read_only=True)
    categories = CategorySerializer(many=True, read_only=True)
    effective_price = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    discount_percent = serializers.IntegerField(read_only=True)
    main_image_url = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = ["id", "vendor", "categories", "sku", "name", "slug", "description", "price", "sale_price", "effective_price", "discount_percent", "currency", "stock", "colors", "sizes", "hashtags", "details", "main_image_url", "images", "rating", "reviews_count", "is_published", "is_trending"]

    def get_main_image_url(self, obj):
        return obj.main_image.url if obj.main_image else None


class StorefrontSectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = StorefrontSection
        fields = ["id", "title", "section_type", "vendor", "config", "sort_order", "is_visible"]
        read_only_fields = ["id"]


class WalletTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = WalletTransaction
        fields = ["id", "transaction_type", "amount", "balance_after", "reference", "note", "metadata", "created_at"]
        read_only_fields = fields


class WalletSerializer(serializers.ModelSerializer):
    transactions = WalletTransactionSerializer(many=True, read_only=True)

    class Meta:
        model = Wallet
        fields = ["id", "balance", "currency", "is_locked", "transactions"]
        read_only_fields = ["id", "balance", "is_locked", "transactions"]


class CouponSerializer(serializers.ModelSerializer):
    class Meta:
        model = Coupon
        fields = ["id", "code", "discount_percent", "discount_amount", "minimum_order", "usage_limit", "used_count", "starts_at", "ends_at", "is_active"]
        read_only_fields = ["used_count"]


class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = ["id", "product", "vendor", "name_snapshot", "sku_snapshot", "quantity", "unit_price", "color", "size", "vendor_total", "commission", "vendor_net"]
        read_only_fields = ["id", "vendor", "name_snapshot", "sku_snapshot", "unit_price", "vendor_total", "commission", "vendor_net"]


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    customer = UserSerializer(read_only=True)

    class Meta:
        model = Order
        fields = ["id", "order_number", "customer", "status", "subtotal", "shipping_fee", "discount", "total", "currency", "shipping_address", "payment_method", "payment_status", "items", "created_at", "updated_at"]
        read_only_fields = ["id", "order_number", "customer", "status", "subtotal", "discount", "total", "payment_status", "items", "created_at", "updated_at"]


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ["id", "title", "body", "image", "product", "is_read", "created_at"]
        read_only_fields = ["id", "created_at"]


class MessageSerializer(serializers.ModelSerializer):
    sender = UserSerializer(read_only=True)

    class Meta:
        model = Message
        fields = ["id", "conversation", "sender", "body", "attachment", "is_read", "created_at"]
        read_only_fields = ["id", "conversation", "sender", "is_read", "created_at"]


class ConversationSerializer(serializers.ModelSerializer):
    messages = MessageSerializer(many=True, read_only=True)

    class Meta:
        model = Conversation
        fields = ["id", "customer", "vendor", "order", "subject", "is_closed", "messages", "created_at", "updated_at"]
        read_only_fields = ["customer", "messages", "created_at", "updated_at"]
