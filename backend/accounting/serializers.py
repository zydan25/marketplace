from rest_framework import serializers

from .models import Account, JournalEntry, JournalLine, Voucher, Wallet, WithdrawalRequest


class AccountSerializer(serializers.ModelSerializer):
    balance = serializers.SerializerMethodField()
    parent_name = serializers.CharField(source="parent.name", read_only=True, allow_null=True)

    class Meta:
        model = Account
        fields = ["id", "code", "name", "parent", "parent_name", "account_type", "normal_side", "is_group", "is_active", "balance", "party_type", "party_user", "metadata"]
        read_only_fields = ["code", "balance"]

    def get_balance(self, obj):
        if obj.is_group:
            from .services_v2 import account_balance
            return str(account_balance(obj))
        from .services_v2 import account_balance
        return str(account_balance(obj))


class WalletSerializer(serializers.ModelSerializer):
    balance = serializers.SerializerMethodField()
    kind_label = serializers.CharField(source="get_kind_display", read_only=True)
    account_code = serializers.CharField(source="account.code", read_only=True)

    class Meta:
        model = Wallet
        fields = ["id", "owner", "kind", "kind_label", "currency", "account", "account_code", "is_active", "balance"]
        read_only_fields = fields

    def get_balance(self, obj):
        from .services_v2 import wallet_balance
        return str(wallet_balance(obj))


class JournalLineSerializer(serializers.ModelSerializer):
    code = serializers.CharField(source="account.code", read_only=True)
    account_name = serializers.CharField(source="account.name", read_only=True)

    class Meta:
        model = JournalLine
        fields = ["id", "account", "code", "account_name", "description", "debit", "credit"]


class JournalEntrySerializer(serializers.ModelSerializer):
    lines = JournalLineSerializer(many=True, read_only=True)

    class Meta:
        model = JournalEntry
        fields = ["id", "number", "entry_date", "description", "status", "source_type", "source_id", "idempotency_key", "created_by", "metadata", "created_at", "lines"]
        read_only_fields = fields


class VoucherSerializer(serializers.ModelSerializer):
    voucher_type_label = serializers.CharField(source="get_voucher_type_display", read_only=True)
    journal_number = serializers.CharField(source="journal_entry.number", read_only=True)

    class Meta:
        model = Voucher
        fields = ["id", "number", "voucher_type", "voucher_type_label", "voucher_date", "amount", "currency", "cash_account", "party_account", "journal_entry", "journal_number", "description", "source_type", "source_id", "created_by", "created_at"]
        read_only_fields = fields


class WithdrawalRequestSerializer(serializers.ModelSerializer):
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    requester_name = serializers.SerializerMethodField()
    hold_journal_number = serializers.CharField(source="hold_journal.number", read_only=True, allow_null=True)
    settlement_journal_number = serializers.CharField(source="settlement_journal.number", read_only=True, allow_null=True)

    class Meta:
        model = WithdrawalRequest
        fields = ["id", "number", "requester", "requester_name", "amount", "currency", "status", "status_label", "note", "source_type", "source_id", "hold_journal", "hold_journal_number", "settlement_journal", "settlement_journal_number", "created_at", "updated_at"]
        read_only_fields = fields

    def get_requester_name(self, obj):
        return obj.requester.get_full_name() or getattr(obj.requester, "phone", "") or getattr(obj.requester, "username", "")
