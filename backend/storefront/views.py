from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_http_methods

from .forms import DesignThemeForm, StorefrontMediaForm, StorefrontSectionForm
from .models import DesignTheme, StorefrontMedia, StorefrontSection


def _can_manage(user):
    return bool(user.is_authenticated and (user.is_staff or getattr(user, "role", None) in {"admin", "vendor"}))


def _vendor_for(user):
    return getattr(user, "vendor_profile", None) if getattr(user, "role", None) == "vendor" else None


@login_required
@require_GET
def dashboard(request):
    if not _can_manage(request.user):
        return render(request, "admin/domains/dashboard.html", {"error": "لا تملك صلاحية إدارة واجهة المتجر."}, status=403)
    vendor = _vendor_for(request.user)
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


def _render_form(request, form, title):
    return render(request, "admin/domains/form.html", {"title": title, "form": form, "cancel_url": "/admin/dashboard/storefront/"})


@login_required
@require_http_methods(["GET", "POST"])
def theme_form(request, pk=None):
    if not _can_manage(request.user):
        return render(request, "admin/domains/form.html", {"title": "الثيم", "error": "غير مصرح."}, status=403)
    vendor = _vendor_for(request.user)
    queryset = DesignTheme.objects.filter(vendor=vendor) if vendor else DesignTheme.objects.all()
    instance = get_object_or_404(queryset, pk=pk) if pk else DesignTheme()
    form = DesignThemeForm(request.POST or None, instance=instance)
    if request.method == "POST" and form.is_valid():
        theme = form.save(commit=False)
        if vendor:
            theme.vendor = vendor
            theme.owner = request.user
            theme.is_global = False
        elif theme.is_global:
            theme.vendor = None
            theme.owner = request.user
        elif theme.owner_id is None:
            theme.owner = request.user
        theme.save()
        return redirect("admin-dashboard-storefront")
    return _render_form(request, form, "إضافة / تعديل ثيم الواجهة")


@login_required
@require_http_methods(["GET", "POST"])
def section_form(request, pk=None):
    if not _can_manage(request.user):
        return render(request, "admin/domains/form.html", {"title": "قسم واجهة", "error": "غير مصرح."}, status=403)
    vendor = _vendor_for(request.user)
    queryset = StorefrontSection.objects.filter(vendor=vendor) if vendor else StorefrontSection.objects.all()
    instance = get_object_or_404(queryset, pk=pk) if pk else StorefrontSection()
    form = StorefrontSectionForm(request.POST or None, instance=instance)
    if request.method == "POST" and form.is_valid():
        section = form.save(commit=False)
        section.owner = request.user
        section.vendor = vendor
        section.save()
        return redirect("admin-dashboard-storefront")
    return _render_form(request, form, "إضافة / تعديل قسم واجهة")


@login_required
@require_http_methods(["GET", "POST"])
def media_form(request, pk=None):
    if not _can_manage(request.user):
        return render(request, "admin/domains/form.html", {"title": "وسائط واجهة", "error": "غير مصرح."}, status=403)
    vendor = _vendor_for(request.user)
    queryset = StorefrontMedia.objects.filter(vendor=vendor) if vendor else StorefrontMedia.objects.all()
    instance = get_object_or_404(queryset, pk=pk) if pk else StorefrontMedia()
    form = StorefrontMediaForm(request.POST or None, request.FILES or None, instance=instance)
    if request.method == "POST" and form.is_valid():
        media = form.save(commit=False)
        media.vendor = vendor
        media.save()
        return redirect("admin-dashboard-storefront")
    return _render_form(request, form, "إضافة / تعديل وسائط المتجر")
