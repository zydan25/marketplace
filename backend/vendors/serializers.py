import base64
import binascii

from django.core.files.base import ContentFile
from django.db import transaction
from rest_framework import serializers

from marketplace.models import User

from .models import VendorApplication, VendorProfile


class VendorOwnerSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "phone", "email", "first_name", "middle_name", "third_name", "last_name", "governorate", "role", "avatar", "is_phone_verified"]
        read_only_fields = fields


class VendorSerializer(serializers.ModelSerializer):
    owner = VendorOwnerSerializer(read_only=True)
    logo_url = serializers.SerializerMethodField()
    cover_url = serializers.SerializerMethodField()
    logo_data_url = serializers.CharField(write_only=True, required=False, allow_blank=True)
    cover_data_url = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = VendorProfile
        fields = ["id", "owner", "store_name", "slug", "description", "logo_url", "cover_url", "logo_data_url", "cover_data_url", "phone", "address", "status", "commission_percent", "settings", "created_at", "updated_at"]
        read_only_fields = ["id", "owner", "slug", "status", "commission_percent", "created_at", "updated_at"]

    def get_logo_url(self, obj):
        request = self.context.get("request")
        if not obj.logo:
            return None
        return request.build_absolute_uri(obj.logo.url) if request else obj.logo.url

    def get_cover_url(self, obj):
        request = self.context.get("request")
        if not obj.cover:
            return None
        return request.build_absolute_uri(obj.cover.url) if request else obj.cover.url

    def _data_file(self, value, prefix):
        if not value or ";base64," not in value:
            return None
        try:
            header, encoded = value.split(";base64,", 1)
            mime = header.split("/", 1)[1].split(";", 1)[0].lower() if "/" in header else "jpeg"
            extension = "jpg" if mime == "jpeg" else mime if mime in {"png", "webp", "gif"} else "jpg"
            raw = base64.b64decode(encoded, validate=True)
        except (ValueError, binascii.Error, TypeError):
            raise serializers.ValidationError({f"{prefix}_data_url": "الصورة المرسلة غير صالحة."})
        return ContentFile(raw, name=f"vendor-{prefix}-{self.instance.pk if self.instance else 'new'}.{extension}")

    @transaction.atomic
    def update(self, instance, validated_data):
        logo_data = validated_data.pop("logo_data_url", "")
        cover_data = validated_data.pop("cover_data_url", "")
        vendor = super().update(instance, validated_data)
        logo = self._data_file(logo_data, "logo")
        cover = self._data_file(cover_data, "cover")
        update_fields = []
        if logo is not None:
            vendor.logo.save(logo.name, logo, save=False)
            update_fields.append("logo")
        if cover is not None:
            vendor.cover.save(cover.name, cover, save=False)
            update_fields.append("cover")
        if update_fields:
            update_fields.append("updated_at")
            vendor.save(update_fields=update_fields)
        return vendor


class VendorApplicationSerializer(serializers.ModelSerializer):
    applicant = VendorOwnerSerializer(read_only=True)
    reviewed_by = VendorOwnerSerializer(read_only=True)

    class Meta:
        model = VendorApplication
        fields = ["id", "applicant", "store_name", "description", "phone", "address", "documents", "status", "review_note", "reviewed_by", "reviewed_at", "created_at", "updated_at"]
        read_only_fields = ["id", "applicant", "status", "review_note", "reviewed_by", "reviewed_at", "created_at", "updated_at"]
