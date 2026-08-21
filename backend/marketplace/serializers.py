import base64
import binascii

from django.core.files.base import ContentFile
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
    ProductImage,
    StorefrontSection,
    User,
    VendorProfile,
    Wallet,
    WalletTransaction,
)


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "phone", "email", "first_name", "middle_name", "third_name", "last_name", "governorate", "role", "avatar", "points_balance"]
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
    category_ids = serializers.PrimaryKeyRelatedField(queryset=Category.objects.filter(is_active=True), many=True, source="categories", write_only=True, required=False)
    effective_price = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    discount_percent = serializers.IntegerField(read_only=True)
    main_image_url = serializers.SerializerMethodField()
    gallery = serializers.SerializerMethodField()
    image_data_urls = serializers.ListField(child=serializers.CharField(), write_only=True, required=False)
    main_image_data_url = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = Product
        fields = ["id", "vendor", "categories", "category_ids", "sku", "name", "slug", "description", "brand", "material", "shipping_note", "return_policy", "price", "sale_price", "effective_price", "discount_percent", "currency", "stock", "colors", "sizes", "hashtags", "details", "main_image_url", "images", "gallery", "image_data_urls", "main_image_data_url", "rating", "reviews_count", "sold_count", "is_published", "is_trending"]
        read_only_fields = ["id", "vendor", "effective_price", "discount_percent", "main_image_url", "gallery", "rating", "reviews_count", "sold_count"]

    def _absolute(self, value):
        if not value:
            return None
        request = self.context.get("request")
        if value.startswith("http://") or value.startswith("https://"):
            return value
        return request.build_absolute_uri(value) if request else value

    def get_main_image_url(self, obj):
        return self._absolute(obj.main_image.url) if obj.main_image else None

    def get_gallery(self, obj):
        output = []
        for item in obj.image_items.all():
            output.append({"id": item.id, "url": self._absolute(item.image.url), "alt": item.alt_text, "sort_order": item.sort_order, "is_primary": item.is_primary})
        if not output and obj.images:
            for index, value in enumerate(obj.images):
                url = value.get("url") if isinstance(value, dict) else value
                if url:
                    output.append({"id": -index - 1, "url": self._absolute(str(url)), "alt": "", "sort_order": index, "is_primary": index == 0})
        return output

    def _save_data_images(self, product, urls):
        for index, data_url in enumerate(urls or []):
            if not data_url or ";base64," not in data_url:
                continue
            header, encoded = data_url.split(";base64,", 1)
            extension = header.split("/")[-1].split(";")[0] or "jpg"
            try:
                content = ContentFile(base64.b64decode(encoded), name=f"product-{product.pk}-{index}.{extension}")
            except (ValueError, binascii.Error):
                continue
            ProductImage.objects.create(product=product, image=content, sort_order=index, is_primary=index == 0)
        if not product.main_image and product.image_items.exists():
            product.main_image = product.image_items.first().image
            product.save(update_fields=["main_image", "updated_at"])

    def create(self, validated_data):
        urls = validated_data.pop("image_data_urls", [])
        main_url = validated_data.pop("main_image_data_url", "")
        product = super().create(validated_data)
        self._save_data_images(product, ([main_url] if main_url else []) + urls)
        return product

    def update(self, instance, validated_data):
        urls = validated_data.pop("image_data_urls", [])
        main_url = validated_data.pop("main_image_data_url", "")
        product = super().update(instance, validated_data)
        self._save_data_images(product, ([main_url] if main_url else []) + urls)
        return product


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
    user = UserSerializer(read_only=True)
    transactions = WalletTransactionSerializer(many=True, read_only=True)

    class Meta:
        model = Wallet
        fields = ["id", "user", "balance", "currency", "is_locked", "transactions"]
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
