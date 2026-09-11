from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.text import slugify

from .models import Service, ServiceDistribution, TelecomPlan, TelecomPlanType
from .settings_admin import settings_center
from .settings_models import ServiceSetting
from .yemen_mobile_catalog_sync import sync_yemen_mobile_catalog


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


def _all_services():
    return Service.objects.filter(is_active=True).select_related("category__main_category").order_by("category__main_category__sort_order", "category__sort_order", "sort_order", "id")


def _canonical_settings():
    return ServiceSetting.objects.filter(is_system=True, is_active=True).select_related("service").order_by("group", "sort_order", "id")


def _as_optional_number(value):
    value = (value or "").strip()
    return value or None


def _plan_form_data(plan):
    benefits = dict((plan.metadata or {}).get("benefits") or {})
    return {
        "id": plan.id,
        "external_code": plan.external_code,
        "name": plan.name,
        "price": plan.price,
        "payment_type": plan.payment_type,
        "line_type": plan.line_type,
        "validity_days": plan.validity_days,
        "internet_amount": benefits.get("internet_amount") or plan.quota or "",
        "internet_unit": benefits.get("internet_unit") or plan.quota_unit or "",
        "voice_minutes": benefits.get("voice_minutes") or "",
        "sms_count": benefits.get("sms_count") or "",
        "technology": benefits.get("technology") or "",
        "quota": plan.quota or "",
        "quota_unit": plan.quota_unit or "",
        "type_ids": list(plan.plan_types.values_list("id", flat=True)),
    }


@user_passes_test(staff_only, login_url="/admin/dashboard/login/")
def services_v2_home(request):
    package_cards = []
    for key, (label, code, setting_label) in PACKAGE_SERVICES.items():
        service = Service.objects.filter(code=code, is_active=True).select_related("category__main_category").first()
        setting = ServiceSetting.objects.filter(
            key=("yemen_mobile_packages" if key == "yemen-mobile" else f"{key.replace('-', '_')}_packages"),
            is_active=True,
        ).first()
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

    edit_plan = None
    edit_id = request.GET.get("edit")
    if edit_id:
        edit_plan = get_object_or_404(TelecomPlan.objects.prefetch_related("plan_types"), pk=edit_id, service=service, is_active=True)

    if request.method == "POST":
        action = request.POST.get("action")
        try:
            with transaction.atomic():
                if action == "sync_catalog":
                    result = sync_yemen_mobile_catalog(service)
                    messages.success(
                        request,
                        f"تم تحديث الكتالوج: {result['created_plans']} باقة، من أصل {result['expected_source_rows']} صفًا، وأسعار صفرية: {result['zero_price']}."
                    )

                elif action == "save_type":
                    name = (request.POST.get("name") or "").strip()
                    if not name:
                        raise ValueError("اسم الفئة مطلوب.")
                    code = slugify(name, allow_unicode=True)[:80]
                    parent = TelecomPlanType.objects.filter(pk=request.POST.get("parent") or 0, service=service).first()
                    obj, _ = TelecomPlanType.objects.update_or_create(
                        service=service,
                        code=code,
                        defaults={
                            "name": name,
                            "parent": parent,
                            "description": (request.POST.get("description") or "").strip(),
                            "is_active": True,
                        },
                    )
                    messages.success(request, "تم حفظ تصنيف الباقة.")

                elif action == "toggle_type":
                    obj = get_object_or_404(TelecomPlanType, pk=request.POST.get("pk"), service=service)
                    obj.is_active = not obj.is_active
                    obj.save(update_fields=["is_active"])

                elif action == "delete_type":
                    obj = get_object_or_404(TelecomPlanType, pk=request.POST.get("pk"), service=service)
                    obj.plans.clear()
                    obj.children.update(parent=None)
                    obj.delete()
                    messages.success(request, "تم حذف التصنيف.")

                elif action == "save_plan":
                    plan_pk = (request.POST.get("plan_pk") or "").strip()
                    external_code = (request.POST.get("external_code") or "").strip()
                    name = (request.POST.get("name") or "").strip()
                    if not external_code or not name:
                        raise ValueError("كود المزود واسم الباقة مطلوبان.")
                    price = request.POST.get("price") or "0"
                    existing = TelecomPlan.objects.filter(service=service, external_code=external_code).first()
                    if plan_pk:
                        plan = get_object_or_404(TelecomPlan, pk=plan_pk, service=service)
                        collision = TelecomPlan.objects.filter(service=service, external_code=external_code).exclude(pk=plan.pk).exists()
                        if collision:
                            raise ValueError("كود المزود مستخدم بالفعل في باقة أخرى.")
                        metadata = dict(plan.metadata or {})
                    else:
                        if existing:
                            plan = existing
                            metadata = dict(existing.metadata or {})
                        else:
                            plan = TelecomPlan(service=service)
                            metadata = {}

                    benefits = dict(metadata.get("benefits") or {})
                    benefits.update({
                        "internet_amount": _as_optional_number(request.POST.get("internet_amount")),
                        "internet_unit": (request.POST.get("internet_unit") or "").strip() or None,
                        "voice_minutes": _as_optional_number(request.POST.get("voice_minutes")),
                        "sms_count": _as_optional_number(request.POST.get("sms_count")),
                        "technology": (request.POST.get("technology") or "").strip() or None,
                    })
                    metadata.update({
                        "benefits": benefits,
                        "source": "services-v2",
                        "provider_operation": "offeryem" if service.code == "yem-offer" else service.code,
                        "purchaseable": True,
                    })
                    plan.name = name
                    plan.external_code = external_code
                    plan.price = price
                    plan.payment_type = (request.POST.get("payment_type") or "").strip()
                    plan.line_type = (request.POST.get("line_type") or "").strip()
                    plan.quota = request.POST.get("quota") or benefits.get("internet_amount") or None
                    plan.quota_unit = (request.POST.get("quota_unit") or benefits.get("internet_unit") or "").strip()
                    plan.validity_days = int(request.POST.get("validity_days")) if (request.POST.get("validity_days") or "").isdigit() else None
                    plan.metadata = metadata
                    plan.is_active = True
                    plan.save()
                    type_ids = [int(x) for x in request.POST.getlist("type_ids") if str(x).isdigit()]
                    plan.plan_types.set(TelecomPlanType.objects.filter(service=service, pk__in=type_ids, is_active=True))
                    messages.success(request, "تم حفظ الباقة وتحديث جميع بياناتها.")

                elif action == "delete_plan":
                    plan = get_object_or_404(TelecomPlan, pk=request.POST.get("pk"), service=service)
                    plan.is_active = False
                    metadata = dict(plan.metadata or {})
                    metadata["removed_from_catalog"] = True
                    plan.metadata = metadata
                    plan.save(update_fields=["is_active", "metadata", "updated_at"])
                    plan.plan_types.clear()
                    messages.success(request, "تم حذف الباقة من الكتالوج وإخفاؤها من القائمة.")

                elif action == "toggle_plan":
                    plan = get_object_or_404(TelecomPlan, pk=request.POST.get("pk"), service=service)
                    plan.is_active = not plan.is_active
                    plan.save(update_fields=["is_active", "updated_at"])
                    if not plan.is_active:
                        plan.plan_types.clear()

                else:
                    raise ValueError("عملية غير معروفة.")
        except Exception as exc:
            messages.error(request, f"تعذر حفظ التغيير: {exc}")
        return redirect(request.path)

    plans = TelecomPlan.objects.filter(service=service, is_active=True).prefetch_related("plan_types").order_by("sort_order", "id")
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
            "edit_plan": _plan_form_data(edit_plan) if edit_plan else None,
        },
    )


@user_passes_test(staff_only, login_url="/admin/dashboard/login/")
def settings_v2(request):
    # Keep /v2/settings/ compatible with the original settings center so the
    # administrator can create a key/name/group, choose service/text/JSON/
    # boolean type, assign a real Service or standalone value, toggle, edit,
    # and delete custom settings.
    return settings_center(request)


@user_passes_test(staff_only, login_url="/admin/dashboard/login/")
def integration_docs_v2(request):
    return render(request, "services/service_integration_v2.html")
