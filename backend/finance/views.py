from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_http_methods

from orders.models import Payment
from vendors.models import VendorProfile

from .forms import CurrencyRateForm, VendorCityShippingForm
from .models import CurrencyRate, VendorCityShipping, VendorLedgerEntry, VendorPayout, Wallet


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


def _render_form(request, form, title):
    return render(request, "admin/domains/form.html", {"title": title, "form": form, "cancel_url": "/admin/dashboard/finance/"})


@login_required
@require_http_methods(["GET", "POST"])
def currency_rate_form(request, pk=None):
    if not (request.user.is_staff or getattr(request.user, "role", None) == "admin"):
        return render(request, "admin/domains/form.html", {"title": "سعر صرف", "error": "إدارة أسعار الصرف للإدارة فقط."}, status=403)
    instance = get_object_or_404(CurrencyRate.objects.all(), pk=pk) if pk else CurrencyRate()
    form = CurrencyRateForm(request.POST or None, instance=instance)
    if request.method == "POST" and form.is_valid():
        obj = form.save(commit=False)
        obj.updated_by = request.user
        obj.save()
        return redirect("admin-dashboard-finance")
    return _render_form(request, form, "إضافة / تعديل سعر صرف")


@login_required
@require_http_methods(["GET", "POST"])
def vendor_shipping_form(request, pk=None):
    user = request.user
    if not (user.is_staff or getattr(user, "role", None) in {"admin", "vendor"}):
        return render(request, "admin/domains/form.html", {"title": "شحن المدن", "error": "غير مصرح."}, status=403)

    vendor = None
    if getattr(user, "role", None) == "vendor" and not user.is_staff:
        vendor = get_object_or_404(VendorProfile.objects.filter(owner=user, status="active"))
    instance = None
    if pk:
        qs = VendorCityShipping.objects.all()
        if vendor:
            qs = qs.filter(vendor=vendor)
        instance = get_object_or_404(qs, pk=pk)

    form = VendorCityShippingForm(
        request.POST or None,
        instance=instance,
        vendor_required=vendor is None,
    )
    if request.method == "POST" and form.is_valid():
        obj = form.save(commit=False)
        if vendor:
            obj.vendor = vendor
        elif obj.vendor_id is None:
            form.add_error("vendor", "اختيار التاجر مطلوب للإدارة.")
            return _render_form(request, form, "إضافة / تعديل رسوم الشحن")
        obj.save()
        return redirect("admin-dashboard-finance")
    return _render_form(request, form, "إضافة / تعديل رسوم الشحن")
