import json
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from django.db import transaction
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.text import slugify

from .accounting_bridge import ensure_service_accounts
from .provider import ProviderClient
from .provider_info import fetch_provider_info
from .provider_setup import create_or_update_sanaacash_provider
from .models import (
    DigitalProduct,
    GameProduct,
    MainServiceCategory,
    ProviderConnection,
    ProviderLink,
    Service,
    ServiceCategory,
    ServiceDistribution,
    ServiceField,
    ServiceOption,
    ServiceTask,
    ServiceTransaction,
    TelecomDenomination,
    TelecomPlan,
    TelecomPlanType,
    WifiCard,
    WifiDenomination,
    WifiNetwork,
)

FIELD_LIBRARY = [
    ("full_name", "الاسم الرباعي مع اللقب", "text"),
    ("name", "الاسم", "text"),
    ("name_en", "الاسم بالإنجليزي", "text"),
    ("number", "رقم", "number"),
    ("card_number", "رقم البطاقة", "text"),
    ("issue_date", "تاريخ الإصدار", "date"),
    ("birth_date", "تاريخ الميلاد", "date"),
    ("mobile", "رقم الهاتف", "phone"),
    ("sim_number", "رقم الشريحة", "text"),
    ("email", "البريد الإلكتروني", "email"),
    ("amount", "المبلغ", "decimal"),
    ("wallet", "المحفظة", "text"),
    ("wallet_number", "رقم المحفظة", "text"),
    ("wallet_company", "اسم شركة الحوالة", "text"),
    ("currency", "العملة", "select"),
    ("customer_id", "رقم المشترك", "text"),
    ("contract_number", "رقم العقد", "text"),
    ("playerid", "رقم اللاعب", "text"),
    ("playername", "اسم اللاعب", "text"),
    ("zoneid", "زون ايدي", "text"),
    ("uniqcode", "الكود الموحد", "text"),
    ("internet_type", "نوع باقة الإنترنت", "select"),
    ("sim_type", "نوع الشريحة", "select"),
    ("wifi_network", "شبكة الواي فاي", "select"),
    ("wifi_card", "فئة كرت الواي فاي", "select"),
    ("service_details", "تفاصيل الخدمة", "text"),
]
FIELD_MAP = {key: (label, typ) for key, label, typ in FIELD_LIBRARY}


def staff_only(user):
    return bool(user.is_authenticated and (user.is_staff or getattr(user, "role", None) == "admin"))


def _render_services_page(request, ctx):
    return render(request, "services/dashboard.html", ctx)


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


def _context(section="overview"):
    mains = MainServiceCategory.objects.all().order_by("sort_order", "id")
    categories = ServiceCategory.objects.select_related("main_category", "parent").all().order_by(
        "main_category__sort_order", "sort_order", "id"
    )
    services = (
        Service.objects.select_related("category__main_category")
        .prefetch_related("fields")
        .annotate(transaction_count=Count("transactions"))
        .order_by("category__main_category__sort_order", "category__sort_order", "sort_order", "id")
    )
    payment_services = services.filter(category__main_category__slug="payments")
    game_services = services.filter(category__main_category__slug="games")
    digital_services = services.filter(category__main_category__slug="software")

    plans = TelecomPlan.objects.select_related("service__category__main_category")
    denoms = TelecomDenomination.objects.select_related("service__category__main_category")
    games = GameProduct.objects.select_related("service__category__main_category")
    digital = DigitalProduct.objects.select_related("service__category__main_category")
    options = ServiceOption.objects.select_related("service__category__main_category")
    plan_types = TelecomPlanType.objects.select_related("service")

    return {
        "section": section,
        "mains": mains,
        "categories": categories,
        "services": services,
        "payment_services": payment_services,
        "game_services": game_services,
        "digital_services": digital_services,
        "fields": ServiceField.objects.select_related("service").order_by("service__name", "sort_order", "id"),
        "field_library": FIELD_LIBRARY,
        "providers": ProviderConnection.objects.all().prefetch_related("links").order_by("name"),
        "links": ProviderLink.objects.select_related("provider").all().order_by("provider__name", "priority", "id"),
        "distributions": ServiceDistribution.objects.select_related("service__category__main_category", "provider_link__provider"),
        "transactions": ServiceTransaction.objects.select_related("service", "customer", "provider_link__provider").order_by("-created_at")[:100],
        "tasks": ServiceTask.objects.select_related("transaction__service", "provider_link__provider").order_by("-id")[:120],
        "plans": plans.order_by("service__category__main_category__sort_order", "service__name", "sort_order", "id"),
        "denoms": denoms.order_by("service__category__main_category__sort_order", "service__name", "sort_order", "id"),
        "games": games.order_by("service__name", "sort_order", "id"),
        "digital": digital.order_by("service__name", "sort_order", "id"),
        "options": options.order_by("service__name", "sort_order", "id"),
        "plan_types": plan_types.order_by("service__name", "sort_order", "id"),
        "wifi_networks": WifiNetwork.objects.select_related("owner").prefetch_related("denominations__cards").order_by("name"),
        "wifi_denominations": WifiDenomination.objects.select_related("network", "network__owner").prefetch_related("cards").order_by("network__name", "face_value", "id"),
        "wifi_cards": WifiCard.objects.select_related("denomination__network", "sold_to").order_by("status", "denomination__network__name", "id")[:500],
        "wifi_owners": __import__("django.contrib.auth", fromlist=["get_user_model"]).get_user_model().objects.filter(is_active=True).order_by("first_name", "last_name", "phone"),
        "stats": {
            "main": mains.filter(is_active=True).count(),
            "categories": categories.filter(is_active=True).count(),
            "services": services.filter(is_active=True).count(),
            "providers": ProviderConnection.objects.filter(is_active=True).count(),
            "queued": ServiceTask.objects.filter(status__in=[ServiceTask.Statuses.QUEUED, ServiceTask.Statuses.RETRY]).count(),
            "transactions": ServiceTransaction.objects.count(),
            "plans": plans.count(),
            "denoms": denoms.count(),
            "games": games.count(),
            "wifi_cards": WifiCard.objects.filter(status=WifiCard.Status.AVAILABLE).count(),
        },
    }


def _post_action(request):
    action = request.POST.get("action")
    with transaction.atomic():
        if action == "main":
            MainServiceCategory.objects.update_or_create(
                slug=_required(request.POST, "slug", "المعرف"),
                defaults={
                    "name": _required(request.POST, "name", "الاسم"),
                    "icon": request.POST.get("icon", ""),
                    "sort_order": int(request.POST.get("sort_order", 0) or 0),
                    "description": request.POST.get("description", "").strip(),
                    "is_active": True,
                },
            )
        elif action == "category":
            main = get_object_or_404(MainServiceCategory, pk=request.POST.get("main_category"))
            parent_id = request.POST.get("parent") or None
            parent = ServiceCategory.objects.filter(pk=parent_id, main_category=main).first() if parent_id else None
            ServiceCategory.objects.update_or_create(
                main_category=main,
                parent=parent,
                slug=_required(request.POST, "slug", "المعرف"),
                defaults={
                    "name": _required(request.POST, "name", "الاسم"),
                    "icon": request.POST.get("icon", ""),
                    "sort_order": int(request.POST.get("sort_order", 0) or 0),
                    "description": request.POST.get("description", "").strip(),
                    "is_active": True,
                },
            )
        elif action == "service":
            category = get_object_or_404(ServiceCategory, pk=request.POST.get("category"), is_active=True)
            pk = request.POST.get("pk") or 0
            service = Service.objects.filter(pk=pk).first() if str(pk).isdigit() else None
            if service is None:
                service = Service(code=_required(request.POST, "code", "الكود"))
            service.category = category
            service.name = _required(request.POST, "name", "الاسم")
            service.slug = request.POST.get("slug") or slugify(service.name, allow_unicode=True)
            service.code = _required(request.POST, "code", "الكود")
            service.description = request.POST.get("description", "").strip()
            service.service_kind = request.POST.get("service_kind", Service.ServiceKinds.PURCHASE)
            service.requires_balance = request.POST.get("requires_balance") == "1"
            service.pricing_mode = request.POST.get("pricing_mode", Service.PricingModes.FIXED)
            service.price = Decimal(request.POST.get("price", "0") or "0")
            service.min_amount = Decimal(request.POST["min_amount"]) if request.POST.get("min_amount") else None
            service.max_amount = Decimal(request.POST["max_amount"]) if request.POST.get("max_amount") else None
            service.currency = (request.POST.get("currency") or "YER").upper()
            service.icon = request.POST.get("icon", "").strip()
            service.sort_order = int(request.POST.get("sort_order", 0) or 0)
            metadata = dict(service.metadata or {})
            for key in ("service_number", "price_usd", "price_sar", "employee_price", "submit_label", "unified_link_number", "duplicate_guard"):
                if key in request.POST:
                    metadata[key] = (request.POST.get(key) or "").strip()
            service.metadata = metadata
            service.is_active = True
            service.save()
        elif action == "field":
            service = get_object_or_404(Service, pk=request.POST.get("service"))
            ServiceField.objects.update_or_create(
                service=service,
                key=_required(request.POST, "key", "المفتاح"),
                defaults={
                    "label": _required(request.POST, "label", "العنوان"),
                    "field_type": request.POST.get("field_type", "text"),
                    "required": request.POST.get("required") == "1",
                    "secret": request.POST.get("secret") == "1",
                    "default_value": _json(request.POST.get("default_value"), None),
                    "choices": _json(request.POST.get("choices"), []),
                    "validation": _json(request.POST.get("validation"), {}),
                    "sort_order": int(request.POST.get("sort_order", 0) or 0),
                    "is_active": True,
                },
            )
        elif action == "provider":
            provider = create_or_update_sanaacash_provider(
                code=_required(request.POST, "code", "كود الربطية"),
                name=_required(request.POST, "name", "اسم الربطية"),
                userid=(request.POST.get("userid") or "").strip(),
                domain_name=(request.POST.get("domain_name") or "").strip(),
                username=(request.POST.get("username") or "").strip(),
                password=request.POST.get("password") or "",
                note=(request.POST.get("note") or "").strip(),
                base_url=(request.POST.get("base_url") or "https://sanaacash.yrbso.net/api/yr/").strip(),
            )
            messages.success(request, f"تم حفظ الربطية {provider.name} وتهيئة مساراتها القياسية.")
        elif action == "provider_balance":
            provider = get_object_or_404(ProviderConnection, pk=request.POST.get("provider"))
            if not provider.is_active:
                raise ValueError("لا يمكن فحص رصيد ربطية متوقفة.")
            result = fetch_provider_info(provider)
            if result.success:
                balance = result.response.get("normalized_balance", result.response.get("balance", "—"))
                messages.success(request, f"رصيد {provider.name}: {balance}")
            else:
                messages.error(request, f"تعذر فحص رصيد {provider.name}: {result.description or result.code}")
        elif action == "link":
            provider = get_object_or_404(ProviderConnection, pk=request.POST.get("provider"), is_active=True)
            ProviderLink.objects.update_or_create(
                code=_required(request.POST, "code", "الكود"),
                defaults={
                    "provider": provider,
                    "name": _required(request.POST, "name", "الاسم"),
                    "operation": request.POST.get("operation", "").strip(),
                    "path_template": _required(request.POST, "path_template", "المسار"),
                    "http_method": request.POST.get("http_method", "GET"),
                    "request_encoding": request.POST.get("request_encoding", "query"),
                    "fixed_params": _json(request.POST.get("fixed_params"), {}),
                    "field_map": _json(request.POST.get("field_map"), {}),
                    "headers": _json(request.POST.get("headers"), {}),
                    "success_codes": _json(request.POST.get("success_codes"), ["0"]),
                    "pending_codes": _json(request.POST.get("pending_codes"), ["-2"]),
                    "status_path_template": request.POST.get("status_path_template", ""),
                    "status_params": _json(request.POST.get("status_params"), {}),
                    "priority": int(request.POST.get("priority", 100) or 100),
                    "is_active": True,
                },
            )
        elif action == "distribution":
            service = get_object_or_404(Service, pk=request.POST.get("service"), is_active=True)
            provider_link = get_object_or_404(ProviderLink, pk=request.POST.get("provider_link"), is_active=True)
            ServiceDistribution.objects.update_or_create(
                service=service,
                provider_link=provider_link,
                defaults={
                    "priority": int(request.POST.get("priority", 100) or 100),
                    "conditions": _json(request.POST.get("conditions"), {}),
                    "is_active": True,
                },
            )
        elif action in {"telecom_denom", "telecom_plan", "game", "digital", "option"}:
            service = get_object_or_404(Service, pk=request.POST.get("service"), is_active=True)
            resource_map = {
                "telecom_denom": TelecomDenomination,
                "telecom_plan": TelecomPlan,
                "game": GameProduct,
                "digital": DigitalProduct,
                "option": ServiceOption,
            }
            model = resource_map[action]
            pk = request.POST.get("pk") or 0
            obj = model.objects.filter(pk=pk).first() if str(pk).isdigit() else None
            if obj is None:
                obj = model(service=service)
            obj.service = service
            obj.name = _required(request.POST, "name", "الاسم")
            obj.external_code = (request.POST.get("external_code") or "").strip()
            if action in {"telecom_denom", "telecom_plan", "game"} and not obj.external_code:
                raise ValueError("الكود الخارجي مطلوب.")
            if action == "telecom_denom":
                obj.face_value = Decimal(request.POST.get("face_value", "0") or "0")
                obj.sale_price = Decimal(request.POST.get("sale_price", "0") or "0")
                obj.payment_type = request.POST.get("payment_type", "").strip()
                obj.line_type = request.POST.get("line_type", "").strip()
                meta = dict(obj.metadata or {})
                for key in ("provider_num", "price_usd", "price_sar", "employee_price"):
                    if key in request.POST:
                        meta[key] = (request.POST.get(key) or "").strip()
                meta.update(_json(request.POST.get("metadata"), {}))
                obj.metadata = meta
            elif action == "telecom_plan":
                obj.price = Decimal(request.POST.get("price", "0") or "0")
                obj.quota = Decimal(request.POST["quota"]) if request.POST.get("quota") else None
                obj.quota_unit = request.POST.get("quota_unit", "").strip()
                obj.validity_days = int(request.POST["validity_days"]) if request.POST.get("validity_days") else None
                obj.payment_type = request.POST.get("payment_type", "").strip()
                obj.line_type = request.POST.get("line_type", "").strip()
                meta = dict(obj.metadata or {})
                for key in ("provider_num", "package_number", "price_usd", "price_sar", "employee_price"):
                    if key in request.POST:
                        meta[key] = (request.POST.get(key) or "").strip()
                meta.update(_json(request.POST.get("metadata"), {}))
                obj.metadata = meta
            elif action == "game":
                obj.price = Decimal(request.POST.get("price", "0") or "0")
                obj.currency = (request.POST.get("currency") or "YER").upper()
                obj.metadata = _json(request.POST.get("metadata"), {})
            elif action == "digital":
                obj.price = Decimal(request.POST.get("price", "0") or "0")
                obj.currency = (request.POST.get("currency") or "YER").upper()
                obj.validity_days = int(request.POST["validity_days"]) if request.POST.get("validity_days") else None
                obj.metadata = _json(request.POST.get("metadata"), {})
            else:
                obj.provider_num = (request.POST.get("provider_num") or "").strip()
                obj.price = Decimal(request.POST.get("price", "0") or "0")
                obj.currency = (request.POST.get("currency") or "YER").upper()
                obj.metadata = _json(request.POST.get("metadata"), {})
            obj.sort_order = int(request.POST.get("sort_order", 0) or 0)
            obj.is_active = True
            obj.save()
        elif action == "plan_type":
            service = get_object_or_404(Service, pk=request.POST.get("service"), is_active=True)
            TelecomPlanType.objects.update_or_create(
                service=service,
                code=_required(request.POST, "code", "الكود"),
                defaults={
                    "name": _required(request.POST, "name", "الاسم"),
                    "description": request.POST.get("description", "").strip(),
                    "sort_order": int(request.POST.get("sort_order", 0) or 0),
                    "is_active": True,
                },
            )
        elif action == "wifi_network":
            from django.contrib.auth import get_user_model

            owner = get_object_or_404(get_user_model(), pk=request.POST.get("owner"), is_active=True)
            obj = WifiNetwork.objects.filter(pk=request.POST.get("pk") or 0).first() or WifiNetwork()
            obj.owner = owner
            obj.name = _required(request.POST, "name", "اسم الشبكة")
            obj.location = _required(request.POST, "location", "الموقع")
            obj.management_percent = Decimal(request.POST.get("management_percent", "0") or "0")
            obj.latitude = request.POST.get("latitude") or None
            obj.longitude = request.POST.get("longitude") or None
            obj.description = request.POST.get("description", "").strip()
            obj.is_active = True
            obj.save()
        elif action == "wifi_denomination":
            network = get_object_or_404(WifiNetwork, pk=request.POST.get("network"), is_active=True)
            obj = WifiDenomination.objects.filter(pk=request.POST.get("pk") or 0).first() or WifiDenomination(network=network)
            obj.network = network
            obj.name = _required(request.POST, "name", "اسم الفئة")
            obj.face_value = Decimal(request.POST.get("face_value", "0") or "0")
            obj.sale_price = Decimal(request.POST.get("sale_price", "0") or "0")
            obj.is_active = True
            if obj.face_value <= 0 or obj.sale_price <= 0:
                raise ValueError("القيمة الاسمية وسعر البيع يجب أن يكونا أكبر من صفر.")
            obj.save()
            messages.success(request, f"تم حفظ فئة الشبكة برقمها النظامي {obj.denomination_number}.")
        elif action == "wifi_card":
            denomination = get_object_or_404(WifiDenomination, pk=request.POST.get("denomination"), is_active=True, network__is_active=True)
            obj = WifiCard.objects.filter(pk=request.POST.get("pk") or 0).first() or WifiCard()
            obj.denomination = denomination
            obj.card_number = _required(request.POST, "card_number", "اسم المستخدم / رقم الكرت")
            obj.pin = (request.POST.get("pin") or "").strip()
            obj.status = request.POST.get("status", WifiCard.Status.AVAILABLE)
            obj.save()
            messages.success(request, "تم حفظ الكرت؛ كلمة المرور اختيارية.")
        elif action == "bulk_wifi_cards":
            denomination = get_object_or_404(WifiDenomination, pk=request.POST.get("denomination"), is_active=True)
            created = 0
            for line in (request.POST.get("cards") or "").splitlines():
                values = [value.strip() for value in line.split(",", 1)]
                username = values[0] if values else ""
                password = values[1] if len(values) > 1 else ""
                if not username:
                    continue
                WifiCard.objects.get_or_create(
                    card_number=username,
                    defaults={"denomination": denomination, "pin": password, "status": WifiCard.Status.AVAILABLE},
                )
                created += 1
            messages.success(request, f"تمت معالجة {created} كرت.")
        elif action == "toggle":
            model_map = {
                "main": MainServiceCategory,
                "category": ServiceCategory,
                "service": Service,
                "provider": ProviderConnection,
                "link": ProviderLink,
                "distribution": ServiceDistribution,
                "field": ServiceField,
                "plan": TelecomPlan,
                "denom": TelecomDenomination,
                "game": GameProduct,
                "digital": DigitalProduct,
                "option": ServiceOption,
                "plan_type": TelecomPlanType,
                "wifi_network": WifiNetwork,
                "wifi_denomination": WifiDenomination,
            }
            model = model_map.get(request.POST.get("model"))
            if not model:
                raise ValueError("نوع العنصر غير معروف.")
            obj = get_object_or_404(model, pk=request.POST.get("pk"))
            if hasattr(obj, "is_active"):
                obj.is_active = not obj.is_active
                obj.save(update_fields=["is_active"])
            elif isinstance(obj, WifiCard):
                obj.status = WifiCard.Status.BLOCKED if obj.status == WifiCard.Status.AVAILABLE else WifiCard.Status.AVAILABLE
                obj.save(update_fields=["status"])
        elif action == "toggle_wifi_card":
            obj = get_object_or_404(WifiCard, pk=request.POST.get("pk"))
            obj.status = WifiCard.Status.BLOCKED if obj.status == WifiCard.Status.AVAILABLE else WifiCard.Status.AVAILABLE
            obj.save(update_fields=["status", "updated_at"])
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
    return _render_services_page(request, _context("overview"))


@user_passes_test(staff_only, login_url="/admin/dashboard/login/")
def section_view(request, section):
    if request.method == "POST":
        try:
            _post_action(request)
        except (ValueError, InvalidOperation) as exc:
            messages.error(request, str(exc))
        except Exception as exc:
            messages.error(request, f"تعذر الحفظ: {exc}")
        return redirect(request.POST.get("next") or request.path)
    return _render_services_page(request, _context(section))
