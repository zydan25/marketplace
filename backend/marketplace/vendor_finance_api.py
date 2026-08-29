from decimal import Decimal
import uuid

from django.db import transaction
from django.db.models import Sum
from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .marketplace_models import VendorLedgerEntry
from .models import VendorPayout, VendorProfile, Wallet, WalletTransaction


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

    def _summary_for_vendor(self, vendor):
        ledger = VendorLedgerEntry.objects.filter(vendor=vendor)
        earned = ledger.filter(entry_type=VendorLedgerEntry.Types.SALE).aggregate(v=Sum("amount"))["v"] or Decimal("0")
        paid_amount = VendorPayout.objects.filter(vendor=vendor, status="paid", vendor_order__isnull=True, order__isnull=True).aggregate(v=Sum("amount"))["v"] or Decimal("0")
        pending_amount = VendorPayout.objects.filter(vendor=vendor, status__in=["pending", "approved"], vendor_order__isnull=True, order__isnull=True).aggregate(v=Sum("amount"))["v"] or Decimal("0")
        wallet, _ = Wallet.objects.get_or_create(user=vendor.owner, defaults={"currency": ledger.order_by("-id").values_list("currency", flat=True).first() or "YER"})
        available = max(Decimal("0"), Decimal(wallet.balance) - pending_amount)
        return {
            "vendor": vendor.id,
            "vendor_name": vendor.store_name,
            "currency": wallet.currency,
            "wallet_balance": str(wallet.balance),
            "earned": str(earned),
            "paid": str(paid_amount),
            "pending": str(pending_amount),
            "available": str(available),
            "payouts": VendorPayoutSerializer(VendorPayout.objects.filter(vendor=vendor).order_by("-created_at")[:30], many=True).data,
        }

    @action(detail=False, methods=["get"])
    def summary(self, request):
        if request.user.role != "vendor" and not (request.user.is_staff or request.user.role == "admin"):
            raise PermissionDenied("المستحقات للتاجر فقط")
        return Response(self._summary_for_vendor(self._vendor_for_request()))

    @action(detail=False, methods=["post"])
    @transaction.atomic
    def request_payout(self, request):
        if request.user.role != "vendor":
            raise PermissionDenied("طلب السحب متاح للتاجر فقط")
        vendor = VendorProfile.objects.select_for_update().filter(owner=request.user, status="active").first()
        if not vendor:
            raise ValidationError("لا يوجد متجر نشط")
        try:
            amount = Decimal(str(request.data.get("amount", "0")))
        except Exception:
            raise ValidationError({"amount": "المبلغ غير صالح"})
        if amount <= 0:
            raise ValidationError({"amount": "أدخل مبلغًا موجبًا"})
        wallet, _ = Wallet.objects.select_for_update().get_or_create(user=request.user, defaults={"currency": "YER"})
        if wallet.is_locked:
            raise PermissionDenied("المحفظة مقفلة")
        if wallet.currency != "YER":
            currency = wallet.currency
        else:
            currency = wallet.currency
        pending = VendorPayout.objects.select_for_update().filter(vendor=vendor, status__in=["pending", "approved"], vendor_order__isnull=True, order__isnull=True).aggregate(v=Sum("amount"))["v"] or Decimal("0")
        available = max(Decimal("0"), wallet.balance - pending)
        if amount > available:
            raise ValidationError({"amount": f"المتاح للسحب {available} {currency}"})
        payout = VendorPayout.objects.create(vendor=vendor, amount=amount, currency=currency, status="pending", reference=f"PAYOUT-REQ-{uuid.uuid4().hex[:10].upper()}")
        return Response(VendorPayoutSerializer(payout).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    @transaction.atomic
    def admin_approve(self, request, pk=None):
        if not (request.user.is_staff or request.user.role == "admin"):
            raise PermissionDenied("اعتماد طلب السحب للإدارة فقط")
        payout = self.get_object()
        if payout.vendor_order_id or payout.order_id:
            raise ValidationError({"payout": "هذه العملية المالية مرتبطة بتحرير طلب وليست طلب سحب يدوي."})
        if payout.status != "pending":
            raise ValidationError({"payout": "طلب السحب ليس معلقًا."})
        payout.status = "approved"
        payout.note = (request.data.get("note") or payout.note or "").strip()
        payout.save(update_fields=["status", "note", "updated_at"])
        return Response(VendorPayoutSerializer(payout).data)

    @action(detail=True, methods=["post"])
    @transaction.atomic
    def admin_pay(self, request, pk=None):
        if not (request.user.is_staff or request.user.role == "admin"):
            raise PermissionDenied("صرف طلب السحب للإدارة فقط")
        payout = VendorPayout.objects.select_for_update().select_related("vendor", "vendor__owner").filter(pk=pk).first()
        if not payout:
            raise ValidationError({"payout": "طلب السحب غير موجود."})
        if payout.vendor_order_id or payout.order_id:
            raise ValidationError({"payout": "لا يمكن صرف تحرير الطلب من شاشة السحب اليدوي."})
        if payout.status not in {"pending", "approved"}:
            raise ValidationError({"payout": "لا يمكن صرف هذا الطلب بالحالة الحالية."})
        wallet = Wallet.objects.select_for_update().filter(user=payout.vendor.owner).first()
        if not wallet:
            raise ValidationError({"wallet": "محفظة التاجر غير موجودة."})
        if wallet.is_locked or wallet.currency != payout.currency:
            raise ValidationError({"wallet": "محفظة التاجر مقفلة أو عملتها لا تطابق طلب السحب."})
        amount = Decimal(payout.amount)
        if wallet.balance < amount:
            raise ValidationError({"wallet": f"رصيد المحفظة غير كافٍ: {wallet.balance} {wallet.currency}."})
        wallet.balance -= amount
        wallet.save(update_fields=["balance", "updated_at"])
        WalletTransaction.objects.create(
            wallet=wallet,
            transaction_type=WalletTransaction.Types.WITHDRAWAL,
            amount=-amount,
            balance_after=wallet.balance,
            reference=payout.reference or f"PAYOUT-{payout.id}",
            note=(request.data.get("note") or f"صرف طلب سحب التاجر {payout.vendor.store_name}").strip(),
            metadata={"vendor_payout_id": payout.id, "processed_by": request.user.id},
        )
        payout.status = "paid"
        payout.note = (request.data.get("note") or payout.note or "").strip()
        payout.save(update_fields=["status", "note", "updated_at"])
        return Response({"payout": VendorPayoutSerializer(payout).data, "wallet_balance": str(wallet.balance), "currency": wallet.currency})

    @action(detail=True, methods=["post"])
    @transaction.atomic
    def admin_reject(self, request, pk=None):
        if not (request.user.is_staff or request.user.role == "admin"):
            raise PermissionDenied("رفض طلب السحب للإدارة فقط")
        payout = self.get_object()
        if payout.vendor_order_id or payout.order_id:
            raise ValidationError({"payout": "هذه العملية مرتبطة بتحرير طلب وليست طلب سحب يدوي."})
        if payout.status not in {"pending", "approved"}:
            raise ValidationError({"payout": "لا يمكن رفض الطلب بالحالة الحالية."})
        payout.status = "rejected"
        payout.note = (request.data.get("note") or "مرفوض من الإدارة").strip()
        payout.save(update_fields=["status", "note", "updated_at"])
        return Response(VendorPayoutSerializer(payout).data)
