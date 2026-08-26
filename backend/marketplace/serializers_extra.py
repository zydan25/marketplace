from rest_framework import serializers
from .models_extra import Address, Loan, GiftTransfer

class AddressSerializer(serializers.ModelSerializer):
    city_name = serializers.CharField(source="city.name", read_only=True)
    class Meta:
        model = Address
        fields = ["id", "title", "city", "city_name", "district", "street", "is_default", "phone"]
        read_only_fields = ["id", "city_name", "phone"]
        extra_kwargs = {"title": {"required": False, "allow_blank": True}, "district": {"required": False}, "street": {"required": False}}
    def validate(self, attrs):
        if not attrs.get("city"): raise serializers.ValidationError({"city": "اختر المدينة."})
        return attrs

    def create(self, validated_data):
        user = self.context["request"].user
        validated_data["phone"] = user.phone or ""
        validated_data["title"] = validated_data.get("title") or "العنوان"
        validated_data.pop("building", None)
        return Address.objects.create(user=user, **validated_data)

    def update(self, instance, validated_data):
        validated_data.pop("phone", None); validated_data.pop("title", None); validated_data.pop("building", None)
        return super().update(instance, validated_data)

class LoanSerializer(serializers.ModelSerializer):
    class Meta:
        model = Loan
        fields = "__all__"
        read_only_fields = ["user", "status", "approved_by"]

class GiftTransferSerializer(serializers.ModelSerializer):
    receiver_phone = serializers.CharField(write_only=True, required=False)
    receiver_name = serializers.CharField(source="receiver_name_snapshot", read_only=True)
    class Meta:
        model = GiftTransfer
        fields = ["id", "sender", "receiver", "receiver_phone", "receiver_name", "amount", "points", "message", "status", "created_at"]
        read_only_fields = ["id", "sender", "receiver", "receiver_name", "status", "created_at"]
