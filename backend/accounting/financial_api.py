from decimal import Decimal, InvalidOperation

from django.contrib.auth import get_user_model
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle

from .services_v2 import wallet_summary
from .transfer_service import transfer_between_users

User = get_user_model()


class FinancialActionThrottle(ScopedRateThrottle):
    scope = "financial_action"


def _resolve_customer(value):
    value = str(value or "").strip()
    if not value:
        raise ValidationError({"recipient": "المستلم مطلوب."})
    user = User.objects.filter(phone=value, is_active=True).first() or User.objects.filter(username__iexact=value, is_active=True).first()
    if not user or getattr(user, "role", None) != "customer":
        raise ValidationError({"recipient": "العميل المستلم غير موجود."})
    return user


def _amount(value):
    try:
        amount = Decimal(str(value)).quantize(Decimal("0.01"))
    except (InvalidOperation, TypeError, ValueError):
        raise ValidationError({"amount": "المبلغ غير صالح."})
    if amount <= 0:
        raise ValidationError({"amount": "المبلغ يجب أن يكون أكبر من صفر."})
    return amount


def _key(request):
    return str(request.headers.get("Idempotency-Key") or request.data.get("idempotency_key") or "").strip() or None


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@throttle_classes([FinancialActionThrottle])
def transfer(request):
    if getattr(request.user, "role", None) != "customer":
        raise PermissionDenied("التحويل المالي مخصص للعملاء.")
    recipient = _resolve_customer(request.data.get("recipient"))
    amount = _amount(request.data.get("amount"))
    currency = str(request.data.get("currency", "YER")).upper()
    key = _key(request)
    try:
        entry = transfer_between_users(
            request.user,
            recipient,
            amount,
            currency,
            source_type="transfer",
            source_id=f"transfer:{key}" if key else "",
            note=str(request.data.get("note", "")).strip(),
            idempotency_key=key,
            created_by=request.user,
        )
    except ValueError as exc:
        raise ValidationError({"transfer": str(exc)})
    return Response({
        "success": True,
        "type": "transfer",
        "journal": entry.number,
        "amount": str(amount),
        "currency": currency,
        "recipient": {"id": recipient.id, "name": recipient.get_full_name() or recipient.phone or recipient.username},
        "balance": wallet_summary(request.user, currency)["customer"]["available"],
        "message": "تم تنفيذ التحويل وتسجيله في القيد المحاسبي.",
    }, status=201)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@throttle_classes([FinancialActionThrottle])
def gift(request):
    if getattr(request.user, "role", None) != "customer":
        raise PermissionDenied("إرسال الهدايا المالية مخصص للعملاء.")
    recipient = _resolve_customer(request.data.get("recipient"))
    amount = _amount(request.data.get("amount"))
    currency = str(request.data.get("currency", "YER")).upper()
    key = _key(request)
    message = str(request.data.get("message", "")).strip()
    try:
        entry = transfer_between_users(
            request.user,
            recipient,
            amount,
            currency,
            source_type="gift",
            source_id=f"gift:{key}" if key else "",
            note=message or "هدية مالية",
            idempotency_key=key,
            created_by=request.user,
        )
    except ValueError as exc:
        raise ValidationError({"gift": str(exc)})
    return Response({
        "success": True,
        "type": "gift",
        "journal": entry.number,
        "amount": str(amount),
        "currency": currency,
        "recipient": {"id": recipient.id, "name": recipient.get_full_name() or recipient.phone or recipient.username},
        "message": "تم إرسال الهدية وتسجيلها في القيد المحاسبي.",
        "balance": wallet_summary(request.user, currency)["customer"]["available"],
    }, status=201)
