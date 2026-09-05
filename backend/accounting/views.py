from decimal import Decimal
import uuid

from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.db.models import Sum

from .models import Account, JournalEntry, JournalLine, Voucher, Wallet, WithdrawalRequest
from .services_v2 import account_balance, ensure_chart, post_entry


def staff_only(user):
    return bool(user.is_authenticated and (user.is_staff or getattr(user, "role", None) == "admin"))


def _leaf_accounts(root_code):
    root = Account.objects.filter(code=root_code).first()
    if not root:
        return Account.objects.none()
    return Account.objects.filter(code__startswith=root.code, is_group=False, is_active=True).order_by("code")


def _report(account):
    rows = JournalLine.objects.filter(account=account, entry__status=JournalEntry.Status.POSTED).select_related("entry").order_by("entry__entry_date", "entry_id", "id")
    running = Decimal("0.00")
    out = []
    for row in rows:
        amount = Decimal(row.credit) - Decimal(row.debit) if account.normal_side == Account.NormalSides.CREDIT else Decimal(row.debit) - Decimal(row.credit)
        running += amount
        out.append({"line": row, "running": running})
    return out, running


@user_passes_test(staff_only, login_url="/admin/dashboard/login/")
def dashboard(request, section="overview"):
    ensure_chart()
    if request.method == "POST":
        try:
            action = request.POST.get("action")
            with transaction.atomic():
                if action == "account_create":
                    parent = get_object_or_404(Account, pk=request.POST.get("parent"), is_group=True, is_active=True)
                    name = (request.POST.get("name") or "").strip()
                    if not name:
                        raise ValueError("اسم الحساب مطلوب.")
                    from .services_v2 import _get_or_create_child
                    account = _get_or_create_child(parent, name, is_group=request.POST.get("is_group") == "1", account_type=request.POST.get("account_type") or Account.Types.ASSET, normal_side=request.POST.get("normal_side") or Account.NormalSides.DEBIT, party_type=(request.POST.get("party_type") or "").strip())
                    account.is_active = request.POST.get("is_active") != "0"
                    account.save(update_fields=["is_active", "updated_at"])
                    section = "accounts"
                elif action == "account_edit":
                    account = get_object_or_404(Account, pk=request.POST.get("pk"))
                    if account.journal_lines.exists():
                        raise ValueError("لا يمكن تعديل حساب لديه قيود؛ عطّله أو أنشئ حسابًا جديدًا للتصحيح.")
                    name = (request.POST.get("name") or "").strip()
                    if not name:
                        raise ValueError("اسم الحساب مطلوب.")
                    account.name = name
                    account.account_type = request.POST.get("account_type") or account.account_type
                    account.normal_side = request.POST.get("normal_side") or account.normal_side
                    account.save(update_fields=["name", "account_type", "normal_side", "updated_at"])
                    section = "accounts"
                elif action == "account_toggle":
                    account = get_object_or_404(Account, pk=request.POST.get("pk"))
                    if account.parent_id is None:
                        raise ValueError("الحسابات الجذرية لا تعطل.")
                    account.is_active = not account.is_active
                    account.save(update_fields=["is_active", "updated_at"])
                    section = "accounts"
                elif action == "account_delete":
                    account = get_object_or_404(Account, pk=request.POST.get("pk"))
                    if account.parent_id is None or account.children.exists() or account.journal_lines.exists() or Wallet.objects.filter(account=account).exists():
                        raise ValueError("لا يمكن حذف حساب مرتبط أو حساب جذري؛ عطّله بدلًا من الحذف.")
                    account.delete()
                    section = "accounts"
                elif action in {"receipt", "payment"}:
                    amount = Decimal(str(request.POST.get("amount") or "0")).quantize(Decimal("0.01"))
                    if amount <= 0:
                        raise ValueError("أدخل مبلغًا موجبًا.")
                    cash = get_object_or_404(Account, pk=request.POST.get("cash_account"), is_group=False, is_active=True)
                    party = get_object_or_404(Account, pk=request.POST.get("party_account"), is_group=False, is_active=True)
                    if not cash.code.startswith("1000"):
                        raise ValueError("حساب الصندوق يجب أن يكون تحت مجموعة الصناديق.")
                    if party.code.startswith("1000"):
                        raise ValueError("حساب الطرف لا يمكن أن يكون حساب صندوق.")
                    description = (request.POST.get("description") or "").strip() or ("سند قبض" if action == "receipt" else "سند صرف")
                    source_id = str(uuid.uuid4())
                    lines = ([{"account": cash, "debit": amount}, {"account": party, "credit": amount}] if action == "receipt" else [{"account": party, "debit": amount}, {"account": cash, "credit": amount}])
                    entry = post_entry(description, lines, source_type="voucher", source_id=source_id, created_by=request.user)
                    Voucher.objects.create(number=f"{'RV' if action == 'receipt' else 'PV'}-{timezone.now():%Y%m%d}-{uuid.uuid4().hex[:8].upper()}", voucher_type=Voucher.Types.RECEIPT if action == "receipt" else Voucher.Types.PAYMENT, voucher_date=timezone.localdate(), amount=amount, currency=(request.POST.get("currency") or "YER").upper(), cash_account=cash, party_account=party, journal_entry=entry, description=description, source_type="manual", source_id=source_id, created_by=request.user)
                    section = "vouchers"
                elif action == "withdrawal":
                    item = get_object_or_404(WithdrawalRequest, pk=request.POST.get("pk"))
                    if item.status == WithdrawalRequest.Status.PENDING:
                        item.status = WithdrawalRequest.Status.APPROVED
                        item.save(update_fields=["status", "updated_at"])
                    elif item.status == WithdrawalRequest.Status.APPROVED:
                        from .services_v2 import settle_withdrawal
                        item.settlement_journal = settle_withdrawal(item.requester, item.amount, item.currency, withdrawal_id=item.number, created_by=request.user)
                        item.status = WithdrawalRequest.Status.PAID
                        item.save(update_fields=["status", "settlement_journal", "updated_at"])
                    section = "withdrawals"
                elif action == "withdrawal_reject":
                    item = get_object_or_404(WithdrawalRequest, pk=request.POST.get("pk"))
                    if item.status not in {WithdrawalRequest.Status.PENDING, WithdrawalRequest.Status.APPROVED}:
                        raise ValueError("لا يمكن رفض طلب السحب بالحالة الحالية.")
                    from .services_v2 import reject_withdrawal
                    reject_withdrawal(item.requester, item.amount, item.currency, withdrawal_id=item.number, created_by=request.user)
                    item.status = WithdrawalRequest.Status.REJECTED
                    item.save(update_fields=["status", "updated_at"])
                    section = "withdrawals"
                else:
                    raise ValueError("عملية غير معروفة.")
            messages.success(request, "تم تنفيذ العملية بنجاح.")
        except (ValueError, TypeError, ArithmeticError) as exc:
            messages.error(request, str(exc))
        except Exception as exc:
            messages.error(request, f"تعذر تنفيذ العملية: {exc}")
        return redirect("admin-dashboard-accounting-section", section=section)

    section = section or "overview"
    accounts = Account.objects.select_related("parent", "party_user").order_by("code")
    roots = accounts.filter(parent__isnull=True, is_group=True)
    groups = accounts.filter(is_group=True, is_active=True).order_by("code")
    account_rows = [{"account": account, "balance": account_balance(account)} for account in accounts]
    selected_report = None
    report_rows = []
    report_balance = Decimal("0.00")
    account_id = request.GET.get("account")
    if account_id:
        selected_report = get_object_or_404(accounts, pk=account_id)
        report_rows, report_balance = _report(selected_report)
    wallet_rows = [{"wallet": wallet, "balance": account_balance(wallet.account)} for wallet in Wallet.objects.select_related("owner", "account").order_by("owner_id", "kind")[:100]]
    context = {
        "title": "مركز المحاسبة",
        "section": section,
        "roots": roots,
        "accounts": accounts,
        "account_rows": account_rows,
        "groups": groups,
        "cash_accounts": _leaf_accounts("1000"),
        "party_accounts": accounts.filter(is_group=False, is_active=True).exclude(code__startswith="1000").order_by("code"),
        "vouchers": Voucher.objects.select_related("cash_account", "party_account", "journal_entry", "created_by").order_by("-id")[:100],
        "journals": JournalEntry.objects.prefetch_related("lines__account").order_by("-id")[:100],
        "withdrawals": WithdrawalRequest.objects.select_related("requester", "hold_journal", "settlement_journal").order_by("-id")[:100],
        "wallets": Wallet.objects.select_related("owner", "account").order_by("owner_id", "kind")[:100],
        "wallet_rows": wallet_rows,
        "recent_entries": JournalEntry.objects.order_by("-id")[:8],
        "pending_withdrawals": WithdrawalRequest.objects.filter(status=WithdrawalRequest.Status.PENDING),
        "journal_count": JournalEntry.objects.filter(status=JournalEntry.Status.POSTED).count(),
        "account_count": Account.objects.count(),
        "voucher_count": Voucher.objects.count(),
        "wallet_count": Wallet.objects.count(),
        "selected_report": selected_report,
        "report_rows": report_rows,
        "report_balance": report_balance,
    }
    return render(request, "accounting/dashboard.html", context)
