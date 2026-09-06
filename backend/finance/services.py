from decimal import Decimal, InvalidOperation
import uuid

from django.db import transaction
from django.db.models import Sum
from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from accounting.models import JournalEntry, Wallet as AccountingWallet
from accounting.services_v2 import hold_withdrawal, reject_withdrawal, settle_withdrawal, wallet_balance
from vendors.models import VendorProfile

from .models import VendorLedgerEntry, VendorPayout, Wallet
from .unified_wallet import sync_finance_projection


class WalletDomainSerializer(serializers.ModelSerializer):
    class Meta:
        model = Wallet
        fields = "__all__"
        read_only_fields = tuple(field.name for field in Wallet._meta.fields)


class VendorPayoutDomainSerializer(serializers.ModelSerializer):
    vendor_name = serializers.CharField(source="vendor.store_name", read_only=True)

    class Meta:
        model = VendorPayout
        fields = [
            "id", "vendor", "vendor_name", "vendor_order", "order", "amount",
            "currency", "status", "reference", "note", "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "vendor", "vendor_name", "vendor_order", "order", "status",
            "reference", "created_at", "updated_at",
        ]


class WalletViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = WalletDomainSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "head", "options"]

    def get_queryset(self):
        user = self.request.user
        if user.is_staff or getattr(user, "role", None) == "admin":
            return Wallet.objects.all().select_related("user").prefetch_related("transactions")
        return Wallet.objects.filter(user=user).prefetch_related("transactions")


class VendorFinanceViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = VendorPayoutDomainSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "head", "options"]

    def get_queryset(self):
        user = self.request.user
        qs = VendorPayout.objects.select_related("vendor", "vendor_order", "order")
        if user.is_staff or getattr(user, "role", None) == "admin":
            return qs
        if getattr(user, "role", None) == "vendor":
            return qs.filter(vendor__owner=user)
        return qs.none()

    def _vendor_for_request(self):
        user = self.request.user
        if getattr(user, "role", None) == "vendor":
            vendor = VendorProfile.objects.filter(owner=user, status="active").first()
        else:
            vendor_id = self.request.query_params.get("vendor_id")
            vendor = VendorProfile.objects.filter(id=vendor_id, status="active").first() if vendor_id else None
        if not vendor:
            raise ValidationError({"vendor_id": "التاجر غير موجود أو غير نشط"})
        return vendor

    def _summary_for_vendor(self, vendor):
        accounting_available = __import__("accounting.services_v2", fromlist=["ensure_wallet"]).ensure_wallet(
            vendor.owner, AccountingWallet.Kinds.VENDOR_AVAILABLE, "YER"
        )
        pending_wallet = __import__("accounting.services_v2", fromlist=["ensure_wallet"]).ensure_wallet(
            vendor.owner, AccountingWallet.Kinds.VENDOR_PENDING, "YER"
        )
        hold_wallet = __import__("accounting.services_v2", fromlist=["ensure_wallet"]).ensure_wallet(
            vendor.owner, AccountingWallet.Kinds.WITHDRAWAL_HOLD, "YER"
        )
        available = wallet_balance(accounting_available)
        pending_provider = wallet_balance(pending_wallet)
        withdrawal_hold = wallet_balance(hold_wallet)
        ledger = VendorLedgerEntry.objects.filter(vendor=vendor)
        earned = ledger.filter(entry_type=VendorLedgerEntry.Types.SALE).aggregate(v=Sum("amount"))["v"] or Decimal("0")
        paid_amount = VendorPayout.objects.filter(vendor=vendor, status="paid", vendor_order__isnull=True, order__isnull=True).aggregate(v=Sum("amount"))["v"] or Decimal("0")
        return {
            "vendor": vendor.id,
            "vendor_name": vendor.store_name,
            "currency": "YER",
            "wallet_balance": str(available.quantize(Decimal("0.01"))),
            "earned": str(earned),
            "paid": str(paid_amount),
            "pending": str(withdrawal_hold.quantize(Decimal("0.01"))),
            "available": str(max(Decimal("0.00"), available).quantize(Decimal("0.01"))),
            "provider_pending": str(pending_provider.quantize(Decimal("0.01"))),
            "withdrawal_hold": str(withdrawal_hold.quantize(Decimal("0.01"))),
            "payouts": VendorPayoutDomainSerializer(
                VendorPayout.objects.filter(vendor=vendor).order_by("-created_at")[:30], many=True
            ).data,
        }

    @action(detail=False, methods=["get"])
    def summary(self, request):
        if getattr(request.user, "role", None) not in {"vendor", "admin"} and not request.user.is_staff:
            raise PermissionDenied("المستحقات للتاجر فقط")
        return Response(self._summary_for_vendor(self._vendor_for_request()))

    @action(detail=False, methods=["post"])
    @transaction.atomic
    def request_payout(self, request):
        if getattr(request.user, "role", None) != "vendor":
            raise PermissionDenied("طلب السحب متاح للتاجر فقط")
        vendor = VendorProfile.objects.select_for_update().filter(owner=request.user, status="active").first()
        if not vendor:
            raise ValidationError({"vendor_id": "لا يوجد متجر نشط"})
        try:
            amount = Decimal(str(request.data.get("amount", "0"))).quantize(Decimal("0.01"))
        except (InvalidOperation, TypeError, ValueError):
            raise ValidationError({"amount": "المبلغ غير صالح"})
        if amount <= 0:
            raise ValidationError({"amount": "المبلغ يجب أن يكون موجبًا"})

        currency = str(request.data.get("currency", "YER")).upper()
        payout = VendorPayout.objects.create(
            vendor=vendor,
            amount=amount,
            currency=currency,
            status="pending",
            reference=f"PAYOUT-REQ-{uuid.uuid4().hex[:10].upper()}",
        )
        try:
            hold_withdrawal(request.user, amount, currency, withdrawal_id=payout.pk, created_by=request.user)
        except ValueError as exc:
            raise ValidationError({"amount": str(exc)})
        sync_finance_projection(request.user, currency)
        return Response(VendorPayoutDomainSerializer(payout).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    @transaction.atomic
    def admin_approve(self, request, pk=None):
        if not (request.user.is_staff or getattr(request.user, "role", None) == "admin"):
            raise PermissionDenied("اعتماد طلب السحب للإدارة فقط")
        payout = self.get_object()
        if payout.vendor_order_id or payout.order_id:
            raise ValidationError({"payout": "هذه العملية مرتبطة بتحرير طلب وليست طلب سحب يدوي."})
        if payout.status != "pending":
            raise ValidationError({"payout": "طلب السحب ليس معلقًا."})
        payout.status = "approved"
        payout.note = str(request.data.get("note") or payout.note or "").strip()
        payout.save(update_fields=["status", "note", "updated_at"])
        return Response(VendorPayoutDomainSerializer(payout).data)

    @action(detail=True, methods=["post"])
    @transaction.atomic
    def admin_pay(self, request, pk=None):
        if not (request.user.is_staff or getattr(request.user, "role", None) == "admin"):
            raise PermissionDenied("صرف طلب السحب للإدارة فقط")
        payout = VendorPayout.objects.select_for_update().select_related("vendor", "vendor__owner").filter(pk=pk).first()
        if not payout:
            raise ValidationError({"payout": "طلب السحب غير موجود."})
        if payout.vendor_order_id or payout.order_id:
            raise ValidationError({"payout": "لا يمكن صرف تحرير الطلب من شاشة السحب اليدوي."})
        if payout.status not in {"pending", "approved"}:
            raise ValidationError({"payout": "لا يمكن صرف هذا الطلب بالحالة الحالية."})

        amount = Decimal(payout.amount)
        user = payout.vendor.owner
        hold_key = f"withdrawal:hold:{payout.pk}"
        if not JournalEntry.objects.filter(idempotency_key=hold_key).exists():
            try:
                hold_withdrawal(user, amount, payout.currency, withdrawal_id=payout.pk, created_by=request.user)
            except ValueError as exc:
                raise ValidationError({"wallet": str(exc)})
        try:
            settle_withdrawal(user, amount, payout.currency, withdrawal_id=payout.pk, created_by=request.user)
        except ValueError as exc:
            raise ValidationError({"wallet": str(exc)})
        sync_finance_projection(user, payout.currency)
        payout.status = "paid"
        payout.note = str(request.data.get("note") or payout.note or "").strip()
        payout.save(update_fields=["status", "note", "updated_at"])
        return Response({"payout": VendorPayoutDomainSerializer(payout).data, "wallet_balance": self._summary_for_vendor(payout.vendor)["available"], "currency": payout.currency})

    @action(detail=True, methods=["post"])
    @transaction.atomic
    def admin_reject(self, request, pk=None):
        if not (request.user.is_staff or getattr(request.user, "role", None) == "admin"):
            raise PermissionDenied("رفض طلب السحب للإدارة فقط")
        payout = self.get_object()
        if payout.vendor_order_id or payout.order_id:
            raise ValidationError({"payout": "هذه العملية مرتبطة بتحرير طلب وليست طلب سحب يدوي."})
        if payout.status not in {"pending", "approved"}:
            raise ValidationError({"payout": "لا يمكن رفض الطلب بالحالة الحالية."})

        hold_key = f"withdrawal:hold:{payout.pk}"
        if JournalEntry.objects.filter(idempotency_key=hold_key).exists():
            reject_withdrawal(
                payout.vendor.owner,
                Decimal(payout.amount),
                payout.currency,
                withdrawal_id=payout.pk,
                created_by=request.user,
            )
            sync_finance_projection(payout.vendor.owner, payout.currency)
        payout.status = "rejected"
        payout.note = str(request.data.get("note") or "مرفوض من الإدارة").strip()
        payout.save(update_fields=["status", "note", "updated_at"])
        return Response(VendorPayoutDomainSerializer(payout).data)
