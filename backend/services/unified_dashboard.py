from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from django.shortcuts import redirect, render

from . import views as core
from .models import DigitalProduct, GameProduct, Service, TelecomDenomination, TelecomPlan


SCOPE_TO_CATEGORY = {
    "yemen-mobile": "yemen-mobile",
    "you": "you",
    "sabafon": "sabafon",
    "why": "why",
    "yemen-4g": "yemen-4g",
    "yemen-net": "yemen-net",
    "adenet": "adenet",
}


def _scope(value):
    value = (value or "").strip().lower()
    return SCOPE_TO_CATEGORY.get(value, value if value in {"games", "software", "digital-cards"} else "")


def _validate_resource_post(request):
    action = request.POST.get("action")
    if action not in {"telecom_denom", "telecom_plan", "game", "digital"}:
        return
    service = Service.objects.select_related("category__main_category").filter(pk=request.POST.get("service"), is_active=True).first()
    if not service:
        raise ValueError("الخدمة المحددة غير متاحة.")
    main_slug = service.category.main_category.slug
    category_slug = service.category.slug
    scope = _scope(request.POST.get("scope"))
    if action in {"telecom_denom", "telecom_plan"}:
        if main_slug != "payments":
            raise ValueError("فئات وباقات الاتصالات لا تُضاف إلا لخدمات قسم التسديدات.")
        if scope and category_slug != scope:
            raise ValueError("الخدمة المختارة لا تنتمي إلى الشركة المطلوبة.")
    elif action == "game" and main_slug != "games":
        raise ValueError("فئات الألعاب لا تُضاف إلا إلى خدمة لعبة داخل قسم الألعاب.")
    elif action == "digital" and main_slug != "software":
        raise ValueError("البطاقات الرقمية لا تُضاف إلا داخل قسم البرامج والبطاقات.")


def _filter_context(ctx, request):
    kind = (request.GET.get("kind") or "").strip().lower()
    company = _scope(request.GET.get("company"))
    if kind == "plan":
        plans = ctx["plans"]
        ctx["plans"] = plans.filter(service__category__slug=company) if company else plans
    elif kind == "denom":
        denoms = ctx["denoms"]
        ctx["denoms"] = denoms.filter(service__category__slug=company) if company else denoms
    elif kind == "game":
        ctx["games"] = ctx["games"].filter(service__category__main_category__slug="games")
    elif kind == "digital":
        ctx["digital"] = ctx["digital"].filter(service__category__main_category__slug="software")
    return ctx


@user_passes_test(core.staff_only, login_url="/admin/dashboard/login/")
def dashboard(request):
    if request.method == "POST":
        try:
            _validate_resource_post(request)
            core._post_action(request)
            messages.success(request, "تم حفظ التغييرات بنجاح.")
        except Exception as exc:
            messages.error(request, f"تعذر الحفظ: {exc}")
        return redirect(request.POST.get("next") or "admin-dashboard-services")
    return render(request, "services/dashboard.html", core._context("overview", request))


@user_passes_test(core.staff_only, login_url="/admin/dashboard/login/")
def section_view(request, section):
    if request.method == "POST":
        try:
            _validate_resource_post(request)
            core._post_action(request)
        except Exception as exc:
            messages.error(request, f"تعذر الحفظ: {exc}")
        return redirect(request.POST.get("next") or request.path)
    ctx = _filter_context(core._context(section, request), request)
    return render(request, "services/dashboard.html", ctx)
