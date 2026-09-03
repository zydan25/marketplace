from decimal import Decimal
from django.utils import timezone
from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from marketplace.models import User

from .models import Address, Coupon, CouponRedemption, GiftTransfer, Loan, Referral


class AddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = Address
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at", "user")


class LoanSerializer(serializers.ModelSerializer):
    class Meta:
        model = Loan
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at", "user", "approved_by", "status")


class GiftTransferSerializer(serializers.ModelSerializer):
    class Meta:
        model = GiftTransfer
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at", "sender", "receiver_name_snapshot", "status")

    def validate(self, attrs):
        amount = attrs.get("amount", Decimal("0")) or Decimal("0")
        points = attrs.get("points", 0) or 0
        if amount < 0 or points < 0:
            raise serializers.ValidationError({"amount": "القيم لا يمكن أن تكون سالبة."})
        if amount == 0 and points == 0:
            raise serializers.ValidationError({"amount": "يجب تحديد مبلغ أو نقاط للتحويل."})
        return attrs


class CouponSerializer(serializers.ModelSerializer):
    class Meta:
        model = Coupon
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at", "used_count")

    def validate_code(self, value):
        return value.strip().upper()


class CouponRedemptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = CouponRedemption
        fields = "__all__"
        read_only_fields = ("id", "created_at", "user", "code_snapshot", "discount_amount")


class ReferralSerializer(serializers.ModelSerializer):
    class Meta:
        model = Referral
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at", "inviter", "code", "reward_paid")


class AddressViewSet(viewsets.ModelViewSet):
    serializer_class = AddressSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_staff or getattr(user, "role", None) == "admin":
            return Address.objects.select_related("user", "city")
        return Address.objects.filter(user=user).select_related("city")

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class LoanViewSet(viewsets.ModelViewSet):
    serializer_class = LoanSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self):
        user = self.request.user
        if user.is_staff or getattr(user, "role", None) == "admin":
            return Loan.objects.select_related("user", "approved_by")
        return Loan.objects.filter(user=user).select_related("approved_by")

    def perform_create(self, serializer):
        serializer.save(user=self.request.user, status=Loan.Status.PENDING, approved_by=None)

    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated])
    def approve(self, request, pk=None):
        if not (request.user.is_staff or getattr(request.user, "role", None) == "admin"):
            return Response({"detail": "اعتماد التمويل متاح للإدارة فقط."}, status=status.HTTP_403_FORBIDDEN)
        loan = self.get_object()
        loan.status = Loan.Status.APPROVED
        loan.approved_by = request.user
        loan.save(update_fields=["status", "approved_by", "updated_at"])
        return Response(self.get_serializer(loan).data)

    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated])
    def reject(self, request, pk=None):
        if not (request.user.is_staff or getattr(request.user, "role", None) == "admin"):
            return Response({"detail": "رفض التمويل متاح للإدارة فقط."}, status=status.HTTP_403_FORBIDDEN)
        loan = self.get_object()
        loan.status = Loan.Status.REJECTED
        loan.approved_by = request.user
        loan.save(update_fields=["status", "approved_by", "updated_at"])
        return Response(self.get_serializer(loan).data)


class GiftTransferViewSet(viewsets.ModelViewSet):
    serializer_class = GiftTransferSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self):
        user = self.request.user
        if user.is_staff or getattr(user, "role", None) == "admin":
            return GiftTransfer.objects.select_related("sender", "receiver")
        return GiftTransfer.objects.filter(sender=user).select_related("receiver")

    def perform_create(self, serializer):
        receiver_id = self.request.data.get("receiver")
        receiver = User.objects.filter(pk=receiver_id).first()
        if not receiver:
            raise serializers.ValidationError({"receiver": "المستلم غير موجود."})
        if receiver.pk == self.request.user.pk:
            raise serializers.ValidationError({"receiver": "لا يمكن التحويل إلى الحساب نفسه."})
        serializer.save(
            sender=self.request.user,
            receiver=receiver,
            receiver_name_snapshot=receiver.get_full_name() or receiver.phone or receiver.username,
            status=GiftTransfer.Status.PENDING,
        )


class CouponViewSet(viewsets.ModelViewSet):
    serializer_class = CouponSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_queryset(self):
        user = self.request.user
        qs = Coupon.objects.all().prefetch_related("assigned_to")
        if user.is_staff or getattr(user, "role", None) == "admin":
            return qs
        return (qs.filter(is_active=True, assigned_to__isnull=True) | qs.filter(is_active=True, assigned_to=user)).distinct()

    def create(self, request, *args, **kwargs):
        if not (request.user.is_staff or getattr(request.user, "role", None) == "admin"):
            return Response({"detail": "إنشاء الكوبونات متاح للإدارة فقط."}, status=status.HTTP_403_FORBIDDEN)
        return super().create(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        if not (request.user.is_staff or getattr(request.user, "role", None) == "admin"):
            return Response({"detail": "تعديل الكوبونات متاح للإدارة فقط."}, status=status.HTTP_403_FORBIDDEN)
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        if not (request.user.is_staff or getattr(request.user, "role", None) == "admin"):
            return Response({"detail": "حذف الكوبونات متاح للإدارة فقط."}, status=status.HTTP_403_FORBIDDEN)
        return super().destroy(request, *args, **kwargs)

    @action(detail=False, methods=["post"])
    def validate(self, request):
        code = str(request.data.get("code", "")).strip()
        now = timezone.now()
        coupon = self.get_queryset().filter(code__iexact=code, is_active=True).first()
        if not coupon or (coupon.starts_at and coupon.starts_at > now) or (coupon.ends_at and coupon.ends_at < now) or (coupon.usage_limit is not None and coupon.used_count >= coupon.usage_limit):
            return Response({"valid": False, "detail": "الكوبون غير صالح أو منتهي."}, status=status.HTTP_200_OK)
        return Response({"valid": True, "coupon": self.get_serializer(coupon).data})


class CouponRedemptionViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = CouponRedemptionSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "head", "options"]

    def get_queryset(self):
        user = self.request.user
        qs = CouponRedemption.objects.select_related("coupon", "order", "user")
        if user.is_staff or getattr(user, "role", None) == "admin":
            return qs
        return qs.filter(user=user)


class ReferralViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ReferralSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "head", "options"]

    def get_queryset(self):
        user = self.request.user
        if user.is_staff or getattr(user, "role", None) == "admin":
            return Referral.objects.select_related("inviter", "invitee")
        return Referral.objects.filter(inviter=user).select_related("invitee")


@api_view(["GET"])
@permission_classes([AllowAny])
def api_info(request):
    return Response({
        "domain": "promotions",
        "version": "2",
        "resources": ["coupons", "coupon-redemptions", "referrals", "addresses", "loans", "gifts"],
        "write_rules": {
            "loans": "create by owner; approval/rejection by admin actions",
            "gifts": "create-only pending records; settlement workflow remains explicit",
            "coupons": "admin-managed",
        },
    })
