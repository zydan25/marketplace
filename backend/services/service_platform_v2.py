from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.text import slugify

from .models import Service, ServiceDistribution, TelecomPlan, TelecomPlanType
from .settings_models import ServiceSetting


PACKAGE_SERVICES = {
    "yemen-mobile": ("يمن موبايل", "yem-offer", "باقات يمن موبايل"),
    "sabafon": ("سبأفون", "saba-offer", "باقات سبأفون"),
    "sabafon-south": ("سبأفون الجنوب", "sbay-offer", "باقات سبأفون الجنوب"),
    "you": ("يو", "you-offer", "باقات يو"),
    "wai": ("واي", "why-package", "باقات واي"),
    "yemen4g": ("يمن فورجي", "yem4g-package", "باقات يمن فورجي"),
}


def staff_only(user):
    return bool(user.is_authenticated and (user.is_staff or getattr(user, "role", None) == "admin"))


def _service_rows():
    return (
        Service.objects.filter(is_active=True)
        .select_related("category__main_category")
        .exclude(service_kind=Service.ServiceKinds.QUERY)
        .order_by("category__main_category__sort_order", "category__sort_order", "sort_order", "id")
    )


def _canonical_settings():
    return ServiceSetting.objects.filter(is_system=True, is_active=True).select_related("service").order_by("group", "sort_order", "id")


@user_passes_test(staff_only, login_url="/admin/dashboard/login/")
def services_v2_home(request):
    package_cards = []
    for key, (label, code, setting_label) in PACKAGE_SERVICES.items():
        service = Service.objects.filter(code=code, is_active=True).select_related("category__main_category").first()
        setting = ServiceSetting.objects.filter(key=f"{('yemen_mobile' if code.startswith('yem') else key)}_packages", is_active=True).first()
        package_cards.append({"key": key, "label": label, "code": code, "title": setting_label, "service": service, "setting": setting})
    return render(
        request,
        "services/services_v2_home.html",
        {
            "package_cards": package_cards,
            "services": _service_rows(),
            "settings": _canonical_settings(),
            "query_services": Service.objects.filter(is_active=True, service_kind=Service.ServiceKinds.QUERY).select_related("category").order_by("name"),
        },
    )


@user_passes_test(staff_only, login_url="/admin/dashboard/login/")
def package_manager_v2(request, package_key):
    config = PACKAGE_SERVICES.get(package_key)
    if not config:
        return redirect("services-v2-home")
    provider_name, service_code, title = config
    service = get_object_or_404(Service.objects.select_related("category__main_category"), code=service_code, is_active=True)
    if request.method == "POST":
        action = request.POST.get("action")
        try:
            with transaction.atomic():
                if action == "save_type":
                    name = (request.POST.get("name") or "").strip()
                    if not name:
                        raise ValueError("اسم الفئة مطلوب.")
                    code = slugify(name, allow_unicode=True)[:80]
                    parent = TelecomPlanType.objects.filter(pk=request.POST.get("parent") or 0, service=service).first()
                    obj, _ = TelecomPlanType.objects.update_or_create(
                        service=service,
                        code=code,
                        defaults={"name": name, "parent": parent, "description": (request.POST.get("description") or "").strip(), "is_active": True},
                    )
                    if parent:
                        obj.plans.clear()
                    messages.success(request, "تم حفظ تصنيف الباقة.")
                elif action == "toggle_type":
                    obj = get_object_or_404(TelecomPlanType, pk=request.POST.get("pk"), service=service)
                    obj.is_active = not obj.is_active
                    obj.save(update_fields=["is_active"])
                elif action == "save_plan":
                    external_code = (request.POST.get("external_code") or "").strip()
                    name = (request.POST.get("name") or "").strip()
                    if not external_code or not name:
                        raise ValueError("كود المزود واسم الباقة مطلوبان.")
                    price = request.POST.get("price") or "0"
                    plan, _ = TelecomPlan.objects.update_or_create(
                        service=service,
                        external_code=external_code,
                        defaults={
                            "name": name,
                            "price": price,
                            "payment_type": (request.POST.get("payment_type") or "").strip(),
                            "line_type": (request.POST.get("line_type") or "").strip(),
                            "quota": request.POST.get("quota") or None,
                            "quota_unit": (request.POST.get("quota_unit") or "").strip(),
                            "validity_days": int(request.POST.get("validity_days")) if (request.POST.get("validity_days") or "").isdigit() else None,
                            "metadata": {"source": "services-v2", "provider_operation": "offeryem" if service.code == "yem-offer" else service.code},
                            "is_active": True,
                        },
                    )
                    type_ids = [int(x) for x in request.POST.getlist("type_ids") if str(x).isdigit()]
                    plan.plan_types.set(TelecomPlanType.objects.filter(service=service, pk__in=type_ids, is_active=True))
                    messages.success(request, "تم حفظ الباقة وربطها بتصنيفاتها.")
                elif action == "toggle_plan":
                    plan = get_object_or_404(TelecomPlan, pk=request.POST.get("pk"), service=service)
                    plan.is_active = not plan.is_active
                    plan.save(update_fields=["is_active"])
                else:
                    raise ValueError("عملية غير معروفة.")
        except Exception as exc:
            messages.error(request, f"تعذر حفظ التغيير: {exc}")
        return redirect(request.path)

    plans = TelecomPlan.objects.filter(service=service).prefetch_related("plan_types").order_by("sort_order", "id")
    types = TelecomPlanType.objects.filter(service=service, is_active=True).select_related("parent").prefetch_related("children").order_by("sort_order", "id")
    root_types = types.filter(parent__isnull=True)
    return render(
        request,
        "services/package_manager_v2.html",
        {
            "package_key": package_key,
            "provider_name": provider_name,
            "title": title,
            "service": service,
            "plans": plans,
            "types": types,
            "root_types": root_types,
        },
    )


@user_passes_test(staff_only, login_url="/admin/dashboard/login/")
def settings_v2(request):
    if request.method == "POST":
        try:
            key = (request.POST.get("key") or "").strip()
            setting = get_object_or_404(ServiceSetting, key=key, is_system=True)
            service = get_object_or_404(Service, pk=request.POST.get("service"), is_active=True)
            setting.service = service
            setting.save(update_fields=["service", "updated_at"])
            messages.success(request, f"تم ربط {setting.name} بالخدمة: {service.name}.")
        except Exception as exc:
            messages.error(request, f"تعذر حفظ الإعداد: {exc}")
        return redirect(request.path)
    return render(request, "services/service_settings_v2.html", {"settings": _canonical_settings(), "services": _service_rows()})


@user_passes_test(staff_only, login_url="/admin/dashboard/login/")
def integration_docs_v2(request):
    return render(request, "services/service_integration_v2.html")
