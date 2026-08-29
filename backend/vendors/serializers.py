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

    class Meta:
        model = VendorProfile
        fields = ["id", "owner", "store_name", "slug", "description", "logo_url", "cover_url", "phone", "address", "status", "commission_percent", "settings", "created_at", "updated_at"]
        read_only_fields = ["id", "owner", "slug", "status", "commission_percent", "created_at", "updated_at"]

    def get_logo_url(self, obj):
        return obj.logo.url if obj.logo else None

    def get_cover_url(self, obj):
        return obj.cover.url if obj.cover else None


class VendorApplicationSerializer(serializers.ModelSerializer):
    applicant = VendorOwnerSerializer(read_only=True)
    reviewed_by = VendorOwnerSerializer(read_only=True)

    class Meta:
        model = VendorApplication
        fields = ["id", "applicant", "store_name", "description", "phone", "address", "documents", "status", "review_note", "reviewed_by", "reviewed_at", "created_at", "updated_at"]
        read_only_fields = ["id", "applicant", "status", "review_note", "reviewed_by", "reviewed_at", "created_at", "updated_at"]
