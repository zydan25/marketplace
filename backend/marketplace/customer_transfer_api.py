import re

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounting.services_v2 import wallet_summary
from .models import User


def _normalize_phone(value):
    digits = str(value or "").translate(str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "01234567890123456789"))
    digits = re.sub(r"\D", "", digits)
    if digits.startswith("00967"):
        digits = digits[5:]
    elif digits.startswith("967"):
        digits = digits[3:]
    if len(digits) > 9 and digits.startswith("0"):
        digits = digits[-9:]
    return digits


def _phone_variants(phone):
    local = _normalize_phone(phone)
    if not local:
        return []
    return [local, f"+967{local}", f"00967{local}", f"967{local}"]


class RecipientLookupAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        phone = _normalize_phone(request.data.get("receiver_phone", ""))
        if not phone:
            return Response({"detail": "رقم المستلم مطلوب."}, status=400)
        receiver = User.objects.filter(phone__in=_phone_variants(phone), is_active=True, role="customer").first()
        if receiver is None:
            return Response({"detail": "المشترك المستلم غير موجود."}, status=404)
        if receiver.pk == request.user.pk:
            return Response({"detail": "لا يمكنك التحويل إلى نفسك."}, status=400)
        summary = wallet_summary(request.user, "YER")
        return Response({
            "receiver_id": receiver.pk,
            "receiver_phone": receiver.phone,
            "receiver_name": receiver.get_full_name() or receiver.phone or receiver.username,
            "available_balance": str(summary["customer"]["available"]),
            "currency": "YER",
        })
