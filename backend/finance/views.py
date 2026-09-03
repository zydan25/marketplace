from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.views.decorators.http import require_GET

from .models import Payment, VendorLedgerEntry, VendorPayout, Wallet


@login_required
@require_GET
def dashboard(request):
    user = request.user
    allowed = user.is_staff or getattr(user, "role", None) in {"admin", "vendor"}
    if not allowed:
        return render(request, "admin/domains/dashboard.html", {"error": "لا تملك صلاحية الإدارة المالية."}, status=403)
    payouts = VendorPayout.objects.all()
    ledger = VendorLedgerEntry.objects.all()
    payments = Payment.objects.all()
    wallets = Wallet.objects.all()
    if getattr(user, "role", None) == "vendor" and not user.is_staff:
        payouts = payouts.filter(vendor__owner=user)
        ledger = ledger.filter(vendor__owner=user)
        payments = payments.filter(order__vendor_orders__vendor__owner=user).distinct()
        wallets = wallets.filter(user=user)
    return render(request, "admin/domains/dashboard.html", {
        "domain_title": "الإدارة المالية والمدفوعات",
        "domain_key": "finance",
        "stats": [
            {"label": "المحافظ", "value": wallets.count()},
            {"label": "الدفعات", "value": payments.count()},
            {"label": "سجلات التجار", "value": ledger.count()},
            {"label": "طلبات السحب", "value": payouts.count()},
        ],
        "api_prefix": "/api/v2/finance/",
    })
