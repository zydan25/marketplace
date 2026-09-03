from rest_framework import serializers

from vendors.models import VendorProfile

from .models import DesignTheme, StorefrontMedia, StorefrontSection


class DesignThemeSerializer(serializers.ModelSerializer):
    class Meta:
        model = DesignTheme
        fields = [
            "id", "name", "vendor", "is_global", "is_active", "tokens", "layout", "sections",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "vendor", "is_global", "created_at", "updated_at"]


class StorefrontSectionSerializer(serializers.ModelSerializer):
    vendor_name = serializers.CharField(source="vendor.store_name", read_only=True)

    class Meta:
        model = StorefrontSection
        fields = [
            "id", "owner", "vendor", "vendor_name", "title", "section_type", "config",
            "sort_order", "is_visible", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "owner", "vendor_name", "created_at", "updated_at"]


class StorefrontMediaSerializer(serializers.ModelSerializer):
    vendor_name = serializers.CharField(source="vendor.store_name", read_only=True)
    url = serializers.SerializerMethodField()

    class Meta:
        model = StorefrontMedia
        fields = [
            "id", "name", "image", "url", "alt_text", "target_url", "vendor", "vendor_name",
            "is_active", "sort_order", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "vendor_name", "url", "created_at", "updated_at"]

    def get_url(self, obj):
        if not obj.image:
            return None
        request = self.context.get("request")
        return request.build_absolute_uri(obj.image.url) if request else obj.image.url


class StorefrontVendorSerializer(serializers.ModelSerializer):
    class Meta:
        model = VendorProfile
        fields = ["id", "store_name", "slug", "status"]
        read_only_fields = fields
