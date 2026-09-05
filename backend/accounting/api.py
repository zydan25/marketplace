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

from .models import Account, JournalEntry, JournalLine, Voucher, Wallet, WithdrawalRequest
from .services import account_balance, ensure_chart, ensure_wallet, hold_withdrawal, post_entry, reject_withdrawal, settle_withdrawal, statement_for_user, wallet_summary


def is_admin(user):
    return bool(user.is_staff or getattr(user, "role", None) == "admin")


def money(value):
    try:
        return Decimal(str(value)).quantize(Decimal("0.01"))
    except (InvalidOperation, TypeError, ValueError):
        raise ValidationError({"amount": "المبلغ غير صالح."})


class AccountViewSet(viewsets.ModelViewSet):
    queryset = Account.objects.select_related("parent", "party_user").all()
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if not is_admin(self.request.user):
            return Account.objects.none()
        return super().get_queryset()

    def create(self, request, *args, **kwargs):
        if not is_admin(request.user):
            raise PermissionDenied("إدارة شجرة الحسابات للإدارة فقط.")
        parent_id = request.data.get("parent")
        if not parent_id:
            raise ValidationError({"parent": "الحسابات الجديدة يجب أن تكون تحت حساب رئيسي."})
        parent = Account.objects.filter(pk=parent_id, is_active=True).first()
        if not parent or not parent.is_group:
            raise ValidationError({"parent": "يجب اختيار حساب رئيسي فعال."})
        name = str(request.data.get("name", "")).strip()
        if not name:
            raise ValidationError({"name": "اسم الحساب مطلوب."})
        account_type = request.data.get("account_type") or Account.Types.ASSET
        normal_side = request.data.get("normal_side") or (
            Account.NormalSides.CREDIT if account_type in {Account.Types.LIABILITY, Account.Types.EQUITY, Account.Types.INCOME} else Account.NormalSides.DEBIT
        )
        from .services import _leaf_account
        account = _leaf_account(parent, name, account_type, normal_side)
        return Response(self._serialize(account), status=status.HTTP_201_CREATED)

    def destroy(self, request, *args, **kwargs):
        if not is_admin(request.user):
            raise PermissionDenied("حذف الحسابات للإدارة فقط.")
        account = self.get_object()
        if account.children.exists() or account.journal_lines.exists() or Wallet.objects.filter(account=account).exists():
            raise ValidationError({"account": "لا يمكن حذف حساب مرتبط. قم بإيقافه بدلًا من حذفه."})
        account.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @staticmethod
    def _serialize(account):
        return {
            "id": account.id,
            "code": account.code,
            "name": account.name,
            "parent": account.parent_id,
            "parent_name": account.parent.name if account.parent else None,
            "account_type": account.account_type,
            "normal_side": account.normal_side,
            "is_group": account.is_group,
            "is_active": account.is_active,
            "balance": str(account_balance(account)) if not account.is_group else None,
            "party_type": account.party_type,
            "party_user": account.party_user_id,
        }

    @action(detail=False, methods=["get"])
    def tree(self, request):
        if not is_admin(request.user):
            raise PermissionDenied("شجرة الحسابات للإدارة فقط.")
        ensure_chart()
        return Response([self._serialize(account) for account in Account.objects.select_related("parent").order_by("code")])


class WalletViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = None

    def get_queryset(self):
        if is_admin(self.request.user):
            return Wallet.objects.select_related("owner", "account").all()
        return Wallet.objects.filter(owner=self.request.user).select_related("account")

    def list(self, request, *args, **kwargs):
        currency = str(request.query_params.get("currency", "YER")).upper()
        summary = wallet_summary(request.user, currency)
        summary["wallets"] = [
            {"id": wallet.id, "kind": wallet.kind, "kind_label": wallet.get_kind_display(), "currency": currency, "balance": str(account_balance(wallet.account)), "account_id": wallet.account_id, "account_code": wallet.account.code}
            for wallet in self.get_queryset().filter(currency=currency)
        ]
        return Response(summary)

    @action(detail=False, methods=["get"], url_path="me/balance")
    def my_balance(self, request):
        currency = str(request.query_params.get("currency", "YER")).upper()
        return Response(wallet_summary(request.user, currency))

    @action(detail=False, methods=["get"], url_path="me/statement")
    def my_statement(self, request):
        currency = str(request.query_params.get("currency", "YER")).upper()
        return Response({"currency": currency, "statement": statement_for_user(request.user, currency)})


class JournalEntryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = JournalEntry.objects.select_related("created_by").prefetch_related("lines__account").all()
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if is_admin(self.request.user):
            return self.queryset
        wallet_account_ids = Wallet.objects.filter(owner=self.request.user).values_list("account_id", flat=True)
        return self.queryset.filter(lines__account_id__in=wallet_account_ids).distinct()

    def retrieve(self, request, *args, **kwargs):
        entry = self.get_object()
        return Response({
            "id": entry.id,
            "number": entry.number,
            "date": entry.entry_date.isoformat(),
            "description": entry.description,
            "source_type": entry.source_type,
            "source_id": entry.source_id,
            "status": entry.status,
            "lines": [{"account_id": line.account_id, "code": line.account.code, "name": line.account.name, "debit": str(line.debit), "credit": str(line.credit), "description": line.description} for line in entry.lines.all()],
        })


class VoucherViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Voucher.objects.select_related("cash_account", "party_account", "journal_entry", "created_by").all()
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return self.queryset if is_admin(self.request.user) else self.queryset.filter(created_by=self.request.user)

    def _create_voucher(self, request, voucher_type):
        if not is_admin(request.user):
            raise PermissionDenied("إصدار السندات للإدارة فقط.")
        amount = money(request.data.get("amount"))
        if amount <= 0:
            raise ValidationError({"amount": "أدخل مبلغًا موجبًا."})
        currency = str(request.data.get("currency", "YER")).upper()
        cash = Account.objects.filter(pk=request.data.get("cash_account"), is_group=False, is_active=True).first()
        party = Account.objects.filter(pk=request.data.get("party_account"), is_group=False, is_active=True).first()
        if not cash or not party:
            raise ValidationError("الصندوق والحساب المقابل يجب أن يكونا حسابين فرعيين فعالين.")
        if cash.account_type != Account.Types.ASSET:
            raise ValidationError({"cash_account": "حساب الصندوق يجب أن يكون من الأصول."})
        entry = post_entry(
            f"{('سند قبض' if voucher_type == Voucher.Types.RECEIPT else 'سند صرف')} - {request.data.get('description', '')}".strip(" -"),
            ([{"account": cash, "debit": amount}, {"account": party, "credit": amount}] if voucher_type == Voucher.Types.RECEIPT else [{"account": party, "debit": amount}, {"account": cash, "credit": amount}]),
            source_type="voucher",
            source_id=str(uuid.uuid4()),
            idempotency_key=f"voucher:{voucher_type}:{uuid.uuid4().hex}",
            created_by=request.user,
        )
        voucher = Voucher.objects.create(
            number=f"{'RV' if voucher_type == Voucher.Types.RECEIPT else 'PV'}-{timezone.now():%Y%m%d}-{uuid.uuid4().hex[:8].upper()}",
            voucher_type=voucher_type,
            voucher_date=date.today(),
            amount=amount,
            currency=currency,
            cash_account=cash,
            party_account=party,
            journal_entry=entry,
            description=str(request.data.get("description", "")).strip(),
            source_type=str(request.data.get("source_type", "manual")),
            source_id=str(request.data.get("source_id", "")),
            created_by=request.user,
        )
        return Response({"id": voucher.id, "number": voucher.number, "type": voucher.voucher_type, "amount": str(amount), "currency": currency, "journal": entry.number}, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["post"])
    def receipt(self, request):
        return self._create_voucher(request, Voucher.Types.RECEIPT)

    @action(detail=False, methods=["post"])
    def payment(self, request):
        return self._create_voucher(request, Voucher.Types.PAYMENT)


class WithdrawalViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self):
        qs = WithdrawalRequest.objects.select_related("requester", "hold_journal", "settlement_journal")
        return qs if is_admin(self.request.user) else qs.filter(requester=self.request.user)

    def list(self, request, *args, **kwargs):
        return Response([{"id": item.id, "number": item.number, "amount": str(item.amount), "currency": item.currency, "status": item.status, "note": item.note, "created_at": item.created_at.isoformat()} for item in self.get_queryset()])

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        if getattr(request.user, "role", None) != "vendor":
            raise PermissionDenied("طلبات السحب مخصصة للتاجر.")
        amount = money(request.data.get("amount"))
        currency = str(request.data.get("currency", "YER")).upper()
        available = account_balance(ensure_wallet(request.user, Wallet.Kinds.VENDOR_AVAILABLE, currency).account)
        already_held = WithdrawalRequest.objects.filter(requester=request.user, currency=currency, status__in=[WithdrawalRequest.Status.PENDING, WithdrawalRequest.Status.APPROVED]).aggregate(v=Sum("amount"))["v"] or Decimal("0.00")
        withdrawable = available - already_held
        if amount <= 0 or amount > withdrawable:
            raise ValidationError({"amount": f"المتاح للسحب {withdrawable} {currency}."})
        item = WithdrawalRequest.objects.create(number=f"WD-{timezone.now():%Y%m%d}-{uuid.uuid4().hex[:8].upper()}", requester=request.user, amount=amount, currency=currency, note=str(request.data.get("note", "")).strip())
        item.hold_journal = hold_withdrawal(request.user, amount, currency, withdrawal_id=item.number, created_by=request.user)
        item.save(update_fields=["hold_journal", "updated_at"])
        return Response({"id": item.id, "number": item.number, "status": item.status, "amount": str(amount), "currency": currency, "message": "تم حجز المبلغ وإنشاء طلب السحب للمراجعة."}, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    @transaction.atomic
    def approve(self, request, pk=None):
        if not is_admin(request.user):
            raise PermissionDenied("الإدارة فقط.")
        item = self.get_object()
        if item.status != WithdrawalRequest.Status.PENDING:
            raise ValidationError({"status": "الطلب ليس معلقًا."})
        item.status = WithdrawalRequest.Status.APPROVED
        item.save(update_fields=["status", "updated_at"])
        return Response({"number": item.number, "status": item.status})

    @action(detail=True, methods=["post"])
    @transaction.atomic
    def pay(self, request, pk=None):
        if not is_admin(request.user):
            raise PermissionDenied("الإدارة فقط.")
        item = WithdrawalRequest.objects.select_for_update().get(pk=pk)
        if item.status != WithdrawalRequest.Status.APPROVED:
            raise ValidationError({"status": "يجب اعتماد الطلب قبل صرفه."})
        entry = settle_withdrawal(item.requester, item.amount, item.currency, withdrawal_id=item.number, created_by=request.user)
        item.settlement_journal = entry
        item.status = WithdrawalRequest.Status.PAID
        item.save(update_fields=["settlement_journal", "status", "updated_at"])
        return Response({"number": item.number, "status": item.status, "journal": entry.number})

    @action(detail=True, methods=["post"])
    @transaction.atomic
    def reject(self, request, pk=None):
        if not is_admin(request.user):
            raise PermissionDenied("الإدارة فقط.")
        item = WithdrawalRequest.objects.select_for_update().get(pk=pk)
        if item.status not in {WithdrawalRequest.Status.PENDING, WithdrawalRequest.Status.APPROVED}:
            raise ValidationError({"status": "لا يمكن رفض الطلب بالحالة الحالية."})
        reject_withdrawal(item.requester, item.amount, item.currency, withdrawal_id=item.number, created_by=request.user)
        item.status = WithdrawalRequest.Status.REJECTED
        item.note = str(request.data.get("note") or "تم رفض الطلب").strip()
        item.save(update_fields=["status", "note", "updated_at"])
        return Response({"number": item.number, "status": item.status})
