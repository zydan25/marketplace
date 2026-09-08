from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from django.db import transaction
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.text import slugify

from .admin_v4 import staff_only
from .models import (
    DigitalProduct,
    GameProduct,
    Service,
    ServiceField,
    ServiceOption,
    TelecomDenomination,
    TelecomPlan,
    TelecomPlanType,
)

RESOURCE_META = {
    "plan": (TelecomPlan, "باقة", "الباقات"),
    "denom": (TelecomDenomination, "فئة", "الفئات"),
    "game": (GameProduct, "فئة لعبة", "الألعاب"),
    "digital": (DigitalProduct, "بطاقة / برنامج", "البطاقات والبرامج"),
    "option": (ServiceOption, "فئة / خيار", "الفئات"),
}

PAYMENT_CHOICES = (
    ("", "غير محدد"),
    ("prepaid", "دفع مسبق"),
    ("postpaid", "فوترة"),
    ("both", "كليهما"),
    ("paid", "مدفوع / تشغيلي"),
)
LINE_CHOICES = (
    ("", "غير محدد"),
    ("شريحة", "شريحة"),
    ("برمجة", "برمجة"),
    ("شريحة + برمجة", "شريحة + برمجة"),
)

DEFAULT_TYPE_NAMES = (
    ("bundle-3g", "3G"),
    ("bundle-4g", "4G"),
    ("bundle-volte", "VoLTE"),
    ("bundle-calls", "اتصال"),
    ("bundle-sim-internet", "إنترنت شريحة"),
    ("bundle-general", "عام"),
)


def _service_kind(service):
    text = " ".join(
        str(value or "")
        for value in (
            service.name,
            service.code,
            getattr(service.category, "name", ""),
            getattr(service.category, "slug", ""),
            getattr(service.category.main_category, "name", "") if service.category_id else "",
        )
    ).lower()
    if any(key in text for key in ("ألعاب", "العاب", "game", "games", "بطاق", "بطائق", "digital", "software")):
        return "entertainment"
    if any(key in text for key in ("اتصال", "mobile", "شريحة", "يمن", "سبأفون", "سبأ", "you", "يو", "واي", "telecom")):
        return "telecom"
    return "other"


def _services_with_counts():
    return (
        Service.objects.select_related("category__main_category")
        .annotate(
            plan_count=Count("telecom_plans", distinct=True),
            denom_count=Count("telecom_denominations", distinct=True),
            game_count=Count("game_products", distinct=True),
            digital_count=Count("digital_products", distinct=True),
            option_count=Count("options", distinct=True),
        )
        .filter(is_active=True)
        .order_by("category__main_category__sort_order", "category__sort_order", "sort_order", "id")
    )


def _sidebar(services):
    telecom, entertainment, other = [], [], []
    for service in services:
        row = {
            "id": service.id,
            "name": service.name,
            "short_name": service.name.replace(" - باقات", "").replace(" - فئات", ""),
            "full_name": service.name,
            "code": service.code,
            "plan_count": getattr(service, "plan_count", 0),
            "denom_count": getattr(service, "denom_count", 0),
        }
        bucket = _service_kind(service)
        (telecom if bucket == "telecom" else entertainment if bucket == "entertainment" else other).append(row)
    return telecom, entertainment, other


def _ensure_plan_types(service):
    if not service or _service_kind(service) != "telecom":
        return []
    is_yemen_mobile = service.code.startswith("yem-") or getattr(service.category, "slug", "") == "yemen-mobile"
    definitions = DEFAULT_TYPE_NAMES if is_yemen_mobile else (("bundle-general", "عام"),)
    created = []
    for code, name in definitions:
        obj, _ = TelecomPlanType.objects.get_or_create(
            service=service,
            code=code,
            defaults={"name": name, "description": "تصنيف يدوي للباقات" if code != "bundle-general" else "تصنيف عام", "sort_order": len(created)},
        )
        if obj.name != name:
            obj.name = name
            obj.save(update_fields=["name"])
        created.append(obj)
    return created


def _guess_plan_type(plan):
    text = f"{plan.name} {getattr(plan, 'metadata', {})}".lower()
    if any(key in text for key in ("volte", "فولت") ):
        return "bundle-volte"
    if any(key in text for key in ("4g", "فورجي")):
        return "bundle-4g"
    if any(key in text for key in ("مودم انترنت شريحة", "انترنت شريحة")):
        return "bundle-sim-internet"
    if any(key in text for key in ("اتصال", "مكالم", "دقائق", "صوت")):
        return "bundle-calls"
    if any(key in text for key in ("3g", "3 جي", "evdo", "1x")):
        return "bundle-3g"
    return "bundle-general"


def _ensure_inferred_type(plan, types):
    if not types or plan.plan_types.filter(code__startswith="bundle-").exists():
        return None
    target_code = _guess_plan_type(plan)
    target = next((item for item in types if item.code == target_code), types[-1])
    plan.plan_types.add(target)
    return target


def _save_resource(request, kind, service):
    model = RESOURCE_META[kind][0]
    pk = (request.POST.get("pk") or "").strip()
    obj = model.objects.filter(pk=pk).first() if pk else None
    if obj is not None and obj.service_id != service.id:
        raise ValueError("العنصر المطلوب تعديله لا يتبع الخدمة المحددة.")
    if obj is None:
        obj = model(service=service)

    obj.service = service
    obj.name = (request.POST.get("name") or "").strip()
    if not obj.name:
        raise ValueError("اسم العنصر مطلوب.")
    obj.external_code = (request.POST.get("external_code") or "").strip()
    if kind in {"plan", "denom", "game"} and not obj.external_code:
        raise ValueError("الكود الخارجي / كود الربط مطلوب.")
    obj.sort_order = max(0, int(request.POST.get("sort_order", 0) or 0))
    obj.is_active = request.POST.get("is_active", "1") == "1"

    if kind == "plan":
        raw_price = request.POST.get("price") or "0"
        obj.price = raw_price
        quota = request.POST.get("quota")
        obj.quota = quota if quota not in (None, "") else None
        obj.quota_unit = (request.POST.get("quota_unit") or "").strip()
        obj.validity_days = int(request.POST["validity_days"]) if request.POST.get("validity_days") else None
        obj.payment_type = (request.POST.get("payment_type") or "").strip()
        obj.line_type = (request.POST.get("line_type") or "").strip()
        meta = dict(obj.metadata or {})
        for key in ("provider_num", "package_number", "price_usd", "price_sar", "employee_price"):
            value = (request.POST.get(key) or "").strip()
            if value:
                meta[key] = value
            elif key in meta:
                meta.pop(key, None)
        obj.metadata = meta
    elif kind == "denom":
        obj.face_value = request.POST.get("face_value") or "0"
        obj.sale_price = request.POST.get("sale_price") or "0"
        obj.payment_type = (request.POST.get("payment_type") or "").strip()
        obj.line_type = (request.POST.get("line_type") or "").strip()
        meta = dict(obj.metadata or {})
        for key in ("provider_num", "price_usd", "price_sar", "employee_price"):
            value = (request.POST.get(key) or "").strip()
            if value:
                meta[key] = value
            elif key in meta:
                meta.pop(key, None)
        obj.metadata = meta
    elif kind == "game":
        obj.price = request.POST.get("price") or "0"
        obj.currency = (request.POST.get("currency") or "YER").strip().upper()
        meta = dict(obj.metadata or {})
        meta["validity_days"] = int(request.POST["validity_days"]) if request.POST.get("validity_days") else None
        meta["details"] = (request.POST.get("details") or "").strip()
        meta["employee_price"] = (request.POST.get("employee_price") or "").strip()
        obj.metadata = meta
    elif kind == "digital":
        obj.price = request.POST.get("price") or "0"
        obj.currency = (request.POST.get("currency") or "YER").strip().upper()
        obj.validity_days = int(request.POST["validity_days"]) if request.POST.get("validity_days") else None
        meta = dict(obj.metadata or {})
        meta["details"] = (request.POST.get("details") or "").strip()
        meta["employee_price"] = (request.POST.get("employee_price") or "").strip()
        obj.metadata = meta
    else:
        obj.provider_num = (request.POST.get("provider_num") or "").strip()
        obj.price = request.POST.get("price") or "0"
        obj.currency = (request.POST.get("currency") or "YER").strip().upper()
        meta = dict(obj.metadata or {})
        meta["details"] = (request.POST.get("details") or "").strip()
        meta["employee_price"] = (request.POST.get("employee_price") or "").strip()
        obj.metadata = meta

    obj.save()

    if kind == "plan":
        type_id = (request.POST.get("plan_type") or "").strip()
        if type_id.isdigit():
            selected_type = TelecomPlanType.objects.filter(pk=type_id, service=service, is_active=True, code__startswith="bundle-").first()
            if selected_type:
                obj.plan_types.remove(*obj.plan_types.filter(code__startswith="bundle-"))
                obj.plan_types.add(selected_type)
    return obj


@user_passes_test(staff_only, login_url="/admin/dashboard/login/")
def dashboard_resources(request, type=None):
    mode = (type or request.GET.get("type") or request.POST.get("type") or "plan").strip().lower()
    if mode not in {"plan", "denom", "entertainment"}:
        mode = "plan"

    services = list(_services_with_counts())
    telecom_services, entertainment_services, other_services = _sidebar(services)
    selected_service_id = (request.GET.get("service") or request.POST.get("service") or "").strip()
    service_code = (request.GET.get("service_code") or request.POST.get("service_code") or "").strip()
    if service_code and not selected_service_id:
        matched = next((s for s in services if s.code == service_code), None)
        if matched:
            selected_service_id = str(matched.id)

    selected_service = next((s for s in services if str(s.id) == str(selected_service_id)), None)
    if selected_service is None and selected_service_id.isdigit():
        selected_service = Service.objects.filter(pk=selected_service_id, is_active=True).select_related("category__main_category").first()

    if request.method == "POST":
        try:
            with transaction.atomic():
                action = request.POST.get("action", "save")
                if action == "create_type":
                    service = get_object_or_404(Service, pk=request.POST.get("service"), is_active=True)
                    name = (request.POST.get("type_name") or "").strip()
                    if not name:
                        raise ValueError("اسم نوع الباقة مطلوب.")
                    code_base = slugify(name, allow_unicode=False) or f"type-{service.id}"
                    code = f"bundle-{code_base}"[:80]
                    suffix = 2
                    while TelecomPlanType.objects.filter(service=service, code=code).exists():
                        tail = f"-{suffix}"
                        code = f"bundle-{code_base[:80-len(tail)]}{tail}"
                        suffix += 1
                    TelecomPlanType.objects.create(service=service, code=code, name=name, description="تصنيف مخصص للباقات", sort_order=TelecomPlanType.objects.filter(service=service).count(), is_active=True)
                    messages.success(request, f"تمت إضافة نوع الباقة: {name}.")
                elif action == "toggle":
                    kind = request.POST.get("subtype") or ("game" if mode == "entertainment" else mode)
                    model = RESOURCE_META.get(kind, (None,))[0]
                    if not model:
                        raise ValueError("نوع المورد غير صالح.")
                    obj = get_object_or_404(model, pk=request.POST.get("pk"))
                    obj.is_active = not obj.is_active
                    obj.save(update_fields=["is_active"])
                    messages.success(request, f"تم تحديث حالة: {obj.name}.")
                else:
                    kind = mode
                    if kind == "entertainment":
                        kind = (request.POST.get("subtype") or "game").strip().lower()
                        if kind not in {"game", "digital", "option"}:
                            raise ValueError("نوع العنصر غير صالح.")
                    else:
                        if kind not in {"plan", "denom"}:
                            raise ValueError("نوع المورد غير صالح.")
                    service = get_object_or_404(Service, pk=request.POST.get("service"), is_active=True)
                    _ensure_plan_types(service)
                    _save_resource(request, kind, service)
                    messages.success(request, f"تم حفظ العنصر ضمن: {service.name}.")
                    selected_service_id = str(service.id)
        except Exception as exc:
            messages.error(request, f"تعذر الحفظ: {exc}")
        return redirect(f"{request.path}?type={mode}&service={selected_service_id}")

    q = (request.GET.get("q") or "").strip()
    payment_filter = (request.GET.get("payment_type") or "").strip()
    line_filter = (request.GET.get("line_type") or "").strip()
    selected_type_id = (request.GET.get("plan_type") or "").strip()

    plan_types = []
    if selected_service and _service_kind(selected_service) == "telecom":
        plan_types = _ensure_plan_types(selected_service)
        plans_without_type = TelecomPlan.objects.filter(service=selected_service).prefetch_related("plan_types")
        for plan in plans_without_type:
            _ensure_inferred_type(plan, plan_types)

    fields = ServiceField.objects.filter(service_id=getattr(selected_service, "id", 0), is_active=True).order_by("sort_order", "id") if selected_service else ServiceField.objects.none()

    edit_obj = None
    edit_resource_kind = (request.GET.get("edit_kind") or "").strip().lower()
    edit_pk = request.GET.get("edit") or ""
    if edit_pk and edit_resource_kind in RESOURCE_META:
        edit_obj = RESOURCE_META[edit_resource_kind][0].objects.filter(pk=edit_pk).select_related("service").first()
        if edit_obj:
            selected_service = edit_obj.service
            selected_service_id = str(edit_obj.service_id)
            if edit_resource_kind == "plan":
                plan_types = _ensure_plan_types(selected_service)

    items = []
    if mode == "plan":
        qs = TelecomPlan.objects.select_related("service").prefetch_related("plan_types").filter(is_active=True)
        if selected_service:
            qs = qs.filter(service=selected_service)
        if selected_type_id.isdigit() and selected_service:
            qs = qs.filter(plan_types__id=selected_type_id)
        if payment_filter:
            qs = qs.filter(payment_type=payment_filter)
        if line_filter:
            qs = qs.filter(line_type=line_filter)
        if q:
            qs = qs.filter(Q(name__icontains=q) | Q(external_code__icontains=q) | Q(service__name__icontains=q))
        items = list(qs.distinct().order_by("service__name", "sort_order", "id"))
    elif mode == "denom":
        qs = TelecomDenomination.objects.select_related("service").filter(is_active=True)
        if selected_service:
            qs = qs.filter(service=selected_service)
        if payment_filter:
            qs = qs.filter(payment_type=payment_filter)
        if line_filter:
            qs = qs.filter(line_type=line_filter)
        if q:
            qs = qs.filter(Q(name__icontains=q) | Q(external_code__icontains=q) | Q(service__name__icontains=q))
        items = list(qs.order_by("service__name", "sort_order", "id"))

    entertainment_items = []
    if mode == "entertainment":
        for kind, model, label in (("game", GameProduct, "لعبة"), ("digital", DigitalProduct, "برنامج / بطاقة"), ("option", ServiceOption, "فئة / خيار")):
            qs = model.objects.select_related("service").filter(service__is_active=True)
            if selected_service:
                qs = qs.filter(service=selected_service)
            if q:
                qs = qs.filter(Q(name__icontains=q) | Q(external_code__icontains=q) | Q(service__name__icontains=q))
            for obj in qs.order_by("service__name", "sort_order", "id"):
                entertainment_items.append({"kind": kind, "kind_label": label, "obj": obj})

    game_services = list(
        Service.objects.filter(is_active=True)
        .filter(Q(game_products__isnull=False) | Q(digital_products__isnull=False) | Q(options__isnull=False))
        .distinct().order_by("name")
    )

    return render(request, "services/resources_v11.html", {
        "mode": mode,
        "edit_obj": edit_obj,
        "edit_resource_kind": edit_resource_kind,
        "services": services,
        "telecom_services": telecom_services,
        "entertainment_services": entertainment_services,
        "other_services": other_services,
        "selected_service": selected_service,
        "selected_service_id": str(selected_service_id),
        "service_fields": fields,
        "plan_types": plan_types,
        "items": items,
        "entertainment_items": entertainment_items,
        "game_services": game_services,
        "query": q,
        "payment_filter": payment_filter,
        "line_filter": line_filter,
        "selected_type_id": str(selected_type_id),
        "payment_choices": PAYMENT_CHOICES,
        "line_choices": LINE_CHOICES,
    })
