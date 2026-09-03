from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.views.decorators.http import require_GET

from .models import DesignTheme, StorefrontMedia, StorefrontSection


def _can_manage(user):
    return bool(user.is_authenticated and (user.is_staff or getattr(user, "role", None) in {"admin", "vendor"}))


@login_required
@require_GET
def dashboard(request):
    if not _can_manage(request.user):
        return render(request, "admin/domains/dashboard.html", {"error": "لا تملك صلاحية إدارة واجهة المتجر."}, status=403)
    vendor = getattr(request.user, "vendor_profile", None) if getattr(request.user, "role", None) == "vendor" else None
    themes = DesignTheme.objects.all()
    sections = StorefrontSection.objects.all()
    media = StorefrontMedia.objects.all()
    if vendor:
        themes = themes.filter(vendor=vendor)
        sections = sections.filter(vendor=vendor)
        media = media.filter(vendor=vendor)
    return render(request, "admin/domains/dashboard.html", {
        "domain_title": "إدارة واجهة المتجر",
        "domain_key": "storefront",
        "stats": [
            {"label": "الثيمات", "value": themes.count()},
            {"label": "الأقسام", "value": sections.count()},
            {"label": "الوسائط", "value": media.count()},
        ],
        "api_prefix": "/api/v2/storefront/",
    })
