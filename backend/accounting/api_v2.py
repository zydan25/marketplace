from datetime import date
from decimal import Decimal, InvalidOperation
import uuid

from django.db import transaction
from django.db.models import Sum
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Account, JournalEntry, Voucher, Wallet, WithdrawalRequest
from .serializers import AccountSerializer, JournalEntrySerializer, VoucherSerializer, WalletSerializer, WithdrawalRequestSerializer
from .services_v2 import account_balance, ensure_chart, ensure_wallet, hold_withdrawal, post_entry, reject_withdrawal, settle_withdrawal, statement_for_user, wallet_summary
from .legacy_sync import sync_vendor_pending


def is_admin(user):
    return bool(user.is_staff or getattr(user, "role", None) == "admin")


def money(value):
    try:
        return Decimal(str(value)).quantize(Decimal("0.01"))
    except (InvalidOperation, TypeError, ValueError):
        raise ValidationError({"amount": "المبلغ غير صالح."})


class AdminOnlyMixin:
    def require_admin(self):
        if not is_admin(self.request.user):
            raise PermissionDenied("هذه العملية متاحة للإدارة فقط.")


class AccountViewSet(AdminOnlyMixin, viewsets.ModelViewSet):
    queryset = Account.objects.select_related("parent", "party_user").all()
    serializer_class = AccountSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "post", "delete", "head", "options"]

    def get_queryset(self):
        self.require_admin()
        return self.queryset

    def create(self, request, *args, **kwargs):
        self.require_admin()
        parent = Account.objects.filter(pk=request.data.get("parent"), is_group=True, is_active=True).first()
        if not parent:
            raise ValidationError({"parent": "اختر حسابًا رئيسيًا فعالًا."})
        name = str(request.data.get("name", "")).strip()
        if not name:
            raise ValidationError({"name": "اسم الحساب مطلوب."})
        account_type = request.data.get("account_type") or Account.Types.ASSET
        normal_side = request.data.get("normal_side") or (Account.NormalSides.CREDIT if account_type in {Account.Types.LIABILITY, Account.Types.EQUITY, Account.Types.INCOME} else Account.NormalSides.DEBIT)
        from .services_v2 import _get_or_create_child
        account = _get_or_create_child(parent, name, is_group=False, account_type=account_type, normal_side=normal_side, party_type=str(request.data.get("party_type", "")).strip())
        return Response(AccountSerializer(account).data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        raise ValidationError({"account": "تعديل الحسابات المرحّلة غير مسموح. غيّر حالة التفعيل أو أنشئ حساب تصحيح."})

    partial_update = update

    def destroy(self, request, *args, **kwargs):
        self.require_admin()
        account = self.get_object()
        if account.parent_id is None:
            raise ValidationError({"account": "لا يمكن حذف الحسابات الجذرية."})
        if account.children.exists() or account.journal_lines.exists() or Wallet.objects.filter(account=account).exists():
            raise ValidationError({"account": "لا يمكن حذف حساب مرتبط بقيود أو محافظ. قم بإيقافه بدلًا من حذفه."})
        account.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=["get"])
    def tree(self, request):
        self.require_admin()
        ensure_chart()
        return Response(self.get_serializer(self.get_queryset(), many=True).data)


class WalletViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = WalletSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = Wallet.objects.select_related("owner", "account")
        return qs if is_admin(self.request.user) else qs.filter(owner=self.request.user)

    def list(self, request, *args, **kwargs):
        currency = str(request.query_params.get("currency", "YER")).upper()
        if getattr(request.user, "role", None) == "vendor":
            sync_vendor_pending(request.user, currency)
        summary = wallet_summary(request.user, currency)
        return Response({**summary, "wallets": WalletSerializer(self.get_queryset().filter(currency=currency), many=True).data})

    def retrieve(self, request, *args, **kwargs):
        return Response(WalletSerializer(self.get_object()).data)

    @action(detail=False, methods=["get"], url_path="me/balance")
    def my_balance(self, request):
        currency = str(request.query_params.get("currency", "YER")).upper()
        if getattr(request.user, "role", None) == "vendor":
            sync_vendor_pending(request.user, currency)
        return Response(wallet_summary(request.user, currency))

    @action(detail=False, methods=["get"], url_path="me/statement")
    def my_statement(self, request):
        currency = str(request.query_params.get("currency", "YER")).upper()
        if getattr(request.user, "role", None) == "vendor":
            sync_vendor_pending(request.user, currency)
        return Response({"currency": currency, "statement": statement_for_user(request.user, currency)})


class JournalEntryViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = JournalEntrySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = JournalEntry.objects.select_related("created_by").prefetch_related("lines__account").all()
        if is_admin(self.request.user):
            return qs
        ids = Wallet.objects.filter(owner=self.request.user).values_list("account_id", flat=True)
        return qs.filter(lines__account_id__in=ids).distinct()


class VoucherViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = VoucherSerializer
    permission_classes = [IsAuthenticated]
    queryset = Voucher.objects.select_related("cash_account", "party_account", "journal_entry", "created_by").all()

    def get_queryset(self):
        return self.queryset if is_admin(self.request.user) else self.queryset.filter(created_by=self.request.user)

    def _create(self, request, voucher_type):
        if not is_admin(request.user):
            raise PermissionDenied("إصدار السندات للإدارة فقط.")
        amount = money(request.data.get("amount"))
        if amount <= 0:
            raise ValidationError({"amount": "أدخل مبلغًا موجبًا."})
        cash = Account.objects.filter(pk=request.data.get("cash_account"), is_group=False, is_active=True).first()
        party = Account.objects.filter(pk=request.data.get("party_account"), is_group=False, is_active=True).first()
        if not cash or not party:
            raise ValidationError("يجب اختيار حسابين فرعيين فعالين.")
        if not cash.code.startswith("1000"):
            raise ValidationError({"cash_account": "يجب اختيار حساب صندوق/نقد تحت مجموعة الصناديق."})
        if party.code.startswith("1000"):
            raise ValidationError({"party_account": "حساب الطرف لا يمكن أن يكون حساب صندوق."})
        description = str(request.data.get("description", "")).strip()
        source_id = str(uuid.uuid4())
        lines = ([{"account": cash, "debit": amount}, {"account": party, "credit": amount}] if voucher_type == Voucher.Types.RECEIPT else [{"account": party, "debit": amount}, {"account": cash, "credit": amount}])
        entry = post_entry(description or ("سند قبض" if voucher_type == Voucher.Types.RECEIPT else "سند صرف"), lines, source_type="voucher", source_id=source_id, created_by=request.user)
        voucher = Voucher.objects.create(number=f"{'RV' if voucher_type == Voucher.Types.RECEIPT else 'PV'}-{timezone.now():%Y%m%d}-{uuid.uuid4().hex[:8].upper()}", voucher_type=voucher_type, voucher_date=date.today(), amount=amount, currency=str(request.data.get("currency", "YER")).upper(), cash_account=cash, party_account=party, journal_entry=entry, description=description, source_type=str(request.data.get("source_type", "manual")), source_id=str(request.data.get("source_id", "")), created_by=request.user)
        return Response(VoucherSerializer(voucher).data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["post"])
    def receipt(self, request):
        return self._create(request, Voucher.Types.RECEIPT)

    @action(detail=False, methods=["post"])
    def payment(self, request):
        return self._create(request, Voucher.Types.PAYMENT)


class WithdrawalViewSet(viewsets.ModelViewSet):
    serializer_class = WithdrawalRequestSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self):
        qs = WithdrawalRequest.objects.select_related("requester", "hold_journal", "settlement_journal")
        return qs if is_admin(self.request.user) else qs.filter(requester=self.request.user)

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        if getattr(request.user, "role", None) != "vendor":
            raise PermissionDenied("طلبات السحب مخصصة للتاجر.")
        amount = money(request.data.get("amount"))
        currency = str(request.data.get("currency", "YER")).upper()
        sync_vendor_pending(request.user, currency)
        available_wallet = ensure_wallet(request.user, Wallet.Kinds.VENDOR_AVAILABLE, currency)
        available_account = Account.objects.select_for_update().get(pk=available_wallet.account_id)
        available = account_balance(available_account)
        held = WithdrawalRequest.objects.select_for_update().filter(requester=request.user, currency=currency, status__in=[WithdrawalRequest.Status.PENDING, WithdrawalRequest.Status.APPROVED]).aggregate(v=Sum("amount"))["v"] or Decimal("0.00")
        withdrawable = available - held
        if amount <= 0 or amount > withdrawable:
            raise ValidationError({"amount": f"المتاح للسحب {withdrawable} {currency}."})
        item = WithdrawalRequest.objects.create(number=f"WD-{timezone.now():%Y%m%d}-{uuid.uuid4().hex[:8].upper()}", requester=request.user, amount=amount, currency=currency, note=str(request.data.get("note", "")).strip())
        item.hold_journal = hold_withdrawal(request.user, amount, currency, withdrawal_id=item.number, created_by=request.user)
        item.save(update_fields=["hold_journal", "updated_at"])
        return Response(WithdrawalRequestSerializer(item).data, status=status.HTTP_201_CREATED)

    def _admin_item(self, request, pk):
        if not is_admin(request.user):
            raise PermissionDenied("الإدارة فقط.")
        return WithdrawalRequest.objects.select_for_update().get(pk=pk)

    @action(detail=True, methods=["post"])
    @transaction.atomic
    def approve(self, request, pk=None):
        item = self._admin_item(request, pk)
        if item.status != WithdrawalRequest.Status.PENDING:
            raise ValidationError({"status": "الطلب ليس معلقًا."})
        item.status = WithdrawalRequest.Status.APPROVED
        item.save(update_fields=["status", "updated_at"])
        return Response(WithdrawalRequestSerializer(item).data)

    @action(detail=True, methods=["post"])
    @transaction.atomic
    def pay(self, request, pk=None):
        item = self._admin_item(request, pk)
        if item.status != WithdrawalRequest.Status.APPROVED:
            raise ValidationError({"status": "يجب اعتماد الطلب قبل الصرف."})
        entry = settle_withdrawal(item.requester, item.amount, item.currency, withdrawal_id=item.number, created_by=request.user)
        item.settlement_journal = entry
        item.status = WithdrawalRequest.Status.PAID
        item.save(update_fields=["settlement_journal", "status", "updated_at"])
        return Response(WithdrawalRequestSerializer(item).data)

    @action(detail=True, methods=["post"])
    @transaction.atomic
    def reject(self, request, pk=None):
        item = self._admin_item(request, pk)
        if item.status not in {WithdrawalRequest.Status.PENDING, WithdrawalRequest.Status.APPROVED}:
            raise ValidationError({"status": "لا يمكن رفض الطلب بالحالة الحالية."})
        reject_withdrawal(item.requester, item.amount, item.currency, withdrawal_id=item.number, created_by=request.user)
        item.status = WithdrawalRequest.Status.REJECTED
        item.note = str(request.data.get("note") or "تم رفض الطلب").strip()
        item.save(update_fields=["status", "note", "updated_at"])
        return Response(WithdrawalRequestSerializer(item).data)
