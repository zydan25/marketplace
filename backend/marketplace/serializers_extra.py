from rest_framework import serializers
from .models_extra import Address, Loan, GiftTransfer

class AddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = Address
        fields = "__all__"
        read_only_fields = ["user", "title", "phone", "building"]

    def _defaults(self, attrs):
        user = self.context["request"].user
        attrs["title"] = attrs.get("title") or "عنوان التوصيل"
        attrs["phone"] = attrs.get("phone") or user.phone or ""
        attrs["building"] = attrs.get("building") or ""
        return attrs

    def create(self, validated_data):
        return Address.objects.create(user=self.context["request"].user, **self._defaults(validated_data))

    def update(self, instance, validated_data):
        return super().update(instance, self._defaults(validated_data))

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
