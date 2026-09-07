from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render

from .models import (
    DigitalProduct,
    GameProduct,
    Service,
    ServiceField,
    ServiceOption,
    TelecomDenomination,
    TelecomPlan,
)

TELECOM_KEYWORDS = (
    "اتصالات", "الاتصالات", "telecom", "mobile", "شبكات", "شريحة",
    "يمن", "سبأفون", "سبأ", "you", "يو", "واي", "yemen mobile",
)
ENTERTAINMENT_KEYWORDS = (
    "ألعاب", "العاب", "game", "games", "بطاقات", "بطائق", "بطاقة",
    "برامج", "رقمية", "digital", "software", "فري فاير", "free fire",
)
RESOURCE_META = {
    "plan": (TelecomPlan, "باقة", "باقات"),
    "denom": (TelecomDenomination, "فئة / شريحة", "فئات"),
    "game": (GameProduct, "فئة لعبة", "لعبة"),
    "digital": (DigitalProduct, "منتج رقمي", "برنامج / بطاقة"),
    "option": (ServiceOption, "فئة / بطاقة", "بطاقة / فئة"),
}


def staff_only(user):
    return bool(user.is_authenticated and (user.is_staff or getattr(user, "role", None) == "admin"))


def dec(value, default="0"):
    raw = value if value not in (None, "") else default
    try:
        return Decimal(str(raw))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise ValueError("القيمة الرقمية غير صالحة.") from exc


def _service_kind(service):
    text = " ".join(
        str(x or "")
        for x in (
            service.name,
            service.code,
            getattr(service.category, "name", ""),
            getattr(service.category.main_category, "name", "") if service.category_id else "",
        )
    ).lower()
    if any(k in text for k in ENTERTAINMENT_KEYWORDS):
        return "entertainment"
    if any(k in text for k in TELECOM_KEYWORDS):
        return "telecom"
    if getattr(service, "plan_count", 0) or getattr(service, "denom_count", 0):
        return "telecom"
    if getattr(service, "game_count", 0) or getattr(service, "digital_count", 0) or getattr(service, "option_count", 0):
        return "entertainment"
    return "other"


def _short_service_name(name):
    value = str(name or "").strip()
    for prefix in ("باقات ", "فئات ", "شرائح "):
        if value.lower().startswith(prefix.lower()):
            value = value[len(prefix):].strip()
            break
    return value or str(name or "")


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
        item = {
            "id": service.id,
            "name": _short_service_name(service.name),
            "full_name": service.name,
            "plan_count": getattr(service, "plan_count", 0),
            "denom_count": getattr(service, "denom_count", 0),
        }
        bucket = _service_kind(service)
        if bucket == "telecom":
            telecom.append(item)
        elif bucket == "entertainment":
            entertainment.append(item)
        else:
            other.append(item)
    return telecom, entertainment, other


def _save_resource(request, kind, service):
    model = RESOURCE_META[kind][0]
    pk = (request.POST.get("pk") or "").strip()
    obj = model.objects.filter(pk=pk).first() if pk else None
    if obj and obj.service_id != service.id:
        raise ValueError("العنصر المطلوب تعديله غير تابع للخدمة المحددة.")
    if obj is None:
        obj = model(service=service)

    obj.service = service
    obj.name = (request.POST.get("name") or "").strip()
    if not obj.name:
        raise ValueError("اسم الفئة مطلوب.")
    obj.external_code = (request.POST.get("external_code") or "").strip()
    if kind in {"plan", "denom", "game"} and not obj.external_code:
        raise ValueError("الكود الخارجي / كود الربط مطلوب.")
    obj.sort_order = int(request.POST.get("sort_order", 0) or 0)
    obj.is_active = request.POST.get("is_active", "1") == "1"

    if kind == "plan":
        obj.price = dec(request.POST.get("price"))
        obj.quota = dec(request.POST.get("quota")) if request.POST.get("quota") else None
        obj.quota_unit = (request.POST.get("quota_unit") or "").strip()
        obj.validity_days = int(request.POST["validity_days"]) if request.POST.get("validity_days") else None
        obj.payment_type = (request.POST.get("payment_type") or "").strip()
        obj.line_type = (request.POST.get("line_type") or "").strip()
        meta = dict(obj.metadata or {})
        for key in ("provider_num", "package_number", "price_usd", "price_sar", "employee_price"):
            meta[key] = (request.POST.get(key) or "").strip()
        obj.metadata = meta
    elif kind == "denom":
        obj.face_value = dec(request.POST.get("face_value"))
        obj.sale_price = dec(request.POST.get("sale_price"))
        obj.payment_type = (request.POST.get("payment_type") or "").strip()
        obj.line_type = (request.POST.get("line_type") or "").strip()
        meta = dict(obj.metadata or {})
        for key in ("provider_num", "price_usd", "price_sar", "employee_price"):
            meta[key] = (request.POST.get(key) or "").strip()
        obj.metadata = meta
    elif kind == "game":
        obj.price = dec(request.POST.get("price"))
        obj.currency = (request.POST.get("currency") or "YER").strip().upper()
        meta = dict(obj.metadata or {})
        meta["validity_days"] = int(request.POST["validity_days"]) if request.POST.get("validity_days") else None
        meta["details"] = (request.POST.get("details") or "").strip()
        meta["employee_price"] = (request.POST.get("employee_price") or "").strip()
        obj.metadata = meta
    elif kind == "digital":
        obj.price = dec(request.POST.get("price"))
        obj.currency = (request.POST.get("currency") or "YER").strip().upper()
        obj.validity_days = int(request.POST["validity_days"]) if request.POST.get("validity_days") else None
        meta = dict(obj.metadata or {})
        meta["details"] = (request.POST.get("details") or "").strip()
        meta["employee_price"] = (request.POST.get("employee_price") or "").strip()
        obj.metadata = meta
    elif kind == "option":
        obj.provider_num = (request.POST.get("provider_num") or "").strip()
        obj.price = dec(request.POST.get("price"))
        obj.currency = (request.POST.get("currency") or "YER").strip().upper()
        meta = dict(obj.metadata or {})
        meta["details"] = (request.POST.get("details") or "").strip()
        meta["employee_price"] = (request.POST.get("employee_price") or "").strip()
        obj.metadata = meta
    obj.save()
    return obj


def _toggle_resource(kind, pk):
    obj = get_object_or_404(RESOURCE_META[kind][0], pk=pk)
    obj.is_active = not obj.is_active
    obj.save(update_fields=["is_active"])
    return obj


@user_passes_test(staff_only, login_url="/admin/dashboard/login/")
def dashboard_resources(request, type=None):
    mode = (type or request.GET.get("type") or request.POST.get("type") or "plan").strip().lower()
    if mode not in {"plan", "denom", "entertainment"}:
        mode = "plan"

    services = _services_with_counts()
    telecom_services, entertainment_services, other_services = _sidebar(services)

    selected_service_id = request.GET.get("service") or request.POST.get("service") or ""
    service_code = (request.GET.get("service_code") or request.POST.get("service_code") or "").strip()
    if service_code and not selected_service_id:
        matched = services.filter(code=service_code).first()
        if matched:
            selected_service_id = str(matched.id)

    selected_service = (
        Service.objects.filter(pk=selected_service_id, is_active=True)
        .select_related("category__main_category")
        .first()
        if selected_service_id else None
    )

    if request.method == "POST":
        try:
            if request.POST.get("action") == "toggle":
                kind = request.POST.get("subtype") or ("game" if mode == "entertainment" else mode)
                if kind not in RESOURCE_META:
                    raise ValueError("نوع العنصر غير صالح.")
                obj = _toggle_resource(kind, request.POST.get("pk"))
                messages.success(request, f"تم تغيير حالة: {obj.name}.")
            elif mode == "entertainment":
                kind = (request.POST.get("subtype") or "game").strip().lower()
                if kind not in {"game", "digital", "option"}:
                    raise ValueError("نوع الفئة غير صالح.")
                service = get_object_or_404(Service, pk=request.POST.get("service"), is_active=True)
                _save_resource(request, kind, service)
                messages.success(request, f"تم حفظ الفئة ضمن الخدمة: {service.name}.")
                selected_service_id = str(service.id)
            else:
                service = get_object_or_404(Service, pk=request.POST.get("service"), is_active=True)
                _save_resource(request, mode, service)
                messages.success(request, f"تم حفظ العنصر ضمن الخدمة: {service.name}.")
                selected_service_id = str(service.id)
        except (ValueError, InvalidOperation) as exc:
            messages.error(request, str(exc))
        except Exception as exc:
            messages.error(request, f"تعذر الحفظ: {exc}")
        return redirect(f"{request.path}?type={mode}&service={selected_service_id}")

    fields = (
        ServiceField.objects.filter(service_id=selected_service_id, is_active=True).order_by("sort_order", "id")
        if selected_service_id else ServiceField.objects.none()
    )

    edit_obj = None
    edit_resource_kind = (request.GET.get("edit_kind") or "").strip().lower()
    edit_pk = request.GET.get("edit") or ""
    if edit_pk and edit_resource_kind in RESOURCE_META:
        candidate = RESOURCE_META[edit_resource_kind][0].objects.filter(pk=edit_pk).select_related("service").first()
        if candidate:
            edit_obj = candidate
            selected_service = candidate.service
            selected_service_id = str(candidate.service_id)
            fields = ServiceField.objects.filter(service=candidate.service, is_active=True).order_by("sort_order", "id")
    elif edit_pk:
        for kind in ("plan", "denom", "game", "digital", "option"):
            candidate = RESOURCE_META[kind][0].objects.filter(pk=edit_pk).select_related("service").first()
            if candidate:
                edit_obj = candidate
                edit_resource_kind = kind
                selected_service = candidate.service
                selected_service_id = str(candidate.service_id)
                fields = ServiceField.objects.filter(service=candidate.service, is_active=True).order_by("sort_order", "id")
                break

    items = []
    if mode == "plan" and selected_service_id:
        items = list(TelecomPlan.objects.filter(service_id=selected_service_id).select_related("service").order_by("sort_order", "id"))
    elif mode == "denom" and selected_service_id:
        items = list(TelecomDenomination.objects.filter(service_id=selected_service_id).select_related("service").order_by("sort_order", "id"))

    q = (request.GET.get("q") or "").strip()
    game_service_id = request.GET.get("game") or ""
    entertainment_items = []
    if mode == "entertainment":
        for kind, model, label in (
            ("game", GameProduct, "لعبة"),
            ("digital", DigitalProduct, "برنامج / بطاقة"),
            ("option", ServiceOption, "بطاقة / فئة"),
        ):
            qs = model.objects.select_related("service").filter(service__is_active=True)
            if game_service_id:
                qs = qs.filter(service_id=game_service_id)
            if q:
                qs = qs.filter(Q(name__icontains=q) | Q(external_code__icontains=q) | Q(service__name__icontains=q))
            for obj in qs.order_by("service__name", "sort_order", "id"):
                entertainment_items.append({"kind": kind, "kind_label": label, "obj": obj})
        entertainment_items.sort(key=lambda x: (str(x["obj"].service.name).lower(), x["obj"].sort_order, str(x["obj"].name).lower()))

    game_services = (
        Service.objects.filter(is_active=True)
        .filter(Q(game_products__isnull=False) | Q(digital_products__isnull=False) | Q(options__isnull=False))
        .distinct()
        .order_by("name")
    )

    return render(request, "services/resources_v10.html", {
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
        "items": items,
        "entertainment_items": entertainment_items,
        "game_services": game_services,
        "query": q,
        "selected_game": str(game_service_id),
    })
