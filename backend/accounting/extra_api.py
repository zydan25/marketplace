from decimal import Decimal, InvalidOperation

from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Account, JournalEntry, Wallet
from .services_v2 import account_balance, post_entry, statement_for_user, wallet_summary


def is_admin(user):
    return bool(user.is_staff or getattr(user, "role", None) == "admin")


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def account_report(request):
    currency = str(request.query_params.get("currency", "YER")).upper()
    summary = wallet_summary(request.user, currency)
    return Response({
        "currency": currency,
        "customer": summary["customer"],
        "vendor": summary["vendor"],
        "wallets": [
            {"id": wallet.id, "kind": wallet.kind, "label": wallet.get_kind_display(), "balance": str(account_balance(wallet.account)), "currency": wallet.currency, "account": wallet.account.code}
            for wallet in Wallet.objects.filter(owner=request.user, currency=currency).select_related("account")
        ],
        "statement": statement_for_user(request.user, currency),
    })


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def post_journal(request):
    if not is_admin(request.user):
        raise PermissionDenied("ترحيل القيود العامة للإدارة فقط.")
    rows = request.data.get("lines")
    if not isinstance(rows, list) or len(rows) < 2:
        raise ValidationError({"lines": "القيد يحتاج إلى سطرين على الأقل."})
    normalized = []
    for row in rows:
        if not isinstance(row, dict):
            raise ValidationError({"lines": "صيغة سطر القيد غير صالحة."})
        account = Account.objects.filter(pk=row.get("account_id"), is_active=True, is_group=False).first()
        if not account:
            raise ValidationError({"account_id": "الحساب غير موجود أو حساب رئيسي وغير قابل للترحيل."})
        try:
            debit = Decimal(str(row.get("debit", "0")))
            credit = Decimal(str(row.get("credit", "0")))
        except (InvalidOperation, TypeError, ValueError):
            raise ValidationError({"lines": "قيمة المدين أو الدائن غير صالحة."})
        normalized.append({"account": account, "debit": debit, "credit": credit, "description": str(row.get("description", "")).strip()})
    try:
        entry = post_entry(
            str(request.data.get("description", "قيد يدوي")).strip() or "قيد يدوي",
            normalized, source_type="manual_journal", source_id=str(request.data.get("reference", "")), created_by=request.user,
        )
    except ValueError as exc:
        raise ValidationError({"journal": str(exc)})
    return Response({"id": entry.id, "number": entry.number, "description": entry.description, "status": entry.status}, status=201)
