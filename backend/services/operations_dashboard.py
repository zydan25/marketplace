from decimal import Decimal

from django.contrib.auth.decorators import user_passes_test
from django.db.models import Count, Q, Sum
from django.shortcuts import render
from django.utils import timezone

from accounting.models import Account, JournalEntry, JournalLine, Wallet
from accounting.services_v2 import account_balance

from .models import ServiceRequestLog, ServiceTask, ServiceTransaction


def staff_only(user):
    return bool(user.is_authenticated and (user.is_staff or getattr(user, "role", None) == "admin"))


def _base_stats():
    return {
        "accepted": ServiceTransaction.objects.filter(status=ServiceTransaction.Status.ACCEPTED).count(),
        "queued": ServiceTask.objects.filter(status=ServiceTask.Statuses.QUEUED).count(),
        "running": ServiceTask.objects.filter(status=ServiceTask.Statuses.RUNNING).count(),
        "retry": ServiceTask.objects.filter(status=ServiceTask.Statuses.RETRY).count(),
        "pending": ServiceTransaction.objects.filter(status=ServiceTransaction.Status.PENDING_PROVIDER).count(),
        "manual": ServiceTransaction.objects.filter(status=ServiceTransaction.Status.MANUAL_REVIEW).count(),
        "success_today": ServiceTransaction.objects.filter(status=ServiceTransaction.Status.SUCCESS, created_at__date=timezone.localdate()).count(),
        "failed_today": ServiceTransaction.objects.filter(status__in=[ServiceTransaction.Status.FAILED, ServiceTransaction.Status.REFUNDED], created_at__date=timezone.localdate()).count(),
    }


@user_passes_test(staff_only, login_url="/admin/dashboard/login/")
def operations_dashboard(request):
    q = (request.GET.get("q") or "").strip()
    status = (request.GET.get("status") or "").strip()
    transactions = ServiceTransaction.objects.select_related("service", "customer", "provider_link").order_by("-created_at")
    if q:
        transactions = transactions.filter(
            Q(mobile__icontains=q)
            | Q(provider_transaction_id__icontains=q)
            | Q(provider_transid__icontains=q)
            | Q(service__name__icontains=q)
            | Q(service__code__icontains=q)
        )
    if status:
        transactions = transactions.filter(status=status)
    transactions = transactions[:120]
    tasks = ServiceTask.objects.select_related("transaction__service", "transaction__customer", "provider_link").order_by("-id")[:120]
    logs = ServiceRequestLog.objects.select_related("transaction__service", "transaction__customer").order_by("-created_at")[:120]
    context = {
        "section": "operations",
        "stats": _base_stats(),
        "transactions": transactions,
        "tasks": tasks,
        "request_logs": logs,
        "status_choices": ServiceTransaction.Status.choices,
        "filters": {"q": q, "status": status},
    }
    return render(request, "services/operations.html", context)


@user_passes_test(staff_only, login_url="/admin/dashboard/login/")
def balances_dashboard(request):
    wallets = list(
        Wallet.objects.select_related("owner", "account")
        .filter(is_active=True)
        .order_by("-updated_at")[:150]
    )
    for wallet in wallets:
        wallet.current_balance = account_balance(wallet.account)

    key_accounts = list(
        Account.objects.filter(is_active=True, code__in=["100001", "400901", "600001", "600101"])
        .order_by("code")
    )
    for account in key_accounts:
        account.current_balance = account_balance(account)

    journal_entries = list(
        JournalEntry.objects.select_related("created_by")
        .prefetch_related("lines__account")
        .order_by("-id")[:100]
    )
    for entry in journal_entries:
        totals = entry.lines.aggregate(debit=Sum("debit"), credit=Sum("credit"))
        entry.total_debit = totals["debit"] or Decimal("0.00")
        entry.total_credit = totals["credit"] or Decimal("0.00")

    totals = {}
    for wallet in wallets:
        key = wallet.currency
        bucket = totals.setdefault(key, {"customer": Decimal("0.00"), "vendor_available": Decimal("0.00"), "vendor_pending": Decimal("0.00"), "withdrawal_hold": Decimal("0.00")})
        bucket.setdefault(wallet.kind, Decimal("0.00"))
        bucket[wallet.kind] += wallet.current_balance

    context = {
        "section": "balances",
        "wallets": wallets,
        "key_accounts": key_accounts,
        "journal_entries": journal_entries,
        "currency_totals": totals,
        "wallet_kinds": dict(Wallet.Kinds.choices),
    }
    return render(request, "services/balances.html", context)
