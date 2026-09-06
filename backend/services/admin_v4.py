import json
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.text import slugify

from .catalog_base import SERVICES
from .models import (
    DigitalProduct, GameProduct, MainServiceCategory, ProviderConnection, ProviderLink,
    Service, ServiceCategory, ServiceDistribution, ServiceField, ServiceOption,
    ServiceTransaction, TelecomDenomination, TelecomPlan,
)

FIELD_LIBRARY = [
    ("full_name", "الاسم الرباعي مع اللقب", "text"), ("name", "الاسم", "text"),
    ("name_en", "الاسم بالإنجليزي", "text"), ("number", "رقم", "number"),
    ("card_number", "رقم البطاقة", "text"), ("issue_date", "تاريخ الإصدار", "date"),
    ("birth_date", "تاريخ الميلاد", "date"), ("mobile", "رقم الهاتف", "phone"),
    ("sim_number", "رقم الشريحة", "text"), ("card_image", "صورة البطاقة الشخصية", "image"),
    ("audio", "الاستديو / الصوت", "audio"), ("points", "النقاط", "number"),
    ("internet_type", "أنواع باقات الانترنت", "select"), ("sim_type", "نوع الشريحة", "select"),
    ("program", "الشريحة / برمجة", "select"), ("amount", "المبلغ", "decimal"),
    ("wallet", "المحفظة", "text"), ("wallet_number", "رقم المحفظة", "text"),
    ("wallet_company", "اسم شركة الحوالة", "text"), ("currency", "العملات", "select"),
    ("wifi_network", "شبكات الواي فاي", "select"), ("wifi_card", "فئات كروت شبكات الواي فاي", "select"),
    ("city_from", "قائمة المدن (من)", "select"), ("city_to", "قائمة المدن (إلى)", "select"),
    ("transport_company", "شركات النقل البري", "select"), ("ticket_type", "فئات التذاكر", "select"),
    ("travel_date", "تاريخ السفر", "date"), ("sender_name", "اسم المرسل", "text"),
    ("receiver_name", "اسم المستلم", "text"), ("address", "العنوان", "text"),
    ("wallet_reference", "مرجع الحوالة", "text"), ("email", "البريد الإلكتروني", "email"),
    ("playerid", "رقم اللاعب", "text"), ("playername", "اسم اللاعب", "text"),
    ("zoneid", "زون ايدي", "text"), ("uniqcode", "الكود الموحد", "text"),
    ("product_price", "سعر المنتج", "decimal"), ("quantity", "الكمية", "number"),
    ("total", "الإجمالي", "decimal"), ("contract_number", "رقم العقد", "text"),
    ("customer_id", "رقم المشترك", "text"), ("placeid", "رقم المنطقة", "text"),
    ("service_details", "تفاصيل الخدمة", "text"),
]
FIELD_MAP = {key: (label, typ) for key, label, typ in FIELD_LIBRARY}
SERVICE_LINK_KEY = {row[0]: row[5] for row in SERVICES}
RESOURCE_MODELS = {"plan": TelecomPlan, "denom": TelecomDenomination, "game": GameProduct, "digital": DigitalProduct, "option": ServiceOption}


def staff_only(user):
    return bool(user.is_authenticated and (user.is_staff or getattr(user, "role", None) == "admin"))


def dec(value, allow_empty=True):
    if value in (None, ""):
        if allow_empty:
            return None
        return Decimal("0")
    try:
        x = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise ValueError("القيمة المالية غير صالحة.") from exc
    if x < 0:
        raise ValueError("القيمة المالية لا يمكن أن تكون سالبة.")
    return x


def json_value(value):
    if not value:
        return {}
    try:
        return json.loads(value)
    except json.JSONDecodeError as exc:
        raise ValueError("JSON غير صالح.") from exc


def choose_link(service, provider):
    links = list(provider.links.filter(is_active=True).order_by("priority", "id"))
    key = SERVICE_LINK_KEY.get(service.code)
    if key:
        exact = next((x for x in links if x.code == key or x.code.endswith("-" + key)), None)
        if exact:
            return exact
    wanted = "query" if service.service_kind == Service.ServiceKinds.QUERY else "catalog" if service.service_kind == Service.ServiceKinds.CATALOG else "bill"
    candidates = [x for x in links if wanted in x.operation.lower() or wanted in x.code.lower()]
    return candidates[0] if candidates else (links[0] if links else None)


def service_context():
    return {
        "mains": MainServiceCategory.objects.all().order_by("sort_order", "id"),
        "categories": ServiceCategory.objects.select_related("main_category").all().order_by("main_category__sort_order", "sort_order", "id"),
        "services": Service.objects.select_related("category__main_category").prefetch_related("fields").all().order_by("category__main_category__sort_order", "category__sort_order", "sort_order", "id"),
        "field_library": FIELD_LIBRARY,
    }


@user_passes_test(staff_only, login_url="/admin/dashboard/login/")
def center(request, section="overview"):
    if request.method == "POST":
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
                        main_category=main, parent=parent,
                        slug=(request.POST.get("slug") or slugify(name, allow_unicode=True)).strip(),
                        defaults={"name": name, "description": request.POST.get("description", "").strip(), "sort_order": int(request.POST.get("sort_order", 0) or 0), "is_active": True},
                    )
                    messages.success(request, "تم حفظ الفئة.")
                elif action == "service":
                    service = Service.objects.filter(pk=request.POST.get("pk") or 0).first() or Service()
                    service.category = get_object_or_404(ServiceCategory, pk=request.POST.get("category"))
                    service.name = (request.POST.get("name") or "").strip()
                    service.code = (request.POST.get("code") or service.code or "").strip()
                    if not service.name or not service.code:
                        raise ValueError("اسم وكود الخدمة مطلوبان.")
                    service.slug = (request.POST.get("slug") or slugify(service.name, allow_unicode=True)).strip()
                    service.description = request.POST.get("description", "").strip()
                    service.service_kind = request.POST.get("service_kind", Service.ServiceKinds.PURCHASE)
                    service.requires_balance = request.POST.get("requires_balance") == "1"
                    service.pricing_mode = request.POST.get("pricing_mode", Service.PricingModes.FIXED)
                    service.price = dec(request.POST.get("price"), allow_empty=False)
                    service.min_amount = dec(request.POST.get("min_amount"))
                    service.max_amount = dec(request.POST.get("max_amount"))
                    service.currency = (request.POST.get("currency") or "YER").strip().upper()
                    service.icon = request.POST.get("icon", "").strip()
                    service.sort_order = int(request.POST.get("sort_order", 0) or 0)
                    metadata = dict(service.metadata or {})
                    for key in ("service_number", "price_usd", "price_sar", "employee_price", "submit_label", "unified_link_number", "duplicate_guard"):
                        metadata[key] = (request.POST.get(key) or "").strip()
                    service.metadata = metadata
                    service.is_active = True
                    service.save()
                    selected = {x for x in request.POST.getlist("field_keys") if x in FIELD_MAP}
                    for index, key in enumerate(FIELD_LIBRARY):
                        field_key = key[0]
                        if field_key in selected:
                            label, typ = FIELD_MAP[field_key]
                            ServiceField.objects.update_or_create(service=service, key=field_key, defaults={"label": label, "field_type": typ, "required": False, "sort_order": index * 10, "is_active": True})
                    ServiceField.objects.filter(service=service, key__in=FIELD_MAP).exclude(key__in=selected).update(is_active=False)
                    messages.success(request, "تم حفظ الخدمة والحقول.")
                elif action == "field":
                    service = get_object_or_404(Service, pk=request.POST.get("service"))
                    key = (request.POST.get("key") or "").strip()
                    if not key:
                        raise ValueError("مفتاح الحقل مطلوب.")
                    ServiceField.objects.update_or_create(
                        service=service, key=key,
                        defaults={"label": (request.POST.get("label") or key).strip(), "field_type": request.POST.get("field_type", "text"), "required": request.POST.get("required") == "1", "secret": request.POST.get("secret") == "1", "choices": json_value(request.POST.get("choices")), "validation": json_value(request.POST.get("validation")), "default_value": json_value(request.POST.get("default_value")), "sort_order": int(request.POST.get("sort_order", 0) or 0), "is_active": True},
                    )
                    messages.success(request, "تم حفظ الحقل المخصص.")
                elif action in RESOURCE_MODELS:
                    service = get_object_or_404(Service, pk=request.POST.get("service"), is_active=True)
                    model = RESOURCE_MODELS[action]
                    pk = request.POST.get("pk") or 0
                    obj = model.objects.filter(pk=pk).first() or model(service=service)
                    obj.service = service
                    obj.name = (request.POST.get("name") or "").strip()
                    obj.external_code = (request.POST.get("external_code") or "").strip()
                    if not obj.name or not obj.external_code:
                        raise ValueError("اسم العنصر والكود الخارجي مطلوبان.")
                    obj.sort_order = int(request.POST.get("sort_order", 0) or 0)
                    obj.is_active = True
                    if action == "plan":
                        obj.price = dec(request.POST.get("price"), allow_empty=False)
                        obj.quota = dec(request.POST.get("quota"))
                        obj.quota_unit = request.POST.get("quota_unit", "").strip()
                        obj.validity_days = int(request.POST["validity_days"]) if request.POST.get("validity_days") else None
                        obj.payment_type = request.POST.get("payment_type", "").strip()
                        obj.line_type = request.POST.get("line_type", "").strip()
                        meta = dict(obj.metadata or {})
                        for key in ("provider_num", "package_number", "price_usd", "price_sar", "employee_price"):
                            meta[key] = (request.POST.get(key) or "").strip()
                        meta.update(json_value(request.POST.get("metadata")))
                        obj.metadata = meta
                    elif action == "denom":
                        obj.face_value = dec(request.POST.get("face_value"), allow_empty=False)
                        obj.sale_price = dec(request.POST.get("sale_price"), allow_empty=False)
                        obj.payment_type = request.POST.get("payment_type", "").strip()
                        obj.line_type = request.POST.get("line_type", "").strip()
                        meta = dict(obj.metadata or {})
                        for key in ("provider_num", "price_usd", "price_sar", "employee_price"):
                            meta[key] = (request.POST.get(key) or "").strip()
                        meta.update(json_value(request.POST.get("metadata")))
                        obj.metadata = meta
                    elif action in {"game", "digital"}:
                        obj.price = dec(request.POST.get("price"), allow_empty=False)
                        obj.currency = (request.POST.get("currency") or "YER").strip().upper()
                        obj.validity_days = int(request.POST["validity_days"]) if request.POST.get("validity_days") else None
                        obj.metadata = json_value(request.POST.get("metadata"))
                    else:
                        obj.provider_num = (request.POST.get("provider_num") or "").strip()
                        obj.price = dec(request.POST.get("price"), allow_empty=False)
                        obj.currency = (request.POST.get("currency") or "YER").strip().upper()
                        obj.metadata = json_value(request.POST.get("metadata"))
                    obj.save()
                    messages.success(request, "تم حفظ المورد.")
                elif action == "toggle_resource":
                    model = RESOURCE_MODELS.get(request.POST.get("kind"))
                    if not model:
                        raise ValueError("نوع المورد غير معروف.")
                    obj = get_object_or_404(model, pk=request.POST.get("pk"))
                    obj.is_active = not obj.is_active
                    obj.save(update_fields=["is_active"])
                    messages.success(request, "تم تحديث الحالة.")
                elif action == "delete_resource":
                    kind = request.POST.get("kind")
                    model = RESOURCE_MODELS.get(kind)
                    if not model:
                        raise ValueError("نوع المورد غير معروف.")
                    obj = get_object_or_404(model, pk=request.POST.get("pk"))
                    if ServiceTransaction.objects.filter(item_id=obj.pk, item_type={"plan": "telecom_plans", "denom": "telecom_denominations", "game": "game_products", "digital": "digital_products", "option": "service_options"}.get(kind, "")).exists():
                        obj.is_active = False
                        obj.save(update_fields=["is_active"])
                        messages.warning(request, "العنصر مرتبط بعملية تاريخية، لذلك تم إيقافه بدل حذفه.")
                    else:
                        obj.delete()
                        messages.success(request, "تم حذف المورد.")
                else:
                    raise ValueError("عملية غير معروفة.")
        except Exception as exc:
            messages.error(request, f"تعذر التنفيذ: {exc}")
        return redirect(request.POST.get("next") or request.path)

    context = service_context()
    context.update({
        "section": section,
        "edit_service": Service.objects.prefetch_related("fields").filter(pk=request.GET.get("edit_service") or 0).first(),
        "edit_plan": TelecomPlan.objects.filter(pk=request.GET.get("edit_plan") or 0).first(),
        "edit_denom": TelecomDenomination.objects.filter(pk=request.GET.get("edit_denom") or 0).first(),
        "edit_game": GameProduct.objects.filter(pk=request.GET.get("edit_game") or 0).first(),
        "edit_digital": DigitalProduct.objects.filter(pk=request.GET.get("edit_digital") or 0).first(),
        "edit_option": ServiceOption.objects.filter(pk=request.GET.get("edit_option") or 0).first(),
        "plans": TelecomPlan.objects.select_related("service").order_by("service__name", "sort_order", "id"),
        "denoms": TelecomDenomination.objects.select_related("service").order_by("service__name", "sort_order", "id"),
        "games": GameProduct.objects.select_related("service").order_by("service__name", "sort_order", "id"),
        "digital": DigitalProduct.objects.select_related("service").order_by("service__name", "sort_order", "id"),
        "options": ServiceOption.objects.select_related("service").order_by("service__name", "sort_order", "id"),
    })
    return render(request, "services/admin_v4.html", context)


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
                    link = choose_link(service, provider)
                    if not link:
                        raise ValueError(f"لا يوجد مسار API فعال للخدمة: {service.name}")
                    ServiceDistribution.objects.update_or_create(service=service, provider_link=link, defaults={"priority": priority, "conditions": {}, "is_active": True})
            messages.success(request, f"تم حفظ توزيع {len(selected)} خدمة.")
        except Exception as exc:
            messages.error(request, f"تعذر حفظ التوزيع: {exc}")
        return redirect(f"{request.path}?provider={request.POST.get('provider', '')}")
    providers = list(ProviderConnection.objects.filter(is_active=True).prefetch_related("links").order_by("name"))
    provider_id = request.GET.get("provider") or (str(providers[0].id) if providers else "")
    selected_services = set(ServiceDistribution.objects.filter(is_active=True, provider_link__provider_id=provider_id).values_list("service_id", flat=True)) if provider_id else set()
    groups = []
    for main in MainServiceCategory.objects.filter(is_active=True).order_by("sort_order", "id"):
        items = []
        for category in main.categories.filter(is_active=True).order_by("sort_order", "id"):
            items.extend((category.name, service) for service in category.services.filter(is_active=True).order_by("sort_order", "id"))
        if items:
            groups.append((main, items))
    return render(request, "services/distribution_v4.html", {"providers": providers, "selected_provider_id": provider_id, "selected_services": selected_services, "groups": groups})
