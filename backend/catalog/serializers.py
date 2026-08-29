import base64
import binascii

from django.core.files.base import ContentFile
from django.db import transaction
from django.db.models import Q
from django.utils.text import slugify
from rest_framework import serializers

from marketplace.models import User, VendorProfile

from .models import Category, CatalogOption, PriceGroup, Product, ProductImage, ProductVariant


class CatalogUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "id",
            "phone",
            "email",
            "first_name",
            "middle_name",
            "third_name",
            "last_name",
            "governorate",
            "role",
            "avatar",
            "points_balance",
        ]
        read_only_fields = ["id", "role"]


class CatalogVendorSerializer(serializers.ModelSerializer):
    owner = CatalogUserSerializer(read_only=True)
    logo_url = serializers.SerializerMethodField()
    cover_url = serializers.SerializerMethodField()

    class Meta:
        model = VendorProfile
        fields = [
            "id",
            "owner",
            "store_name",
            "slug",
            "description",
            "logo_url",
            "cover_url",
            "phone",
            "address",
            "status",
            "commission_percent",
            "settings",
        ]
        read_only_fields = ["id", "slug", "status", "commission_percent"]

    def get_logo_url(self, obj):
        return obj.logo.url if obj.logo else None

    def get_cover_url(self, obj):
        return obj.cover.url if obj.cover else None


class CategorySerializer(serializers.ModelSerializer):
    children_count = serializers.IntegerField(read_only=True)
    products_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Category
        fields = ["id", "name", "slug", "image", "parent", "is_active", "sort_order", "children_count", "products_count"]
        read_only_fields = ["id", "children_count", "products_count"]

    def validate(self, attrs):
        instance = self.instance
        parent = attrs.get("parent", getattr(instance, "parent", None))
        if instance and parent and parent.pk == instance.pk:
            raise serializers.ValidationError({"parent": "لا يمكن جعل الفئة أبًا لنفسها."})
        if instance and parent:
            cursor = parent
            seen = {instance.pk}
            while cursor is not None:
                if cursor.pk in seen:
                    raise serializers.ValidationError({"parent": "سلسلة الفئات تحتوي على حلقة غير صالحة."})
                seen.add(cursor.pk)
                cursor = cursor.parent
        return attrs


class ProductVariantSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False)
    available_stock = serializers.IntegerField(read_only=True)
    effective_price = serializers.SerializerMethodField()
    sku = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = ProductVariant
        fields = [
            "id",
            "sku",
            "color",
            "size",
            "price_override",
            "available_stock",
            "stock",
            "reserved_stock",
            "is_active",
            "effective_price",
        ]
        read_only_fields = ["available_stock", "effective_price", "reserved_stock"]

    def validate(self, attrs):
        stock = attrs.get("stock")
        variant_id = attrs.get("id")
        if stock is not None and variant_id:
            current = ProductVariant.objects.filter(id=variant_id).first()
            if current and stock < current.reserved_stock:
                raise serializers.ValidationError({"stock": "لا يمكن خفض المخزون عن الكمية المحجوزة."})
        sku = attrs.get("sku")
        if sku:
            qs = ProductVariant.objects.filter(sku=sku)
            if variant_id:
                qs = qs.exclude(pk=variant_id)
            if qs.exists():
                raise serializers.ValidationError({"sku": f"SKU مستخدم مسبقًا: {sku}"})
        return attrs

    def get_effective_price(self, obj):
        return obj.price_override if obj.price_override is not None else obj.product.effective_price


class ProductImageSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()

    class Meta:
        model = ProductImage
        fields = ["id", "product", "image", "url", "alt_text", "sort_order", "is_primary"]
        read_only_fields = ["id", "url"]

    def get_url(self, obj):
        if not obj.image:
            return None
        request = self.context.get("request")
        return request.build_absolute_uri(obj.image.url) if request else obj.image.url


class ProductSerializer(serializers.ModelSerializer):
    vendor = CatalogVendorSerializer(read_only=True)
    categories = CategorySerializer(many=True, read_only=True)
    category_ids = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.filter(is_active=True),
        many=True,
        source="categories",
        write_only=True,
        required=False,
    )
    effective_price = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    available_stock = serializers.IntegerField(read_only=True)
    discount_percent = serializers.IntegerField(read_only=True)
    main_image_url = serializers.SerializerMethodField()
    gallery = serializers.SerializerMethodField()
    image_data_urls = serializers.ListField(child=serializers.CharField(), write_only=True, required=False)
    main_image_data_url = serializers.CharField(write_only=True, required=False, allow_blank=True)
    keep_image_ids = serializers.ListField(child=serializers.IntegerField(), write_only=True, required=False)
    delete_image_ids = serializers.ListField(child=serializers.IntegerField(), write_only=True, required=False)
    variants = ProductVariantSerializer(many=True, required=False)

    class Meta:
        model = Product
        fields = [
            "id",
            "vendor",
            "categories",
            "category_ids",
            "sku",
            "name",
            "slug",
            "description",
            "brand",
            "material",
            "shipping_note",
            "return_policy",
            "price",
            "sale_price",
            "effective_price",
            "discount_percent",
            "currency",
            "stock",
            "reserved_stock",
            "available_stock",
            "colors",
            "sizes",
            "hashtags",
            "details",
            "main_image_url",
            "images",
            "gallery",
            "image_data_urls",
            "main_image_data_url",
            "keep_image_ids",
            "delete_image_ids",
            "variants",
            "rating",
            "reviews_count",
            "sold_count",
            "is_published",
            "is_trending",
        ]
        read_only_fields = [
            "id",
            "vendor",
            "reserved_stock",
            "available_stock",
            "effective_price",
            "discount_percent",
            "main_image_url",
            "gallery",
            "rating",
            "reviews_count",
            "sold_count",
        ]

    def _absolute(self, value):
        if not value:
            return None
        request = self.context.get("request")
        return value if value.startswith(("http://", "https://")) else request.build_absolute_uri(value) if request else value

    def get_main_image_url(self, obj):
        return self._absolute(obj.main_image.url) if obj.main_image else None

    def get_gallery(self, obj):
        output = []
        for item in obj.image_items.all():
            output.append(
                {
                    "id": item.id,
                    "url": self._absolute(item.image.url),
                    "alt": item.alt_text,
                    "sort_order": item.sort_order,
                    "is_primary": item.is_primary,
                }
            )
        if not output and obj.images:
            for index, value in enumerate(obj.images):
                url = value.get("url") if isinstance(value, dict) else value
                if url:
                    output.append({"id": -index - 1, "url": self._absolute(str(url)), "alt": "", "sort_order": index, "is_primary": index == 0})
        return output

    def _validate_variant_rows(self, rows, instance=None):
        seen_dimensions = set()
        seen_skus = set()
        existing_by_id = {v.id: v for v in instance.variants.all()} if instance else {}
        for row in rows:
            variant_id = row.get("id")
            if variant_id and variant_id not in existing_by_id:
                raise serializers.ValidationError({"variants": f"الصنف {variant_id} لا ينتمي إلى هذا المنتج."})
            key = (str(row.get("color", "")).strip(), str(row.get("size", "")).strip())
            if key in seen_dimensions:
                raise serializers.ValidationError({"variants": "لا يمكن تكرار تركيبة اللون والمقاس داخل المنتج."})
            seen_dimensions.add(key)
            sku = str(row.get("sku", "")).strip()
            if sku and sku in seen_skus:
                raise serializers.ValidationError({"variants": f"SKU مكرر داخل الطلب: {sku}"})
            if sku:
                seen_skus.add(sku)
                qs = ProductVariant.objects.filter(sku=sku)
                if variant_id:
                    qs = qs.exclude(pk=variant_id)
                if qs.exists():
                    raise serializers.ValidationError({"variants": f"SKU مستخدم مسبقًا: {sku}"})

    def _save_data_images(self, product, urls):
        for index, data_url in enumerate(urls or []):
            if not data_url or ";base64," not in data_url:
                continue
            header, encoded = data_url.split(";base64,", 1)
            mime = header.split("/", 1)[1].split(";", 1)[0].lower() if "/" in header else "jpeg"
            extension = "jpg" if mime == "jpeg" else mime if mime in {"png", "webp", "gif"} else "jpg"
            try:
                raw = base64.b64decode(encoded, validate=True)
            except (ValueError, binascii.Error, TypeError):
                continue
            content = ContentFile(raw, name=f"product-{product.pk}-{index}.{extension}")
            ProductImage.objects.create(product=product, image=content, sort_order=index, is_primary=(index == 0 and not product.image_items.exists()))
        if not product.main_image and product.image_items.exists():
            product.main_image = product.image_items.order_by("sort_order", "id").first().image
            product.save(update_fields=["main_image", "updated_at"])

    @transaction.atomic
    def create(self, validated_data):
        urls = validated_data.pop("image_data_urls", [])
        main_url = validated_data.pop("main_image_data_url", "")
        validated_data.pop("keep_image_ids", None)
        validated_data.pop("delete_image_ids", None)
        variants_data = validated_data.pop("variants", [])
        self._validate_variant_rows(variants_data)
        categories = validated_data.pop("categories", None)
        product = super().create(validated_data)
        if categories is not None:
            product.categories.set(categories)
        for row in variants_data:
            ProductVariant.objects.create(product=product, **row)
        self._save_data_images(product, ([main_url] if main_url else []) + urls)
        return product

    @transaction.atomic
    def update(self, instance, validated_data):
        urls = validated_data.pop("image_data_urls", [])
        main_url = validated_data.pop("main_image_data_url", "")
        keep_value = validated_data.pop("keep_image_ids", None)
        keep_ids = set(keep_value or []) if keep_value is not None else None
        delete_ids = set(validated_data.pop("delete_image_ids", []))
        variants_data = validated_data.pop("variants", None)
        if variants_data is not None:
            self._validate_variant_rows(variants_data, instance=instance)
        categories = validated_data.pop("categories", None)
        product = super().update(instance, validated_data)
        if categories is not None:
            product.categories.set(categories)
        if delete_ids:
            product.image_items.filter(id__in=delete_ids).delete()
        if keep_ids is not None:
            product.image_items.exclude(id__in=keep_ids).delete()
        if variants_data is not None:
            existing = {v.id: v for v in product.variants.all()}
            incoming_ids = set()
            for row in variants_data:
                row = dict(row)
                variant_id = row.pop("id", None)
                if variant_id:
                    variant = existing[variant_id]
                    for key, value in row.items():
                        setattr(variant, key, value)
                    variant.is_active = True
                    variant.save()
                    incoming_ids.add(variant_id)
                else:
                    incoming = ProductVariant.objects.create(product=product, is_active=True, **row)
                    incoming_ids.add(incoming.id)
            product.variants.exclude(id__in=incoming_ids).update(is_active=False)
        self._save_data_images(product, ([main_url] if main_url else []) + urls)
        return product


class CatalogOptionSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True)

    class Meta:
        model = CatalogOption
        fields = ["id", "group", "name", "slug", "category", "category_name", "sort_order", "is_active"]
        read_only_fields = ["id", "slug"]

    def validate(self, attrs):
        name = str(attrs.get("name", getattr(self.instance, "name", ""))).strip()
        group = str(attrs.get("group", getattr(self.instance, "group", ""))).strip().lower()
        if not name or not group:
            raise serializers.ValidationError({"name": "اسم الخيار مطلوب", "group": "نوع الخيار مطلوب"})
        return attrs


class PriceGroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = PriceGroup
        fields = ["id", "name", "code", "adjustment_type", "percentage", "fixed_amount", "is_active", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]