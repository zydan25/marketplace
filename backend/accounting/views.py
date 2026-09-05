from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from django.db.models import Sum
from django.shortcuts import redirect, render

from .models import Account, JournalEntry, WithdrawalRequest
from .services import account_balance, ensure_chart


def staff_only(user):
    return bool(user.is_authenticated and (user.is_staff or getattr(user, "role", None) == "admin"))


@user_passes_test(staff_only, login_url="/admin/dashboard/login/")
def dashboard(request):
    ensure_chart()
    roots = []
    for account in Account.objects.filter(is_group=True).order_by("code"):
        children = account.children.filter(is_active=True).order_by("code")
        balance = sum((account_balance(child) for child in children if not child.is_group), Decimal("0.00"))
        roots.append({"account": account, "balance": balance, "children": children})
    pending_withdrawals = WithdrawalRequest.objects.filter(status=WithdrawalRequest.Status.PENDING)
    recent_entries = JournalEntry.objects.prefetch_related("lines__account").order_by("-id")[:20]
    context = {
        "roots": roots,
        "recent_entries": recent_entries,
        "pending_withdrawals": pending_withdrawals,
        "pending_withdrawals_total": pending_withdrawals.aggregate(v=Sum("amount"))["v"] or Decimal("0.00"),
        "title": "المحاسبة والعمليات المالية",
    }
    return render(request, "accounting/dashboard.html", context)
