from decimal import Decimal, InvalidOperation

from django.db import transaction
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import User, Wallet, WalletTransaction
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
        if self.request.user.role == "admin" or self.request.user.is_staff:
            return Loan.objects.all()
        return Loan.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class GiftTransferViewSet(viewsets.ModelViewSet):
    serializer_class = GiftTransferSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return GiftTransfer.objects.filter(sender=self.request.user) | GiftTransfer.objects.filter(receiver=self.request.user)

    def create(self, request, *args, **kwargs):
        receiver_phone = request.data.get("receiver_phone")
        amount = request.data.get("amount", 0)

        try:
            amount = Decimal(str(amount))
        except (ValueError, TypeError, InvalidOperation):
            return Response({"detail": "المبلغ غير صالح"}, status=status.HTTP_400_BAD_REQUEST)

        if amount <= 0:
            return Response({"detail": "المبلغ يجب أن يكون أكبر من صفر"}, status=status.HTTP_400_BAD_REQUEST)

        receiver = User.objects.filter(phone=receiver_phone).first()
        if not receiver:
            return Response({"detail": "رقم الهاتف المستلم غير مسجل"}, status=status.HTTP_404_NOT_FOUND)

        if receiver == request.user:
            return Response({"detail": "لا يمكنك تحويل رصيد لنفسك"}, status=status.HTTP_400_BAD_REQUEST)

        wallet = Wallet.objects.get(user=request.user)
        if wallet.balance < amount:
            return Response({"detail": "الرصيد غير كافٍ"}, status=status.HTTP_400_BAD_REQUEST)

        receiver_name = f"{receiver.first_name} {receiver.last_name}".strip() or receiver.phone

        gift = GiftTransfer.objects.create(
            sender=request.user,
            receiver=receiver,
            amount=amount,
            message=request.data.get("message", ""),
            status=GiftTransfer.Status.PENDING,
            receiver_name_snapshot=receiver_name
        )

        return Response({
            "id": gift.id,
            "receiver_name": receiver_name,
            "amount": str(amount),
            "status": gift.status,
            "message": "يرجى تأكيد عملية التحويل"
        }, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        gift = self.get_object()
        if gift.sender != request.user:
            return Response({"detail": "لا تملك صلاحية إلغاء هذه العملية"}, status=status.HTTP_403_FORBIDDEN)
        if gift.status != GiftTransfer.Status.PENDING:
            return Response({"detail": "هذه العملية ليست معلقة"}, status=status.HTTP_400_BAD_REQUEST)
        gift.status = GiftTransfer.Status.CANCELLED
        gift.save(update_fields=["status", "updated_at"])
        return Response(GiftTransferSerializer(gift).data)

    @action(detail=True, methods=["post"])
    @transaction.atomic
    def confirm(self, request, pk=None):
        gift = self.get_object()
        if gift.sender != request.user:
            return Response({"detail": "لا تملك صلاحية تأكيد هذه العملية"}, status=status.HTTP_403_FORBIDDEN)

        if gift.status != GiftTransfer.Status.PENDING:
            return Response({"detail": "هذه العملية ليست في حالة انتظار التأكيد"}, status=status.HTTP_400_BAD_REQUEST)

        sender_wallet = Wallet.objects.select_for_update().get(user=request.user)
        if sender_wallet.balance < gift.amount:
            gift.status = GiftTransfer.Status.CANCELLED
            gift.save()
            return Response({"detail": "الرصيد غير كافٍ لإتمام العملية"}, status=status.HTTP_400_BAD_REQUEST)

        receiver_wallet = Wallet.objects.select_for_update().get(user=gift.receiver)

        sender_wallet.balance -= gift.amount
        sender_wallet.save()

        receiver_wallet.balance += gift.amount
        receiver_wallet.save()

        WalletTransaction.objects.create(wallet=sender_wallet, transaction_type="payment", amount=-gift.amount, balance_after=sender_wallet.balance, note=f"تحويل إلى {gift.receiver.phone}")
        WalletTransaction.objects.create(wallet=receiver_wallet, transaction_type="reward", amount=gift.amount, balance_after=receiver_wallet.balance, note=f"هدية من {request.user.phone}")

        gift.status = GiftTransfer.Status.COMPLETED
        gift.save()

        return Response(GiftTransferSerializer(gift).data)
