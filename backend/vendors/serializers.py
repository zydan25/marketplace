from rest_framework import serializers

from accounts.serializers import UserSerializer

from .models import VendorApplication, VendorProfile


class VendorSerializer(serializers.ModelSerializer):
    owner = UserSerializer(read_only=True)
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
    applicant = UserSerializer(read_only=True)
    reviewed_by = UserSerializer(read_only=True)

    class Meta:
        model = VendorApplication
        fields = ["id", "applicant", "store_name", "description", "phone", "address", "documents", "status", "review_note", "reviewed_by", "reviewed_at", "created_at", "updated_at"]
        read_only_fields = ["id", "applicant", "status", "review_note", "reviewed_by", "reviewed_at", "created_at", "updated_at"]
