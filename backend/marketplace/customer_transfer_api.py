from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounting.services_v2 import wallet_summary
from .models import User
from .phone_utils import normalize_yemen_phone


def _phone_variants(phone):
    local = normalize_yemen_phone(phone)
    if not local:
        return []
    return [local, f"+967{local}", f"00967{local}", f"967{local}"]


class RecipientLookupAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        phone = normalize_yemen_phone(request.data.get("receiver_phone", ""))
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
