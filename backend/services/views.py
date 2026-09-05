import json
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from django.db import transaction
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.text import slugify

from .accounting_bridge import ensure_service_accounts
from .models import DigitalProduct, GameProduct, MainServiceCategory, ProviderConnection, ProviderLink, Service, ServiceCategory, ServiceDistribution, ServiceField, ServiceTask, ServiceTransaction, TelecomDenomination, TelecomPlan


def staff_only(user):
    return bool(user.is_authenticated and (user.is_staff or getattr(user, "role", None) == "admin"))


def _json(value, fallback):
    if not value:
        return fallback
    try:
        return json.loads(value)
    except json.JSONDecodeError as exc:
        raise ValueError("JSON غير صالح.") from exc


def _required(data, name, label):
    value = (data.get(name) or "").strip()
    if not value:
        raise ValueError(f"{label} مطلوب.")
    return value


def _context():
    services = Service.objects.select_related("category__main_category").annotate(task_count=Count("transactions")).order_by("sort_order", "id")
    return {
        "mains": MainServiceCategory.objects.all(),
        "categories": ServiceCategory.objects.select_related("main_category", "parent").all(),
        "services": services,
        "fields": ServiceField.objects.select_related("service"),
        "providers": ProviderConnection.objects.all(),
        "links": ProviderLink.objects.select_related("provider"),
        "distributions": ServiceDistribution.objects.select_related("service", "provider_link"),
        "transactions": ServiceTransaction.objects.select_related("service", "customer").order_by("-created_at")[:50],
        "tasks": ServiceTask.objects.select_related("transaction__service", "provider_link").order_by("-id")[:60],
        "plans": TelecomPlan.objects.select_related("service"),
        "denoms": TelecomDenomination.objects.select_related("service"),
        "games": GameProduct.objects.select_related("service"),
        "digital": DigitalProduct.objects.select_related("service"),
        "stats": {
            "main": MainServiceCategory.objects.filter(is_active=True).count(),
            "categories": ServiceCategory.objects.filter(is_active=True).count(),
            "services": Service.objects.filter(is_active=True).count(),
            "providers": ProviderConnection.objects.filter(is_active=True).count(),
            "queued": ServiceTask.objects.filter(status__in=[ServiceTask.Statuses.QUEUED, ServiceTask.Statuses.RETRY]).count(),
        },
    }


def _post_action(request):
    action = request.POST.get("action")
    with transaction.atomic():
        if action == "main":
            MainServiceCategory.objects.update_or_create(slug=_required(request.POST, "slug", "المعرف"), defaults={"name": _required(request.POST, "name", "الاسم"), "icon": request.POST.get("icon", ""), "sort_order": int(request.POST.get("sort_order", 0) or 0), "description": request.POST.get("description", "")})
        elif action == "category":
            main = get_object_or_404(MainServiceCategory, pk=request.POST.get("main_category"))
            parent = ServiceCategory.objects.filter(pk=request.POST.get("parent") or None).first()
            ServiceCategory.objects.update_or_create(main_category=main, parent=parent, slug=_required(request.POST, "slug", "المعرف"), defaults={"name": _required(request.POST, "name", "الاسم"), "icon": request.POST.get("icon", ""), "sort_order": int(request.POST.get("sort_order", 0) or 0), "description": request.POST.get("description", "")})
        elif action == "service":
            category = get_object_or_404(ServiceCategory, pk=request.POST.get("category"))
            Service.objects.update_or_create(code=_required(request.POST, "code", "الكود"), defaults={"category": category, "name": _required(request.POST, "name", "الاسم"), "slug": request.POST.get("slug") or slugify(request.POST["name"], allow_unicode=True), "description": request.POST.get("description", ""), "pricing_mode": request.POST.get("pricing_mode", "fixed"), "price": Decimal(request.POST.get("price", "0") or "0"), "min_amount": Decimal(request.POST["min_amount"]) if request.POST.get("min_amount") else None, "max_amount": Decimal(request.POST["max_amount"]) if request.POST.get("max_amount") else None, "currency": request.POST.get("currency", "YER"), "icon": request.POST.get("icon", ""), "sort_order": int(request.POST.get("sort_order", 0) or 0)})
        elif action == "field":
            service = get_object_or_404(Service, pk=request.POST.get("service"))
            ServiceField.objects.update_or_create(service=service, key=_required(request.POST, "key", "المفتاح"), defaults={"label": _required(request.POST, "label", "العنوان"), "field_type": request.POST.get("field_type", "text"), "required": request.POST.get("required") == "1", "secret": request.POST.get("secret") == "1", "default_value": _json(request.POST.get("default_value"), None), "choices": _json(request.POST.get("choices"), []), "validation": _json(request.POST.get("validation"), {}), "sort_order": int(request.POST.get("sort_order", 0) or 0)})
        elif action == "provider":
            connection = ProviderConnection.objects.filter(code=request.POST.get("code")).first()
            if connection:
                connection.name = _required(request.POST, "name", "الاسم")
                connection.connection_type = request.POST.get("connection_type", "sanaacash")
                connection.base_url = request.POST.get("base_url", "")
                connection.userid = request.POST.get("userid", "")
                connection.domain_name = request.POST.get("domain_name", "")
                connection.username = request.POST.get("username", "")
                if request.POST.get("password"):
                    connection.set_password(request.POST.get("password"))
                connection.headers = _json(request.POST.get("headers"), {})
                connection.timeout_seconds = int(request.POST.get("timeout_seconds", 20) or 20)
                connection.save()
            else:
                connection = ProviderConnection(name=_required(request.POST, "name", "الاسم"), code=_required(request.POST, "code", "الكود"), connection_type=request.POST.get("connection_type", "sanaacash"), base_url=request.POST.get("base_url", ""), userid=request.POST.get("userid", ""), domain_name=request.POST.get("domain_name", ""), username=request.POST.get("username", ""), headers=_json(request.POST.get("headers"), {}), timeout_seconds=int(request.POST.get("timeout_seconds", 20) or 20))
                connection.set_password(request.POST.get("password", ""))
                connection.save()
        elif action == "link":
            provider = get_object_or_404(ProviderConnection, pk=request.POST.get("provider"))
            ProviderLink.objects.update_or_create(code=_required(request.POST, "code", "الكود"), defaults={"provider": provider, "name": _required(request.POST, "name", "الاسم"), "operation": request.POST.get("operation", ""), "path_template": _required(request.POST, "path_template", "المسار"), "http_method": request.POST.get("http_method", "GET"), "fixed_params": _json(request.POST.get("fixed_params"), {}), "field_map": _json(request.POST.get("field_map"), {}), "headers": _json(request.POST.get("headers"), {}), "success_codes": _json(request.POST.get("success_codes"), ["0"]), "pending_codes": _json(request.POST.get("pending_codes"), ["-2"]), "status_path_template": request.POST.get("status_path_template", ""), "status_params": _json(request.POST.get("status_params"), {}), "priority": int(request.POST.get("priority", 100) or 100)})
        elif action == "distribution":
            service = get_object_or_404(Service, pk=request.POST.get("service"))
            provider_link = get_object_or_404(ProviderLink, pk=request.POST.get("provider_link"))
            ServiceDistribution.objects.update_or_create(service=service, provider_link=provider_link, defaults={"priority": int(request.POST.get("priority", 100) or 100), "conditions": _json(request.POST.get("conditions"), {})})
        elif action == "telecom_denom":
            service = get_object_or_404(Service, pk=request.POST.get("service"))
            TelecomDenomination.objects.update_or_create(service=service, external_code=_required(request.POST, "external_code", "رقم/كود الربط لدى المزود"), defaults={"name": _required(request.POST, "name", "الاسم"), "face_value": Decimal(request.POST["face_value"]), "sale_price": Decimal(request.POST["sale_price"]), "payment_type": request.POST.get("payment_type", ""), "line_type": request.POST.get("line_type", ""), "metadata": _json(request.POST.get("metadata"), {})})
        elif action == "telecom_plan":
            service = get_object_or_404(Service, pk=request.POST.get("service"))
            TelecomPlan.objects.update_or_create(service=service, external_code=_required(request.POST, "external_code", "رقم/كود الربط لدى المزود"), defaults={"name": _required(request.POST, "name", "الاسم"), "price": Decimal(request.POST["price"]), "quota": Decimal(request.POST["quota"]) if request.POST.get("quota") else None, "quota_unit": request.POST.get("quota_unit", ""), "validity_days": int(request.POST["validity_days"]) if request.POST.get("validity_days") else None, "payment_type": request.POST.get("payment_type", ""), "line_type": request.POST.get("line_type", ""), "metadata": _json(request.POST.get("metadata"), {})})
        elif action == "game":
            service = get_object_or_404(Service, pk=request.POST.get("service"))
            GameProduct.objects.update_or_create(service=service, external_code=_required(request.POST, "external_code", "رقم/كود الربط لدى المزود"), defaults={"name": _required(request.POST, "name", "الاسم"), "price": Decimal(request.POST["price"]), "currency": request.POST.get("currency", "YER"), "metadata": _json(request.POST.get("metadata"), {})})
        elif action == "digital":
            service = get_object_or_404(Service, pk=request.POST.get("service"))
            DigitalProduct.objects.update_or_create(service=service, external_code=request.POST.get("external_code", ""), defaults={"name": _required(request.POST, "name", "الاسم"), "price": Decimal(request.POST["price"]), "currency": request.POST.get("currency", "YER"), "validity_days": int(request.POST["validity_days"]) if request.POST.get("validity_days") else None, "metadata": _json(request.POST.get("metadata"), {})})
        elif action == "toggle":
            model_map = {"main": MainServiceCategory, "category": ServiceCategory, "service": Service, "provider": ProviderConnection, "link": ProviderLink, "distribution": ServiceDistribution, "field": ServiceField}
            obj = get_object_or_404(model_map[request.POST.get("model")], pk=request.POST.get("pk"))
            obj.is_active = not obj.is_active
            obj.save(update_fields=["is_active"])
        else:
            raise ValueError("عملية غير معروفة.")
        ensure_service_accounts()


@user_passes_test(staff_only, login_url="/admin/dashboard/login/")
def dashboard(request):
    if request.method == "POST":
        try:
            _post_action(request)
            messages.success(request, "تم حفظ التغييرات بنجاح.")
        except (ValueError, InvalidOperation) as exc:
            messages.error(request, str(exc))
        except Exception as exc:
            messages.error(request, f"تعذر الحفظ: {exc}")
        return redirect(request.POST.get("next") or "admin-dashboard-services")
    ctx = _context()
    ctx["section"] = "overview"
    return render(request, "services/dashboard.html", ctx)


@user_passes_test(staff_only, login_url="/admin/dashboard/login/")
def section_view(request, section):
    if request.method == "POST":
        try:
            _post_action(request)
            messages.success(request, "تم الحفظ بنجاح.")
        except (ValueError, InvalidOperation) as exc:
            messages.error(request, str(exc))
        except Exception as exc:
            messages.error(request, f"تعذر الحفظ: {exc}")
        return redirect(request.POST.get("next") or request.path)
    ctx = _context()
    ctx["section"] = section
    return render(request, "services/dashboard.html", ctx)
