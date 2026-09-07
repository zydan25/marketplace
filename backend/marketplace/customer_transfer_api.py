from decimal import Decimal, InvalidOperation

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounting.services_v2 import wallet_summary
from .models import User


class RecipientLookupAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        phone = str(request.data.get("receiver_phone", "")).strip()
        if not phone:
            return Response({"detail": "رقم المستلم مطلوب."}, status=400)
        receiver = User.objects.filter(phone=phone, is_active=True, role="customer").first()
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
