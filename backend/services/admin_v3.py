import json
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.text import slugify

from .catalog_base import SERVICES
from .catalog_data import CATEGORIES, LINKS, MAIN
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
    ServiceTransaction,
    TelecomDenomination,
    TelecomPlan,
)
from .provider import ProviderClient
from .provider_setup import create_or_update_sanaacash_provider


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
    ("card_image", "صورة البطاقة الشخصية", "image"),
    ("audio", "الاستديو / الصوت", "audio"),
    ("points", "النقاط", "number"),
    ("internet_type", "أنواع باقات الانترنت", "select"),
    ("sim_type", "نوع الشريحة", "select"),
    ("program", "الشريحة / برمجة", "select"),
    ("amount", "المبلغ", "decimal"),
    ("wallet", "المحفظة", "text"),
    ("wallet_number", "رقم المحفظة", "text"),
    ("wallet_company", "اسم شركة الحوالة", "text"),
    ("currency", "العملات", "select"),
    ("wifi_network", "شبكات الواي فاي", "select"),
    ("wifi_card", "فئات كروت شبكات الواي فاي", "select"),
    ("city_from", "قائمة المدن (من)", "select"),
    ("city_to", "قائمة المدن (إلى)", "select"),
    ("transport_company", "شركات النقل البري", "select"),
    ("ticket_type", "فئات التذاكر", "select"),
    ("travel_date", "تاريخ السفر", "date"),
    ("sender_name", "اسم المرسل", "text"),
    ("receiver_name", "اسم المستلم", "text"),
    ("address", "العنوان", "text"),
    ("wallet_reference", "مرجع الحوالة", "text"),
    ("email", "البريد الإلكتروني", "email"),
    ("playerid", "رقم اللاعب", "text"),
    ("playername", "اسم اللاعب", "text"),
    ("zoneid", "زون ايدي", "text"),
    ("uniqcode", "الكود الموحد", "text"),
    ("product_price", "سعر المنتج", "decimal"),
    ("quantity", "الكمية", "number"),
    ("total", "الإجمالي", "decimal"),
    ("contract_number", "رقم العقد", "text"),
    ("customer_id", "رقم المشترك", "text"),
    ("placeid", "رقم المنطقة", "text"),
    ("service_details", "تفاصيل الخدمة", "text"),
]
FIELD_MAP = {key: (label, field_type) for key, label, field_type in FIELD_LIBRARY}
SERVICE_LINK_KEY = {row[0]: row[5] for row in SERVICES}


def staff_only(user):
    return bool(user.is_authenticated and (user.is_staff or getattr(user, "role", None) == "admin"))


def money(value, default="0"):
    if value in (None, ""):
        return Decimal(default)
    try:
        result = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError("القيمة المالية غير صالحة.") from exc
    if result < 0:
        raise ValueError("القيمة المالية لا يمكن أن تكون سالبة.")
    return result


def json_value(value, fallback):
    if not value:
        return fallback
    try:
        return json.loads(value)
    except json.JSONDecodeError as exc:
        raise ValueError("JSON غير صالح.") from exc


def common_context(section):
    return {
        "section": section,
        "mains": MainServiceCategory.objects.all().order_by("sort_order", "id"),
        "categories": ServiceCategory.objects.select_related("main_category", "parent").all().order_by("main_category__sort_order", "sort_order", "id"),
        "services": Service.objects.select_related("category__main_category").prefetch_related("fields").all().order_by("category__main_category__sort_order", "category__sort_order", "sort_order", "id"),
        "providers": ProviderConnection.objects.prefetch_related("links").all().order_by("name"),
        "fields": ServiceField.objects.select_related("service").all().order_by("service__name", "sort_order", "id"),
        "plans": TelecomPlan.objects.select_related("service").all().order_by("service__name", "sort_order", "id"),
        "denoms": TelecomDenomination.objects.select_related("service").all().order_by("service__name", "sort_order", "id"),
        "games": GameProduct.objects.select_related("service").all().order_by("service__name", "sort_order", "id"),
        "digital": DigitalProduct.objects.select_related("service").all().order_by("service__name", "sort_order", "id"),
        "options": ServiceOption.objects.select_related("service").all().order_by("service__name", "sort_order", "id"),
        "field_library": FIELD_LIBRARY,
    }


def choose_provider_link(service, provider):
    key = SERVICE_LINK_KEY.get(service.code)
    links = list(provider.links.filter(is_active=True).order_by("priority", "id"))
    if not links:
        return None
    if key:
        exact = next((link for link in links if link.code == key or link.code.endswith("-" + key)), None)
        if exact:
            return exact
    operation = "query" if service.service_kind == Service.ServiceKinds.QUERY else "catalog" if service.service_kind == Service.ServiceKinds.CATALOG else "bill"
    candidates = [link for link in links if operation in link.operation.lower() or operation in link.code.lower()]
    return candidates[0] if candidates else links[0]


def save_selected_fields(service, selected):
    selected = {key for key in selected if key in FIELD_MAP}
    existing = set(service.fields.values_list("key", flat=True))
    for index, key in enumerate(FIELD_LIBRARY):
        field_key = key[0]
        if field_key not in selected:
            continue
        label, field_type = FIELD_MAP[field_key]
        ServiceField.objects.update_or_create(
            service=service,
            key=field_key,
            defaults={
                "label": label,
                "field_type": field_type,
                "required": False,
                "sort_order": index * 10,
                "is_active": True,
            },
        )
    ServiceField.objects.filter(service=service, key__in=existing).exclude(key__in=selected).update(is_active=False)


def resource_history(kind, obj_id):
    return ServiceTransaction.objects.filter(item_type=kind, item_id=obj_id).exists()


@user_passes_test(staff_only, login_url="/admin/dashboard/login/")
def service_admin(request, section="overview"):
    if request.method != "POST":
        context = common_context(section)
        context["edit_service"] = Service.objects.prefetch_related("fields").filter(pk=request.GET.get("edit_service") or 0).first()
        context["edit_plan"] = TelecomPlan.objects.filter(pk=request.GET.get("edit_plan") or 0).first()
        context["edit_denom"] = TelecomDenomination.objects.filter(pk=request.GET.get("edit_denom") or 0).first()
        context["edit_game"] = GameProduct.objects.filter(pk=request.GET.get("edit_game") or 0).first()
        context["edit_digital"] = DigitalProduct.objects.filter(pk=request.GET.get("edit_digital") or 0).first()
        context["edit_option"] = ServiceOption.objects.filter(pk=request.GET.get("edit_option") or 0).first()
        return render(request, "services/admin_v3.html", context)

    action = request.POST.get("action", "")
    try:
        with transaction.atomic():
            if action == "main":
                name = (request.POST.get("name") or "").strip()
                if not name:
                    raise ValueError("اسم الفئة الرئيسية مطلوب.")
                MainServiceCategory.objects.update_or_create(
                    slug=(request.POST.get("slug") or slugify(name, allow_unicode=True)).strip(),
                    defaults={"name": name, "description": request.POST.get("description", "").strip(), "sort_order": int(request.POST.get("sort_order", 0) or 0), "is_active": True},
                )
                messages.success(request, "تم حفظ الفئة الرئيسية.")
            elif action == "category":
                main = get_object_or_404(MainServiceCategory, pk=request.POST.get("main_category"))
                name = (request.POST.get("name") or "").strip()
                if not name:
                    raise ValueError("اسم الفئة مطلوب.")
                parent = ServiceCategory.objects.filter(pk=request.POST.get("parent") or None).first()
                ServiceCategory.objects.update_or_create(
                    main_category=main,
                    parent=parent,
                    slug=(request.POST.get("slug") or slugify(name, allow_unicode=True)).strip(),
                    defaults={"name": name, "description": request.POST.get("description", "").strip(), "sort_order": int(request.POST.get("sort_order", 0) or 0), "is_active": True},
                )
                messages.success(request, "تم حفظ الفئة.")
            elif action == "service":
                service = Service.objects.filter(pk=request.POST.get("pk") or 0).first() or Service()
                service.category = get_object_or_404(ServiceCategory, pk=request.POST.get("category"))
                service.name = (request.POST.get("name") or "").strip()
                service.code = (request.POST.get("code") or service.code or "").strip()
                service.slug = (request.POST.get("slug") or slugify(service.name, allow_unicode=True)).strip()
                if not service.name or not service.code:
                    raise ValueError("اسم وكود الخدمة مطلوبان.")
                service.description = request.POST.get("description", "").strip()
                service.service_kind = request.POST.get("service_kind", Service.ServiceKinds.PURCHASE)
                service.requires_balance = request.POST.get("requires_balance") == "1"
                service.pricing_mode = request.POST.get("pricing_mode", Service.PricingModes.FIXED)
                service.price = money(request.POST.get("price"))
                service.min_amount = money(request.POST.get("min_amount")) if request.POST.get("min_amount") else None
                service.max_amount = money(request.POST.get("max_amount")) if request.POST.get("max_amount") else None
                service.currency = (request.POST.get("currency") or "YER").strip().upper()
                service.icon = request.POST.get("icon", "").strip()
                service.sort_order = int(request.POST.get("sort_order", 0) or 0)
                metadata = dict(service.metadata or {})
                for key in ("service_number", "price_usd", "price_sar", "employee_price", "submit_label", "unified_link_number", "duplicate_guard"):
                    metadata[key] = (request.POST.get(key) or "").strip()
                service.metadata = metadata
                service.is_active = True
                service.save()
                save_selected_fields(service, request.POST.getlist("field_keys"))
                messages.success(request, "تم حفظ الخدمة والحقول المختارة.")
            elif action == "field":
                service = get_object_or_404(Service, pk=request.POST.get("service"))
                key = (request.POST.get("key") or "").strip()
                if not key:
                    raise ValueError("مفتاح الحقل مطلوب.")
                field_type = request.POST.get("field_type", "text")
                allowed_types = {x[0] for x in FIELD_LIBRARY} | {"text", "number", "decimal", "date", "phone", "select", "boolean", "email", "image", "audio", "json"}
                if field_type not in allowed_types:
                    raise ValueError("نوع الحقل غير مدعوم.")
                ServiceField.objects.update_or_create(
                    service=service,
                    key=key,
                    defaults={
                        "label": (request.POST.get("label") or key).strip(),
                        "field_type": field_type,
                        "required": request.POST.get("required") == "1",
                        "secret": request.POST.get("secret") == "1",
                        "choices": json_value(request.POST.get("choices"), []),
                        "validation": json_value(request.POST.get("validation"), {}),
                        "default_value": json_value(request.POST.get("default_value"), None),
                        "sort_order": int(request.POST.get("sort_order", 0) or 0),
                        "is_active": True,
                    },
                )
                messages.success(request, "تم حفظ الحقل.")
            elif action in {"plan", "denom", "game", "digital", "option"}:
                service = get_object_or_404(Service, pk=request.POST.get("service"), is_active=True)
                name = (request.POST.get("name") or "").strip()
                code = (request.POST.get("external_code") or "").strip()
                if not name or not code:
                    raise ValueError("اسم العنصر والكود الخارجي مطلوبان.")
                metadata = json_value(request.POST.get("metadata"), {})
                if action == "plan":
                    obj = TelecomPlan.objects.filter(pk=request.POST.get("pk") or 0).first() or TelecomPlan(service=service)
                    obj.service = service
                    obj.name = name
                    obj.external_code = code
                    obj.provider_num = (request.POST.get("provider_num") or "").strip()
                    obj.package_number = (request.POST.get("package_number") or "").strip()
                    obj.price = money(request.POST.get("price"))
                    obj.quota = money(request.POST.get("quota")) if request.POST.get("quota") else None
                    obj.quota_unit = request.POST.get("quota_unit", "").strip()
                    obj.validity_days = int(request.POST["validity_days"]) if request.POST.get("validity_days") else None
                    obj.payment_type = request.POST.get("payment_type", "").strip()
                    obj.line_type = request.POST.get("line_type", "").strip()
                    meta = dict(obj.metadata or {})
                    meta.update(metadata)
                    meta.update({"price_usd": (request.POST.get("price_usd") or "").strip(), "price_sar": (request.POST.get("price_sar") or "").strip(), "employee_price": (request.POST.get("employee_price") or "").strip()})
                    obj.metadata = meta
                    obj.sort_order = int(request.POST.get("sort_order", 0) or 0)
                    obj.is_active = True
                    obj.save()
                elif action == "denom":
                    obj = TelecomDenomination.objects.filter(pk=request.POST.get("pk") or 0).first() or TelecomDenomination(service=service)
                    obj.service = service
                    obj.name = name
                    obj.external_code = code
                    obj.provider_num = (request.POST.get("provider_num") or "").strip()
                    obj.face_value = money(request.POST.get("face_value"))
                    obj.sale_price = money(request.POST.get("sale_price"))
                    obj.payment_type = request.POST.get("payment_type", "").strip()
                    obj.line_type = request.POST.get("line_type", "").strip()
                    meta = dict(obj.metadata or {})
                    meta.update(metadata)
                    meta.update({"price_usd": (request.POST.get("price_usd") or "").strip(), "price_sar": (request.POST.get("price_sar") or "").strip(), "employee_price": (request.POST.get("employee_price") or "").strip()})
                    obj.metadata = meta
                    obj.sort_order = int(request.POST.get("sort_order", 0) or 0)
                    obj.is_active = True
                    obj.save()
                elif action == "game":
                    obj = GameProduct.objects.filter(pk=request.POST.get("pk") or 0).first() or GameProduct(service=service)
                    obj.service = service
                    obj.name = name
                    obj.external_code = code
                    obj.price = money(request.POST.get("price"))
                    obj.currency = (request.POST.get("currency") or "YER").strip().upper()
                    obj.validity_days = int(request.POST["validity_days"]) if request.POST.get("validity_days") else None
                    obj.metadata = metadata
                    obj.sort_order = int(request.POST.get("sort_order", 0) or 0)
                    obj.is_active = True
                    obj.save()
                elif action == "digital":
                    obj = DigitalProduct.objects.filter(pk=request.POST.get("pk") or 0).first() or DigitalProduct(service=service)
                    obj.service = service
                    obj.name = name
                    obj.external_code = code
                    obj.price = money(request.POST.get("price"))
                    obj.currency = (request.POST.get("currency") or "YER").strip().upper()
                    obj.validity_days = int(request.POST["validity_days"]) if request.POST.get("validity_days") else None
                    obj.metadata = metadata
                    obj.sort_order = int(request.POST.get("sort_order", 0) or 0)
                    obj.is_active = True
                    obj.save()
                else:
                    obj = ServiceOption.objects.filter(pk=request.POST.get("pk") or 0).first() or ServiceOption(service=service)
                    obj.service = service
                    obj.name = name
                    obj.external_code = code
                    obj.provider_num = (request.POST.get("provider_num") or "").strip()
                    obj.price = money(request.POST.get("price"))
                    obj.currency = (request.POST.get("currency") or "YER").strip().upper()
                    obj.metadata = metadata
                    obj.sort_order = int(request.POST.get("sort_order", 0) or 0)
                    obj.is_active = True
                    obj.save()
                messages.success(request, "تم حفظ المورد بنجاح.")
            elif action == "toggle_resource":
                mapping = {"plan": TelecomPlan, "denom": TelecomDenomination, "game": GameProduct, "digital": DigitalProduct, "option": ServiceOption}
                model = mapping.get(request.POST.get("kind"))
                if not model:
                    raise ValueError("نوع المورد غير معروف.")
                obj = get_object_or_404(model, pk=request.POST.get("pk"))
                obj.is_active = not obj.is_active
                obj.save(update_fields=["is_active"])
                messages.success(request, "تم تحديث حالة المورد.")
            elif action == "delete_resource":
                mapping = {"plan": TelecomPlan, "denom": TelecomDenomination, "game": GameProduct, "digital": DigitalProduct, "option": ServiceOption}
                kind = request.POST.get("kind")
                model = mapping.get(kind)
                if not model:
                    raise ValueError("نوع المورد غير معروف.")
                obj = get_object_or_404(model, pk=request.POST.get("pk"))
                if resource_history(kind, obj.pk):
                    obj.is_active = False
                    obj.save(update_fields=["is_active"])
                    messages.warning(request, "المورد مستخدم في عمليات تاريخية؛ تم إيقافه بدل حذفه.")
                else:
                    obj.delete()
                    messages.success(request, "تم حذف المورد بأمان.")
            else:
                raise ValueError("عملية غير معروفة.")
    except Exception as exc:
        messages.error(request, f"تعذر التنفيذ: {exc}")
    return redirect(request.POST.get("next") or request.path)


@user_passes_test(staff_only, login_url="/admin/dashboard/login/")
def distribution(request):
    if request.method == "POST":
        try:
            provider = get_object_or_404(ProviderConnection, pk=request.POST.get("provider"), is_active=True)
            selected = {int(x) for x in request.POST.getlist("services") if x.isdigit()}
            priority = max(1, int(request.POST.get("priority", 100) or 100))
            with transaction.atomic():
                ServiceDistribution.objects.filter(provider_link__provider=provider).update(is_active=False)
                for service in Service.objects.filter(pk__in=selected, is_active=True):
                    link = choose_provider_link(service, provider)
                    if not link:
                        raise ValueError(f"لا يوجد مسار قياسي فعال للخدمة: {service.name}")
                    ServiceDistribution.objects.update_or_create(
                        service=service,
                        provider_link=link,
                        defaults={"priority": priority, "conditions": {}, "is_active": True},
                    )
            messages.success(request, f"تم حفظ {len(selected)} خدمة على الربطية {provider.name}.")
        except Exception as exc:
            messages.error(request, f"تعذر حفظ التوزيع: {exc}")
        return redirect(f"{request.path}?provider={request.POST.get('provider', '')}")

    providers = list(ProviderConnection.objects.filter(is_active=True).prefetch_related("links").order_by("name"))
    provider_id = request.GET.get("provider") or (str(providers[0].id) if providers else "")
    selected = set(ServiceDistribution.objects.filter(is_active=True, provider_link__provider_id=provider_id).values_list("service_id", flat=True)) if provider_id else set()
    groups = []
    for main in MainServiceCategory.objects.filter(is_active=True).order_by("sort_order", "id"):
        rows = []
        for category in main.categories.filter(is_active=True).order_by("sort_order", "id"):
            rows.extend((category.name, service) for service in category.services.filter(is_active=True).order_by("sort_order", "id"))
        if rows:
            groups.append((main, rows))
    return render(request, "services/distribution_v3.html", {"providers": providers, "selected_provider_id": provider_id, "selected_services": selected, "groups": groups})


@user_passes_test(staff_only, login_url="/admin/dashboard/login/")
def providers(request):
    # Delegate to the tested provider flow while keeping all admin pages under one app.
    return redirect("legacy-services-providers")
