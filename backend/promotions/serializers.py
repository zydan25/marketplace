from rest_framework import serializers

from orders.models import Order

from .models import Address, Coupon, CouponRedemption, GiftTransfer, Loan, Referral


class CouponSerializer(serializers.ModelSerializer):
    class Meta:
        model = Coupon
        fields = [
            "id", "code", "discount_percent", "discount_amount", "minimum_order", "usage_limit",
            "used_count", "starts_at", "ends_at", "is_active", "assigned_to", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "used_count", "created_at", "updated_at"]


class CouponRedemptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = CouponRedemption
        fields = [
            "id", "coupon", "order", "user", "code_snapshot", "discount_amount", "currency", "created_at",
        ]
        read_only_fields = fields


class ReferralSerializer(serializers.ModelSerializer):
    class Meta:
        model = Referral
        fields = ["id", "inviter", "invitee", "code", "reward_amount", "reward_paid", "created_at", "updated_at"]
        read_only_fields = ["id", "inviter", "reward_paid", "created_at", "updated_at"]


class AddressSerializer(serializers.ModelSerializer):
    city_name = serializers.CharField(source="city.name", read_only=True)

    class Meta:
        model = Address
        fields = [
            "id", "user", "title", "city", "city_name", "district", "street", "building", "phone",
            "latitude", "longitude", "is_default", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "user", "city_name", "created_at", "updated_at"]


class LoanSerializer(serializers.ModelSerializer):
    class Meta:
        model = Loan
        fields = [
            "id", "user", "amount", "reason", "status", "approved_by", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "user", "status", "approved_by", "created_at", "updated_at"]


class GiftTransferSerializer(serializers.ModelSerializer):
    class Meta:
        model = GiftTransfer
        fields = [
            "id", "sender", "receiver", "amount", "points", "message", "status",
            "receiver_name_snapshot", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "sender", "receiver_name_snapshot", "status", "created_at", "updated_at"]
