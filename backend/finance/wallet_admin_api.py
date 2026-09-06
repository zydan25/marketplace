from decimal import Decimal, InvalidOperation

from django.shortcuts import get_object_or_404
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.status import HTTP_201_CREATED
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from accounting.models import Wallet as AccountingWallet
from accounting.services_v2 import wallet_balance

from .models import Wallet, WalletTransaction
from .unified_wallet import adjust_user_wallet


class FinancialActionThrottle(ScopedRateThrottle):
    scope = "financial_action"


class AdminWalletAdjustAPIView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [FinancialActionThrottle]

    def post(self, request, pk):
        if not (request.user.is_staff or getattr(request.user, "role", None) == "admin"):
            raise PermissionDenied("هذه العملية للمدير فقط")
        wallet = get_object_or_404(Wallet, pk=pk)
        try:
            amount = Decimal(str(request.data.get("amount", "0"))).quantize(Decimal("0.01"))
        except (InvalidOperation, TypeError, ValueError):
            raise ValidationError({"amount": "المبلغ غير صالح"})
        if amount == 0:
            raise ValidationError({"amount": "أدخل مبلغًا غير صفري"})
        transaction_type = str(request.data.get("transaction_type", WalletTransaction.Types.ADJUSTMENT))
        if transaction_type not in {choice.value for choice in WalletTransaction.Types}:
            raise ValidationError({"transaction_type": "نوع العملية غير صالح"})
        request_key = str(request.headers.get("Idempotency-Key") or "").strip()
        if not request_key:
            raise ValidationError({"idempotency_key": "Idempotency-Key مطلوب لكل تسوية مالية."})
        reference = str(request.data.get("reference") or "").strip() or f"admin-adjust:{request_key}"
        note = str(request.data.get("note") or "").strip()
        entry, projection, tx = adjust_user_wallet(
            wallet.user,
            amount,
            wallet.currency,
            reference=reference,
            note=note,
            transaction_type=transaction_type,
            created_by=request.user,
            idempotency_key=f"admin-wallet-adjust:{request_key}",
        )
        accounting_wallet = __import__("accounting.services_v2", fromlist=["ensure_wallet"]).ensure_wallet(
            wallet.user,
            AccountingWallet.Kinds.VENDOR_AVAILABLE if getattr(wallet.user, "role", None) == "vendor" else AccountingWallet.Kinds.CUSTOMER,
            wallet.currency,
        )
        return Response({
            "journal": entry.number,
            "transaction_id": tx.pk,
            "wallet_id": projection.pk,
            "balance": str(wallet_balance(accounting_wallet).quantize(Decimal("0.01"))),
            "currency": projection.currency,
        }, status=HTTP_201_CREATED)
