import json
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.text import slugify

from .models import (
    DigitalProduct,
    GameProduct,
    MainServiceCategory,
    ProviderConnection,
    Service,
    ServiceCategory,
    ServiceDistribution,
    ServiceField,
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
    ("player_id", "رقم اللاعب", "text"),
    ("player_name", "اسم اللاعب", "text"),
    ("zone_id", "زون ايدي", "text"),
    ("uniqcode", "الكود الموحد", "text"),
    ("product_price", "سعر المنتج", "decimal"),
    ("quantity", "الكمية", "number"),
    ("total", "الإجمالي", "decimal"),
    ("contract_number", "رقم العقد", "text"),
    ("service_details", "تفاصيل الخدمة", "text"),
]
FIELD_MAP = {key: (label, field_type) for key, label, field_type in FIELD_LIBRARY}


def staff_only(user):
    return bool(user.is_authenticated and (user.is_staff or getattr(user, "role", None) == "admin"))


def _dec(value, default="0"):
    if value in (None, ""):
        return Decimal(default)
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError("القيمة المالية غير صالحة.") from exc


def _json(value, fallback):
    if not value:
        return fallback
    try:
        return json.loads(value)
    except json.JSONDecodeError as exc:
        raise ValueError("JSON غير صالح.") from exc


def _ctx(section):
    return {
        "section": section,
        "mains": MainServiceCategory.objects.all(),
        "categories": ServiceCategory.objects.select_related("main_category", "parent").all(),
        "services": Service.objects.select_related("category__main_category").prefetch_related("fields").all(),
        "fields": ServiceField.objects.select_related("service").all(),
        "providers": ProviderConnection.objects.prefetch_related("links").all(),
        "links": __import__("services.models", fromlist=["ProviderLink"]).ProviderLink.objects.select_related("provider").all(),
        "distributions": ServiceDistribution.objects.select_related("service", "provider_link__provider").all(),
        "plans": TelecomPlan.objects.select_related("service").all(),
        "denoms": TelecomDenomination.objects.select_related("service").all(),
        "games": GameProduct.objects.select_related("service").all(),
        "digital": DigitalProduct.objects.select_related("service").all(),
        "transactions_count": ServiceTransaction.objects.count(),
        "field_library": FIELD_LIBRARY,
    }


def _choose_link(service, provider):
    links = list(provider.links.filter(is_active=True).order_by("priority", "id"))
    if not links:
        return None
    meta = service.metadata or {}
    exact_code = str(meta.get("provider_link_code") or "").strip()
    if exact_code:
        exact = next((link for link in links if link.code == exact_code), None)
        if exact:
            return exact
    operation = str(meta.get("provider_operation") or "").lower().strip()
    if not operation:
        operation = "query" if service.service_kind == Service.ServiceKinds.QUERY else "catalog" if service.service_kind == Service.ServiceKinds.CATALOG else "bill"
    candidates = [link for link in links if link.operation.lower() == operation or operation in link.code.lower()]
    if "offer" in service.code.lower():
        offers = [link for link in candidates if "offer" in link.code.lower() or "offer" in link.operation.lower()]
        if offers:
            return offers[0]
    return candidates[0] if candidates else links[0]


def _save_fields(service, selected):
    selected = {key for key in selected if key in FIELD_MAP}
    for index, key in enumerate(selected):
        label, field_type = FIELD_MAP[key]
        ServiceField.objects.update_or_create(
            service=service,
            key=key,
            defaults={"label": label, "field_type": field_type, "required": False, "sort_order": index * 10, "is_active": True},
        )
    ServiceField.objects.filter(service=service, key__in=FIELD_MAP).exclude(key__in=selected).update(is_active=False)


@user_passes_test(staff_only, login_url="/admin/dashboard/login/")
def service_center(request, section="overview"):
    if request.method == "POST":
        try:
            action = request.POST.get("action", "")
            with transaction.atomic():
                if action == "main":
                    name = (request.POST.get("name") or "").strip()
                    if not name:
                        raise ValueError("اسم الفئة الرئيسية مطلوب.")
                    MainServiceCategory.objects.update_or_create(
                        slug=(request.POST.get("slug") or slugify(name, allow_unicode=True)).strip(),
                        defaults={
                            "name": name,
                            "description": request.POST.get("description", "").strip(),
                            "icon": request.POST.get("icon", "").strip(),
                            "sort_order": int(request.POST.get("sort_order", 0) or 0),
                            "is_active": True,
                        },
                    )
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
                        defaults={
                            "name": name,
                            "description": request.POST.get("description", "").strip(),
                            "icon": request.POST.get("icon", "").strip(),
                            "sort_order": int(request.POST.get("sort_order", 0) or 0),
                            "is_active": True,
                        },
                    )
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
                    service.price = _dec(request.POST.get("price"))
                    service.min_amount = _dec(request.POST.get("min_amount")) if request.POST.get("min_amount") else None
                    service.max_amount = _dec(request.POST.get("max_amount")) if request.POST.get("max_amount") else None
                    service.currency = (request.POST.get("currency") or "YER").strip().upper()
                    service.icon = request.POST.get("icon", "").strip()
                    service.sort_order = int(request.POST.get("sort_order", 0) or 0)
                    meta = dict(service.metadata or {})
                    for key in (
                        "service_number", "price_usd", "price_sar", "employee_price",
                        "submit_label", "unified_link_number", "duplicate_guard",
                        "provider_link_code", "provider_operation",
                    ):
                        meta[key] = (request.POST.get(key) or "").strip()
                    service.metadata = meta
                    service.is_active = True
                    service.save()
                    _save_fields(service, request.POST.getlist("field_keys"))
                elif action == "field":
                    service = get_object_or_404(Service, pk=request.POST.get("service"))
                    key = (request.POST.get("key") or "").strip()
                    if not key:
                        raise ValueError("مفتاح الحقل مطلوب.")
                    ServiceField.objects.update_or_create(
                        service=service,
                        key=key,
                        defaults={
                            "label": (request.POST.get("label") or key).strip(),
                            "field_type": request.POST.get("field_type", "text"),
                            "required": request.POST.get("required") == "1",
                            "secret": request.POST.get("secret") == "1",
                            "choices": _json(request.POST.get("choices"), []),
                            "validation": _json(request.POST.get("validation"), {}),
                            "default_value": _json(request.POST.get("default_value"), None),
                            "sort_order": int(request.POST.get("sort_order", 0) or 0),
                            "is_active": True,
                        },
                    )
                elif action in {"telecom_plan", "telecom_denom", "game", "digital"}:
                    service = get_object_or_404(Service, pk=request.POST.get("service"))
                    external_code = (request.POST.get("external_code") or "").strip()
                    name = (request.POST.get("name") or "").strip()
                    if not name or not external_code:
                        raise ValueError("الاسم والكود الخارجي مطلوبان.")
                    if action == "telecom_plan":
                        TelecomPlan.objects.update_or_create(
                            service=service,
                            external_code=external_code,
                            defaults={
                                "name": name,
                                "provider_num": request.POST.get("provider_num", "").strip(),
                                "package_number": request.POST.get("package_number", "").strip(),
                                "price": _dec(request.POST.get("price")),
                                "price_usd": _dec(request.POST.get("price_usd")) if request.POST.get("price_usd") else None,
                                "price_sar": _dec(request.POST.get("price_sar")) if request.POST.get("price_sar") else None,
                                "employee_price": _dec(request.POST.get("employee_price")),
                                "quota": _dec(request.POST.get("quota")) if request.POST.get("quota") else None,
                                "quota_unit": request.POST.get("quota_unit", "").strip(),
                                "validity_days": int(request.POST["validity_days"]) if request.POST.get("validity_days") else None,
                                "payment_type": request.POST.get("payment_type", "").strip(),
                                "line_type": request.POST.get("line_type", "").strip(),
                                "metadata": _json(request.POST.get("metadata"), {}),
                            },
                        )
                    elif action == "telecom_denom":
                        TelecomDenomination.objects.update_or_create(
                            service=service,
                            external_code=external_code,
                            defaults={
                                "name": name,
                                "provider_num": request.POST.get("provider_num", "").strip(),
                                "face_value": _dec(request.POST.get("face_value")),
                                "sale_price": _dec(request.POST.get("sale_price")),
                                "price_usd": _dec(request.POST.get("price_usd")) if request.POST.get("price_usd") else None,
                                "price_sar": _dec(request.POST.get("price_sar")) if request.POST.get("price_sar") else None,
                                "employee_price": _dec(request.POST.get("employee_price")),
                                "payment_type": request.POST.get("payment_type", "").strip(),
                                "line_type": request.POST.get("line_type", "").strip(),
                                "metadata": _json(request.POST.get("metadata"), {}),
                            },
                        )
                    elif action == "game":
                        GameProduct.objects.update_or_create(
                            service=service,
                            external_code=external_code,
                            defaults={
                                "name": name,
                                "price": _dec(request.POST.get("price")),
                                "currency": request.POST.get("currency", "YER").strip().upper(),
                                "validity_days": int(request.POST["validity_days"]) if request.POST.get("validity_days") else None,
                                "metadata": _json(request.POST.get("metadata"), {}),
                            },
                        )
                    else:
                        DigitalProduct.objects.update_or_create(
                            service=service,
                            external_code=external_code,
                            defaults={
                                "name": name,
                                "price": _dec(request.POST.get("price")),
                                "currency": request.POST.get("currency", "YER").strip().upper(),
                                "validity_days": int(request.POST["validity_days"]) if request.POST.get("validity_days") else None,
                                "metadata": _json(request.POST.get("metadata"), {}),
                            },
                        )
                elif action == "toggle":
                    mapping = {"main": MainServiceCategory, "category": ServiceCategory, "service": Service, "field": ServiceField}
                    obj = get_object_or_404(mapping[request.POST.get("model")], pk=request.POST.get("pk"))
                    obj.is_active = not obj.is_active
                    obj.save(update_fields=["is_active"])
                elif action == "delete_service":
                    service = get_object_or_404(Service, pk=request.POST.get("pk"))
                    if service.transactions.exists():
                        service.is_active = False
                        service.save(update_fields=["is_active"])
                        messages.warning(request, "للخدمة عمليات تاريخية؛ تم إيقافها بدل حذفها.")
                    else:
                        ServiceDistribution.objects.filter(service=service).delete()
                        ServiceField.objects.filter(service=service).delete()
                        TelecomPlan.objects.filter(service=service).delete()
                        TelecomDenomination.objects.filter(service=service).delete()
                        GameProduct.objects.filter(service=service).delete()
                        DigitalProduct.objects.filter(service=service).delete()
                        service.delete()
                        messages.success(request, "تم حذف الخدمة وبياناتها التابعة بأمان.")
                else:
                    raise ValueError("عملية غير معروفة.")
            if action not in {"delete_service"}:
                messages.success(request, "تم الحفظ بنجاح.")
        except (ValueError, InvalidOperation) as exc:
            messages.error(request, str(exc))
        except Exception as exc:
            messages.error(request, f"تعذر الحفظ: {exc}")
        return redirect(request.POST.get("next") or request.path)

    ctx = _ctx(section)
    service_id = request.GET.get("edit_service")
    ctx["editing_service"] = Service.objects.prefetch_related("fields").filter(pk=service_id).first() if service_id else None
    return render(request, "services/legacy_dashboard.html", ctx)


@user_passes_test(staff_only, login_url="/admin/dashboard/login/")
def provider_setup_v2(request):
    if request.method == "POST":
        action = request.POST.get("action", "save")
        try:
            provider = get_object_or_404(ProviderConnection, pk=request.POST.get("provider")) if request.POST.get("provider") else None
            with transaction.atomic():
                if action == "save":
                    name = (request.POST.get("name") or "").strip()
                    if not name:
                        raise ValueError("اسم الربطية مطلوب.")
                    provider = create_or_update_sanaacash_provider(
                        code=(request.POST.get("code") or slugify(name)).strip(),
                        name=name,
                        userid=request.POST.get("userid", "").strip(),
                        username=request.POST.get("username", "").strip(),
                        password=request.POST.get("password") or "",
                        note=request.POST.get("note", "").strip(),
                        base_url=request.POST.get("base_url", "").strip(),
                        domain_name="",
                    )
                    messages.success(request, "تم حفظ الربطية وتهيئة المسارات القياسية.")
                elif action == "balance":
                    result = ProviderClient(provider).check_balance()
                    if result.success:
                        messages.success(request, f"الرصيد: {result.response.get('balance')}")
                    else:
                        messages.error(request, result.description or "تعذر فحص الرصيد")
                elif action == "activate":
                    provider.is_active = True
                    provider.links.update(is_active=True)
                    provider.save(update_fields=["is_active", "updated_at"])
                elif action in {"archive", "delete"}:
                    has_transactions = provider.links.filter(transactions__isnull=False).exists()
                    if has_transactions:
                        ServiceDistribution.objects.filter(provider_link__provider=provider).update(is_active=False)
                        provider.links.update(is_active=False)
                        provider.is_active = False
                        provider.save(update_fields=["is_active", "updated_at"])
                        messages.warning(request, "للربطية عمليات تاريخية؛ تم أرشفتها بدل حذفها.")
                    else:
                        ServiceDistribution.objects.filter(provider_link__provider=provider).delete()
                        provider.links.all().delete()
                        provider.delete()
                        messages.success(request, "تم حذف الربطية بأمان.")
                else:
                    raise ValueError("عملية غير معروفة")
        except Exception as exc:
            messages.error(request, f"تعذر تنفيذ العملية: {exc}")
        return redirect(request.path)
    return render(request, "services/provider_setup_v2.html", {"providers": ProviderConnection.objects.prefetch_related("links").all()})


@user_passes_test(staff_only, login_url="/admin/dashboard/login/")
def distribution_v2(request):
    if request.method == "POST":
        try:
            provider = get_object_or_404(ProviderConnection, pk=request.POST.get("provider"), is_active=True)
            selected = {int(value) for value in request.POST.getlist("services") if value.isdigit()}
            priority = max(1, int(request.POST.get("priority", 100) or 100))
            with transaction.atomic():
                ServiceDistribution.objects.filter(provider_link__provider=provider).update(is_active=False)
                for service in Service.objects.filter(pk__in=selected, is_active=True):
                    link = _choose_link(service, provider)
                    if not link:
                        raise ValueError(f"لا يوجد مسار API فعال للخدمة: {service.name}")
                    ServiceDistribution.objects.update_or_create(
                        service=service,
                        provider_link=link,
                        defaults={"priority": priority, "is_active": True, "conditions": {}},
                    )
            messages.success(request, f"تم حفظ توزيع {len(selected)} خدمة للربطية {provider.name}.")
        except Exception as exc:
            messages.error(request, f"تعذر حفظ التوزيع: {exc}")
        return redirect(f"{request.path}?provider={request.POST.get('provider', '')}")

    providers = list(ProviderConnection.objects.filter(is_active=True).prefetch_related("links").order_by("name"))
    selected_provider_id = request.GET.get("provider") or (str(providers[0].id) if providers else "")
    selected_services = (
        set(ServiceDistribution.objects.filter(is_active=True, provider_link__provider_id=selected_provider_id).values_list("service_id", flat=True))
        if selected_provider_id
        else set()
    )
    groups = []
    for main in MainServiceCategory.objects.filter(is_active=True).order_by("sort_order", "id"):
        items = []
        for category in main.categories.filter(is_active=True).order_by("sort_order", "id"):
            items.extend((category.name, service) for service in category.services.filter(is_active=True).order_by("sort_order", "id"))
        if items:
            groups.append((main, items))
    return render(
        request,
        "services/distribution_v2.html",
        {"providers": providers, "selected_provider_id": selected_provider_id, "selected_services": selected_services, "groups": groups},
    )
