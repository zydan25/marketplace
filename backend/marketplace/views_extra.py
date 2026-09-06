from decimal import Decimal, InvalidOperation

from django.db import transaction
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from accounting.services_v2 import wallet_summary
from accounting.transfer_service import transfer_between_users
from .models import User
from .models_extra import Address, Loan, GiftTransfer
from .serializers_extra import AddressSerializer, LoanSerializer, GiftTransferSerializer


class AddressViewSet(viewsets.ModelViewSet):
    serializer_class = AddressSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Address.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class LoanViewSet(viewsets.ModelViewSet):
    serializer_class = LoanSerializer

    def get_permissions(self):
        from .permissions import IsAdminRole
        return [IsAdminRole()]

    def get_queryset(self):
        return Loan.objects.all()

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class GiftTransferViewSet(viewsets.ModelViewSet):
    serializer_class = GiftTransferSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self):
        return GiftTransfer.objects.filter(sender=self.request.user) | GiftTransfer.objects.filter(receiver=self.request.user)

    def create(self, request, *args, **kwargs):
        receiver_phone = str(request.data.get("receiver_phone", "")).strip()
        try:
            amount = Decimal(str(request.data.get("amount", "0"))).quantize(Decimal("0.01"))
        except (ValueError, TypeError, InvalidOperation):
            return Response({"detail": "المبلغ غير صالح"}, status=status.HTTP_400_BAD_REQUEST)
        if amount <= 0:
            return Response({"detail": "المبلغ يجب أن يكون أكبر من صفر"}, status=status.HTTP_400_BAD_REQUEST)

        receiver = User.objects.filter(phone=receiver_phone, is_active=True).first()
        if not receiver:
            return Response({"detail": "العميل المستلم غير موجود؛ لم يتم إنشاء طلب التحويل."}, status=status.HTTP_404_NOT_FOUND)
        if receiver.pk == request.user.pk:
            return Response({"detail": "لا يمكنك تحويل رصيد لنفسك"}, status=status.HTTP_400_BAD_REQUEST)

        summary = wallet_summary(request.user, "YER")
        if Decimal(summary["customer"]["available"]) < amount:
            return Response({"detail": "الرصيد المحاسبي غير كافٍ"}, status=status.HTTP_400_BAD_REQUEST)

        receiver_name = receiver.get_full_name() or receiver.phone or receiver.username
        gift = GiftTransfer.objects.create(
            sender=request.user,
            receiver=receiver,
            amount=amount,
            message=str(request.data.get("message", ""))[:2000],
            status=GiftTransfer.Status.PENDING,
            receiver_name_snapshot=receiver_name,
        )
        return Response({
            "id": gift.id,
            "receiver_name": receiver_name,
            "amount": str(amount),
            "status": gift.status,
            "currency": "YER",
            "message": "يرجى تأكيد عملية التحويل",
        }, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    @transaction.atomic
    def cancel(self, request, pk=None):
        gift = GiftTransfer.objects.select_for_update().filter(pk=pk).first()
        if not gift:
            raise ValidationError({"gift": "العملية غير موجودة."})
        if gift.sender_id != request.user.id:
            raise PermissionDenied("لا تملك صلاحية إلغاء هذه العملية")
        if gift.status != GiftTransfer.Status.PENDING:
            raise ValidationError({"gift": "هذه العملية ليست معلقة"})
        gift.status = GiftTransfer.Status.CANCELLED
        gift.save(update_fields=["status", "updated_at"])
        return Response(GiftTransferSerializer(gift).data)

    @action(detail=True, methods=["post"])
    @transaction.atomic
    def confirm(self, request, pk=None):
        gift = GiftTransfer.objects.select_for_update().filter(pk=pk).first()
        if not gift:
            raise ValidationError({"gift": "العملية غير موجودة."})
        if gift.sender_id != request.user.id:
            raise PermissionDenied("لا تملك صلاحية تأكيد هذه العملية")
        if gift.status != GiftTransfer.Status.PENDING:
            raise ValidationError({"gift": "هذه العملية ليست في حالة انتظار التأكيد"})

        key = f"legacy-gift:{gift.pk}"
        try:
            entry = transfer_between_users(
                request.user,
                gift.receiver,
                gift.amount,
                "YER",
                source_type="gift",
                source_id=f"gift:{gift.pk}",
                note=gift.message or "إرسال هدية",
                idempotency_key=key,
                created_by=request.user,
            )
        except ValueError as exc:
            raise ValidationError({"gift": str(exc)})

        gift.status = GiftTransfer.Status.COMPLETED
        gift.save(update_fields=["status", "updated_at"])
        return Response({
            **GiftTransferSerializer(gift).data,
            "journal": entry.number,
            "balance": wallet_summary(request.user, "YER")["customer"]["available"],
        })
