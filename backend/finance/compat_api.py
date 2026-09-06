from decimal import Decimal, InvalidOperation

from django.db import transaction
from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from accounting.models import Wallet as AccountingWallet
from accounting.services_v2 import wallet_balance

from .models import Wallet, WalletTransaction
from .unified_wallet import adjust_user_wallet, sync_finance_projection


class AccountingBackedWalletSerializer(serializers.ModelSerializer):
    balance = serializers.SerializerMethodField()
    currency = serializers.CharField(read_only=True)

    class Meta:
        model = Wallet
        fields = ["id", "user", "balance", "currency", "is_locked", "created_at", "updated_at"]
        read_only_fields = fields

    def get_balance(self, obj):
        kind = (
            AccountingWallet.Kinds.VENDOR_AVAILABLE
            if getattr(obj.user, "role", None) == "vendor"
            else AccountingWallet.Kinds.CUSTOMER
        )
        accounting_wallet = __import__("accounting.services_v2", fromlist=["ensure_wallet"]).ensure_wallet(
            obj.user, kind, obj.currency
        )
        return str(wallet_balance(accounting_wallet).quantize(Decimal("0.01")))


class AccountingBackedWalletViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = AccountingBackedWalletSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self):
        user = self.request.user
        if user.is_staff or getattr(user, "role", None) == "admin":
            return Wallet.objects.all().select_related("user")
        return Wallet.objects.filter(user=user).select_related("user")

    def _projection(self, wallet):
        return sync_finance_projection(wallet.user, wallet.currency)

    def retrieve(self, request, *args, **kwargs):
        wallet = self.get_object()
        self._projection(wallet)
        wallet.refresh_from_db()
        return Response(self.get_serializer(wallet).data)

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        # The serializer computes the authoritative accounting balance, so the
        # response stays correct even if a compatibility projection was stale.
        return response

    @action(detail=True, methods=["post"])
    @transaction.atomic
    def admin_adjust(self, request, pk=None):
        if not (request.user.is_staff or getattr(request.user, "role", None) == "admin"):
            raise PermissionDenied("هذه العملية للمدير فقط")
        wallet = self.get_object()
        try:
            amount = Decimal(str(request.data.get("amount", "0"))).quantize(Decimal("0.01"))
        except (InvalidOperation, TypeError, ValueError):
            raise ValidationError({"amount": "المبلغ غير صالح"})
        if amount == 0:
            raise ValidationError({"amount": "أدخل مبلغًا غير صفري"})
        transaction_type = str(request.data.get("transaction_type", WalletTransaction.Types.ADJUSTMENT))
        if transaction_type not in {choice.value for choice in WalletTransaction.Types}:
            raise ValidationError({"transaction_type": "نوع العملية غير صالح"})
        reference = str(request.data.get("reference", "")).strip()
        note = str(request.data.get("note", "")).strip()
        _entry, projection, tx = adjust_user_wallet(
            wallet.user,
            amount,
            wallet.currency,
            reference=reference,
            note=note,
            transaction_type=transaction_type,
            created_by=request.user,
        )
        return Response(
            {"wallet": AccountingBackedWalletSerializer(projection).data, "transaction": tx.pk},
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"])
    @transaction.atomic
    def top_up_request(self, request, pk=None):
        wallet = self.get_object()
        if wallet.user_id != request.user.id and not (request.user.is_staff or getattr(request.user, "role", None) == "admin"):
            raise PermissionDenied("لا تملك هذه المحفظة")
        if wallet.is_locked:
            raise PermissionDenied("المحفظة مقفلة")
        try:
            amount = Decimal(str(request.data.get("amount", "0"))).quantize(Decimal("0.01"))
        except (InvalidOperation, TypeError, ValueError):
            raise ValidationError({"amount": "المبلغ غير صالح"})
        if amount <= 0:
            raise ValidationError({"amount": "أدخل مبلغًا موجبًا"})
        return Response(
            {"status": "pending", "amount": str(amount), "currency": wallet.currency, "message": "تم إنشاء طلب شحن الرصيد للمراجعة"},
            status=status.HTTP_202_ACCEPTED,
        )
