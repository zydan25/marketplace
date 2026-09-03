from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.views.decorators.http import require_GET

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
