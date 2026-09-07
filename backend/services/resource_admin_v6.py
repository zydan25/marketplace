from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
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


RESOURCE_TYPES = {
    "plan": {"model": TelecomPlan, "title": "الباقات", "singular": "باقة", "label": "اسم الباقة"},
    "denom": {"model": TelecomDenomination, "title": "الفئات والشرائح", "singular": "فئة / شريحة", "label": "اسم الفئة"},
    "game": {"model": GameProduct, "title": "فئات الألعاب", "singular": "فئة لعبة", "label": "اسم الفئة"},
    "digital": {"model": DigitalProduct, "title": "البرامج والمنتجات الرقمية", "singular": "منتج رقمي", "label": "اسم المنتج / البرنامج"},
    "option": {"model": ServiceOption, "title": "فئات وخيارات الخدمة", "singular": "خيار / فئة", "label": "اسم الفئة / الخيار"},
}


def staff_only(user):
    return bool(user.is_authenticated and (user.is_staff or getattr(user, "role", None) == "admin"))


def decimal_value(value, default="0"):
    raw = value if value not in (None, "") else default
    try:
        return Decimal(str(raw))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise ValueError("القيمة الرقمية غير صالحة.") from exc


def selected_type(request):
    value = (request.GET.get("type") or request.POST.get("type") or "plan").strip().lower()
    return value if value in RESOURCE_TYPES else "plan"


def service_queryset():
    return Service.objects.select_related("category__main_category").filter(is_active=True).prefetch_related("fields")


@user_passes_test(staff_only, login_url="/admin/dashboard/login/")
def resources(request):
    kind = selected_type(request)
    spec = RESOURCE_TYPES[kind]
    model = spec["model"]

    if request.method == "POST":
        try:
            service = get_object_or_404(Service, pk=request.POST.get("service"), is_active=True)
            pk = request.POST.get("pk") or ""
            obj = model.objects.filter(pk=pk).first() if pk else None
            if obj is not None and obj.service_id != service.id:
                raise ValueError("العنصر المطلوب تعديله غير تابع للخدمة المحددة.")
            if obj is None:
                obj = model(service=service)

            obj.service = service
            obj.name = (request.POST.get("name") or "").strip()
            if not obj.name:
                raise ValueError(f"{spec['label']} مطلوب.")
            obj.external_code = (request.POST.get("external_code") or "").strip()
            if kind in {"plan", "denom", "game"} and not obj.external_code:
                raise ValueError("الكود الخارجي / كود الربط مطلوب.")
            obj.sort_order = int(request.POST.get("sort_order", 0) or 0)
            obj.is_active = True

            if kind == "plan":
                obj.price = decimal_value(request.POST.get("price"))
                obj.quota = decimal_value(request.POST.get("quota"), default="0") if request.POST.get("quota") else None
                obj.quota_unit = (request.POST.get("quota_unit") or "").strip()
                obj.validity_days = int(request.POST["validity_days"]) if request.POST.get("validity_days") else None
                obj.payment_type = (request.POST.get("payment_type") or "").strip()
                obj.line_type = (request.POST.get("line_type") or "").strip()
                meta = dict(obj.metadata or {})
                for key in ("provider_num", "package_number", "price_usd", "price_sar", "employee_price"):
                    meta[key] = (request.POST.get(key) or "").strip()
                obj.metadata = meta
            elif kind == "denom":
                obj.face_value = decimal_value(request.POST.get("face_value"))
                obj.sale_price = decimal_value(request.POST.get("sale_price"))
                obj.payment_type = (request.POST.get("payment_type") or "").strip()
                obj.line_type = (request.POST.get("line_type") or "").strip()
                meta = dict(obj.metadata or {})
                for key in ("provider_num", "price_usd", "price_sar", "employee_price"):
                    meta[key] = (request.POST.get(key) or "").strip()
                obj.metadata = meta
            elif kind == "game":
                obj.price = decimal_value(request.POST.get("price"))
                obj.currency = (request.POST.get("currency") or "YER").strip().upper()
                meta = dict(obj.metadata or {})
                meta["validity_days"] = int(request.POST["validity_days"]) if request.POST.get("validity_days") else None
                meta["details"] = (request.POST.get("details") or "").strip()
                meta["employee_price"] = (request.POST.get("employee_price") or "").strip()
                obj.metadata = meta
            elif kind == "digital":
                obj.price = decimal_value(request.POST.get("price"))
                obj.currency = (request.POST.get("currency") or "YER").strip().upper()
                obj.validity_days = int(request.POST["validity_days"]) if request.POST.get("validity_days") else None
                meta = dict(obj.metadata or {})
                meta["details"] = (request.POST.get("details") or "").strip()
                meta["employee_price"] = (request.POST.get("employee_price") or "").strip()
                obj.metadata = meta
            else:
                obj.provider_num = (request.POST.get("provider_num") or "").strip()
                obj.price = decimal_value(request.POST.get("price"))
                obj.currency = (request.POST.get("currency") or "YER").strip().upper()
                meta = dict(obj.metadata or {})
                meta["details"] = (request.POST.get("details") or "").strip()
                meta["employee_price"] = (request.POST.get("employee_price") or "").strip()
                obj.metadata = meta
            obj.save()
            messages.success(request, f"تم حفظ {spec['singular']} ضمن الخدمة: {service.name}.")
        except (ValueError, InvalidOperation) as exc:
            messages.error(request, str(exc))
        except Exception as exc:
            messages.error(request, f"تعذر الحفظ: {exc}")
        return redirect(f"{request.path}?type={kind}&service={request.POST.get('service', '')}")

    services = service_queryset()
    selected_service_id = request.GET.get("service") or (str(services[0].id) if services else "")
    selected_service = next((x for x in services if str(x.id) == str(selected_service_id)), None)
    edit_obj = model.objects.filter(pk=request.GET.get("edit") or 0).first()
    if edit_obj is not None:
        selected_service = edit_obj.service
        selected_service_id = str(edit_obj.service_id)

    queryset = model.objects.select_related("service").filter(service_id=selected_service_id).order_by("sort_order", "id") if selected_service_id else model.objects.none()
    fields = ServiceField.objects.filter(service_id=selected_service_id, is_active=True).order_by("sort_order", "id") if selected_service_id else ServiceField.objects.none()

    return render(request, "services/resources_v7.html", {
        "kind": kind,
        "spec": spec,
        "resource_types": RESOURCE_TYPES,
        "services": services,
        "selected_service": selected_service,
        "selected_service_id": selected_service_id,
        "edit_obj": edit_obj,
        "items": queryset,
        "service_fields": fields,
    })
