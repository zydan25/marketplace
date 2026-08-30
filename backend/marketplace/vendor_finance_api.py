from decimal import Decimal
import uuid

from django.db.models import Sum
from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .marketplace_models import VendorLedgerEntry
from .models import VendorPayout, VendorProfile, Wallet


class VendorPayoutSerializer(serializers.ModelSerializer):
    vendor_name = serializers.CharField(source="vendor.store_name", read_only=True)

    class Meta:
        model = VendorPayout
        fields = ["id", "vendor", "vendor_name", "vendor_order", "order", "amount", "currency", "status", "reference", "note", "created_at", "updated_at"]
        read_only_fields = ["id", "vendor", "vendor_name", "vendor_order", "order", "status", "reference", "created_at", "updated_at"]


class VendorFinanceViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = VendorPayoutSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        qs = VendorPayout.objects.select_related("vendor", "vendor_order", "order")
        if user.is_staff or user.role == "admin":
            return qs
        if user.role == "vendor":
            return qs.filter(vendor__owner=user)
        return qs.none()

    def _vendor_for_request(self):
        user = self.request.user
        if user.role == "vendor":
            vendor = VendorProfile.objects.filter(owner=user).first()
        else:
            vendor_id = self.request.query_params.get("vendor_id")
            vendor = VendorProfile.objects.filter(id=vendor_id).first() if vendor_id else None
        if not vendor:
            raise ValidationError({"vendor_id": "التاجر غير موجود"})
        return vendor

    @action(detail=False, methods=["get"])
    def summary(self, request):
        if request.user.role != "vendor" and not (request.user.is_staff or request.user.role == "admin"):
            raise PermissionDenied("المستحقات للتاجر فقط")
        vendor = self._vendor_for_request()
        ledger = VendorLedgerEntry.objects.filter(vendor=vendor)
        currency = ledger.order_by("-id").values_list("currency", flat=True).first() or "YER"
        earned = ledger.filter(entry_type=VendorLedgerEntry.Types.SALE).aggregate(v=Sum("amount"))["v"] or Decimal("0")
        paid_amount = VendorPayout.objects.filter(vendor=vendor, status="paid").aggregate(v=Sum("amount"))["v"] or Decimal("0")
        pending_amount = VendorPayout.objects.filter(vendor=vendor, status__in=["pending", "approved"]).aggregate(v=Sum("amount"))["v"] or Decimal("0")
        available = max(Decimal("0"), earned - paid_amount - pending_amount)
        wallet, _ = Wallet.objects.get_or_create(user=vendor.owner, defaults={"currency": currency})
        wallet_balance = wallet.balance if wallet.currency == currency else Decimal("0")
        return Response({
            "vendor": vendor.id,
            "vendor_name": vendor.store_name,
            "currency": currency,
            "earned": str(earned),
            "paid": str(paid_amount),
            "pending": str(pending_amount),
            "available": str(available),
            "wallet_balance": str(wallet_balance),
            "wallet_currency": wallet.currency,
            "payouts": VendorPayoutSerializer(VendorPayout.objects.filter(vendor=vendor).order_by("-created_at")[:20], many=True).data,
        })

    @action(detail=False, methods=["post"])
    def request_payout(self, request):
        if request.user.role != "vendor":
            raise PermissionDenied("طلب السحب متاح للتاجر فقط")
        vendor = VendorProfile.objects.filter(owner=request.user, status="active").first()
        if not vendor:
            raise ValidationError("لا يوجد متجر نشط")
        try:
            amount = Decimal(str(request.data.get("amount", "0")))
        except Exception:
            raise ValidationError({"amount": "المبلغ غير صالح"})
        if amount <= 0:
            raise ValidationError({"amount": "أدخل مبلغًا موجبًا"})
        ledger = VendorLedgerEntry.objects.filter(vendor=vendor)
        earned = ledger.filter(entry_type=VendorLedgerEntry.Types.SALE).aggregate(v=Sum("amount"))["v"] or Decimal("0")
        paid = VendorPayout.objects.filter(vendor=vendor, status="paid").aggregate(v=Sum("amount"))["v"] or Decimal("0")
        pending = VendorPayout.objects.filter(vendor=vendor, status__in=["pending", "approved"]).aggregate(v=Sum("amount"))["v"] or Decimal("0")
        available = max(Decimal("0"), earned - paid - pending)
        if amount > available:
            raise ValidationError({"amount": f"المتاح للسحب {available}"})
        payout = VendorPayout.objects.create(vendor=vendor, amount=amount, currency=ledger.order_by("-id").values_list("currency", flat=True).first() or "YER", status="pending", reference=f"PAYOUT-REQ-{uuid.uuid4().hex[:10].upper()}")
        return Response(VendorPayoutSerializer(payout).data, status=status.HTTP_201_CREATED)
