from rest_framework import serializers
from .models_extra import Address, Loan, GiftTransfer

class AddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = Address
        fields = "__all__"
        read_only_fields = ["user"]

class LoanSerializer(serializers.ModelSerializer):
    class Meta:
        model = Loan
        fields = "__all__"
        read_only_fields = ["user", "status", "approved_by"]

class GiftTransferSerializer(serializers.ModelSerializer):
    receiver_phone = serializers.CharField(write_only=True)
    
    class Meta:
        model = GiftTransfer
        fields = ["id", "sender", "receiver", "receiver_phone", "amount", "points", "message", "created_at"]
        read_only_fields = ["id", "sender", "receiver", "created_at"]
