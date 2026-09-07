from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.text import slugify

from .admin_v4 import FIELD_LIBRARY
from .models import Service, ServiceCategory, ServiceField


FIELD_MAP = {key: (label, field_type) for key, label, field_type in FIELD_LIBRARY}


def staff_only(user):
    return bool(user.is_authenticated and (user.is_staff or getattr(user, "role", None) == "admin"))


def dec(value, default="0"):
    raw = value if value not in (None, "") else default
    try:
        return Decimal(str(raw))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise ValueError("القيمة المالية غير صالحة.") from exc


@user_passes_test(staff_only, login_url="/admin/dashboard/login/")
def services(request):
    if request.method == "POST":
        try:
            service = Service.objects.filter(pk=request.POST.get("pk") or 0).first() or Service()
            service.category = get_object_or_404(ServiceCategory, pk=request.POST.get("category"))
            service.name = (request.POST.get("name") or "").strip()
            service.code = (request.POST.get("code") or "").strip()
            if not service.name or not service.code:
                raise ValueError("اسم الخدمة وكودها مطلوبان.")
            service.slug = (request.POST.get("slug") or slugify(service.name, allow_unicode=True)).strip()
            service.description = (request.POST.get("description") or "").strip()
            service.service_kind = request.POST.get("service_kind", Service.ServiceKinds.PURCHASE)
            service.requires_balance = request.POST.get("requires_balance") == "1"
            service.pricing_mode = request.POST.get("pricing_mode", Service.PricingModes.FIXED)
            service.price = dec(request.POST.get("price"))
            service.min_amount = dec(request.POST.get("min_amount"), "") if request.POST.get("min_amount") else None
            service.max_amount = dec(request.POST.get("max_amount"), "") if request.POST.get("max_amount") else None
            service.currency = (request.POST.get("currency") or "YER").strip().upper()
            service.icon = (request.POST.get("icon") or "").strip()
            service.sort_order = int(request.POST.get("sort_order", 0) or 0)
            metadata = dict(service.metadata or {})
            for key in ("service_number", "price_usd", "price_sar", "employee_price", "submit_label", "unified_link_number"):
                metadata[key] = (request.POST.get(key) or "").strip()
            metadata["duplicate_guard"] = request.POST.get("duplicate_guard") == "1"
            service.metadata = metadata
            service.is_active = True
            service.save()

            selected = {key for key in request.POST.getlist("field_keys") if key in FIELD_MAP}
            for index, (key, label, field_type) in enumerate(FIELD_LIBRARY):
                if key in selected:
                    ServiceField.objects.update_or_create(
                        service=service,
                        key=key,
                        defaults={
                            "label": label,
                            "field_type": field_type,
                            "required": request.POST.get(f"required_{key}") == "1",
                            "sort_order": index * 10,
                            "is_active": True,
                        },
                    )
            ServiceField.objects.filter(service=service, key__in=FIELD_MAP).exclude(key__in=selected).update(is_active=False)
            messages.success(request, f"تم حفظ الخدمة: {service.name} والحقول الخاصة بها.")
        except (ValueError, InvalidOperation) as exc:
            messages.error(request, str(exc))
        except Exception as exc:
            messages.error(request, f"تعذر حفظ الخدمة: {exc}")
        return redirect(f"{request.path}?edit={request.POST.get('pk', '')}" if request.POST.get("pk") else request.path)

    services_qs = Service.objects.select_related("category__main_category").prefetch_related("fields").order_by("category__main_category__sort_order", "category__sort_order", "sort_order", "id")
    categories = ServiceCategory.objects.select_related("main_category", "parent").filter(is_active=True).order_by("main_category__sort_order", "sort_order", "id")
    edit_service = services_qs.filter(pk=request.GET.get("edit") or 0).first()
    active_field_keys = {f.key for f in edit_service.fields.all() if f.is_active} if edit_service else set()
    return render(request, "services/services_v6.html", {
        "services": services_qs,
        "categories": categories,
        "edit_service": edit_service,
        "active_field_keys": active_field_keys,
        "field_library": FIELD_LIBRARY,
    })
