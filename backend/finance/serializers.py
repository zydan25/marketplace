from rest_framework import serializers

from catalog.models import City
from orders.models import Order, VendorOrder
from vendors.models import VendorProfile

from .models import CurrencyRate, VendorCityShipping, VendorLedgerEntry, VendorPayout, Wallet, WalletTransaction


class WalletSerializer(serializers.ModelSerializer):
    class Meta:
        model = Wallet
        fields = ["id", "user", "balance", "currency", "is_locked", "created_at", "updated_at"]
        read_only_fields = fields


class WalletTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = WalletTransaction
        fields = [
            "id", "wallet", "transaction_type", "amount", "balance_after", "reference", "note",
            "metadata", "created_at", "updated_at",
        ]
        read_only_fields = fields


class VendorLedgerEntrySerializer(serializers.ModelSerializer):
    vendor_name = serializers.CharField(source="vendor.store_name", read_only=True)
    vendor_order_number = serializers.CharField(source="vendor_order.order_number", read_only=True)

    class Meta:
        model = VendorLedgerEntry
        fields = [
            "id", "vendor", "vendor_name", "vendor_order", "vendor_order_number", "entry_type",
            "amount", "balance_after", "currency", "reference", "metadata", "created_at",
        ]
        read_only_fields = fields


class VendorPayoutSerializer(serializers.ModelSerializer):
    vendor_name = serializers.CharField(source="vendor.store_name", read_only=True)

    class Meta:
        model = VendorPayout
        fields = [
            "id", "vendor", "vendor_name", "vendor_order", "order", "amount", "currency",
            "status", "reference", "note", "created_at", "updated_at",
        ]
        read_only_fields = fields


class CurrencyRateSerializer(serializers.ModelSerializer):
    updated_by_name = serializers.CharField(source="updated_by.get_full_name", read_only=True)

    class Meta:
        model = CurrencyRate
        fields = [
            "id", "base_currency", "target_currency", "rate", "is_active", "updated_by",
            "updated_by_name", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "updated_by", "updated_by_name", "created_at", "updated_at"]


class VendorCityShippingSerializer(serializers.ModelSerializer):
    vendor_name = serializers.CharField(source="vendor.store_name", read_only=True)
    city_name = serializers.CharField(source="city.name", read_only=True)

    class Meta:
        model = VendorCityShipping
        fields = [
            "id", "vendor", "vendor_name", "city", "city_name", "fee", "is_active",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "vendor_name", "city_name", "created_at", "updated_at"]
