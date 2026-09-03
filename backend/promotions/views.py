from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_http_methods

from .forms import CouponForm, LoanReviewForm
from .models import Address, Coupon, GiftTransfer, Loan, Referral


@login_required
@require_GET
def dashboard(request):
    user = request.user
    allowed = user.is_staff or getattr(user, "role", None) in {"admin", "vendor"}
    if not allowed:
        return render(request, "admin/domains/dashboard.html", {"error": "لا تملك صلاحية إدارة العروض وخدمات العملاء."}, status=403)
    coupons = Coupon.objects.all()
    addresses = Address.objects.all()
    loans = Loan.objects.all()
    gifts = GiftTransfer.objects.all()
    referrals = Referral.objects.all()
    if not (user.is_staff or getattr(user, "role", None) == "admin"):
        coupons = coupons.filter(is_active=True)
        addresses = addresses.filter(user=user)
        loans = loans.filter(user=user)
        gifts = gifts.filter(sender=user)
        referrals = referrals.filter(inviter=user)
    return render(request, "admin/domains/dashboard.html", {
        "domain_title": "العروض وخدمات العملاء",
        "domain_key": "promotions",
        "stats": [
            {"label": "الكوبونات", "value": coupons.count()},
            {"label": "العناوين", "value": addresses.count()},
            {"label": "طلبات التمويل", "value": loans.count()},
            {"label": "تحويلات الهدايا", "value": gifts.count()},
            {"label": "الإحالات", "value": referrals.count()},
        ],
        "api_prefix": "/api/v2/promotions/",
    })


@login_required
@require_http_methods(["GET", "POST"])
def coupon_form(request, pk=None):
    user = request.user
    if not (user.is_staff or getattr(user, "role", None) == "admin"):
        return render(request, "admin/domains/form.html", {"title": "كوبون", "error": "إدارة الكوبونات للإدارة فقط."}, status=403)
    instance = get_object_or_404(Coupon.objects.all(), pk=pk) if pk else Coupon()
    form = CouponForm(request.POST or None, instance=instance)
    if request.method == "POST" and form.is_valid():
        obj = form.save()
        obj.code = obj.code.strip().upper()
        obj.save(update_fields=["code", "updated_at"])
        return redirect("admin-dashboard-promotions")
    return render(request, "admin/domains/form.html", {"title": "إضافة / تعديل كوبون", "form": form, "cancel_url": "/admin/dashboard/promotions/"})


@login_required
@require_http_methods(["GET", "POST"])
def loan_review(request, pk):
    user = request.user
    if not (user.is_staff or getattr(user, "role", None) == "admin"):
        return render(request, "admin/domains/form.html", {"title": "مراجعة التمويل", "error": "مراجعة التمويل للإدارة فقط."}, status=403)
    loan = get_object_or_404(Loan.objects.all(), pk=pk)
    form = LoanReviewForm(request.POST or None, instance=loan)
    if request.method == "POST" and form.is_valid():
        obj = form.save(commit=False)
        obj.approved_by = user
        obj.save(update_fields=["status", "reason", "approved_by", "updated_at"])
        return redirect("admin-dashboard-promotions")
    return render(request, "admin/domains/form.html", {"title": "مراجعة طلب تمويل", "form": form, "cancel_url": "/admin/dashboard/promotions/"})
