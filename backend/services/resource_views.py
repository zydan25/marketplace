from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from .models import DigitalProduct, GameProduct, MainServiceCategory, Service, ServiceTransaction, TelecomDenomination, TelecomPlan


def staff_only(user):
    return bool(user.is_authenticated and (user.is_staff or getattr(user, "role", None) == "admin"))


def dec(value):
    if value in (None, ""):
        return Decimal("0")
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError("القيمة المالية غير صالحة.") from exc


def integer(value):
    return None if value in (None, "") else int(value)


def has_history(kind, obj_id):
    return ServiceTransaction.objects.filter(item_type=kind, item_id=obj_id).exists()


def _scoped_service(request):
    service = get_object_or_404(Service.objects.select_related("category__main_category"), pk=request.POST.get("service"), is_active=True)
    main_id = (request.POST.get("main_category") or "").strip()
    if main_id.isdigit() and service.category.main_category_id != int(main_id):
        raise ValueError("الخدمة لا تنتمي إلى الفئة الرئيسية المحددة.")
    return service


def _filter_resource(qs, main_id, service_id, q, sort, price_field="price"):
    if main_id.isdigit():
        qs = qs.filter(service__category__main_category_id=int(main_id))
    if service_id.isdigit():
        qs = qs.filter(service_id=int(service_id))
    if q:
        qs = qs.filter(Q(name__icontains=q) | Q(external_code__icontains=q) | Q(service__name__icontains=q))
    if sort == "price":
        return qs.order_by(price_field, "id")
    if sort == "newest":
        return qs.order_by("-id")
    return qs.order_by("name", "id")


@user_passes_test(staff_only, login_url="/admin/dashboard/login/")
def resources(request):
    if request.method == "POST":
        action = request.POST.get("action", "")
        try:
            with transaction.atomic():
                if action in {"plan", "denom", "game", "digital"}:
                    service = _scoped_service(request)
                    name = (request.POST.get("name") or "").strip()
                    code = (request.POST.get("external_code") or "").strip()
                    if not name or not code:
                        raise ValueError("اسم العنصر والكود الخارجي مطلوبان.")
                    if action == "plan":
                        TelecomPlan.objects.update_or_create(service=service, external_code=code, defaults={
                            "name": name, "provider_num": request.POST.get("provider_num", "").strip(),
                            "price": dec(request.POST.get("price")), "quota": dec(request.POST.get("quota")) if request.POST.get("quota") else None,
                            "quota_unit": request.POST.get("quota_unit", "").strip(), "validity_days": integer(request.POST.get("validity_days")),
                            "payment_type": request.POST.get("payment_type", "").strip(), "line_type": request.POST.get("line_type", "").strip(),
                            "metadata": {"package_number": request.POST.get("package_number", "").strip(), "price_usd": request.POST.get("price_usd", "").strip(), "price_sar": request.POST.get("price_sar", "").strip(), "employee_price": request.POST.get("employee_price", "").strip()},
                            "sort_order": int(request.POST.get("sort_order", 0) or 0), "is_active": True,
                        })
                    elif action == "denom":
                        TelecomDenomination.objects.update_or_create(service=service, external_code=code, defaults={
                            "name": name, "provider_num": request.POST.get("provider_num", "").strip(),
                            "face_value": dec(request.POST.get("face_value")), "sale_price": dec(request.POST.get("sale_price")),
                            "payment_type": request.POST.get("payment_type", "").strip(), "line_type": request.POST.get("line_type", "").strip(),
                            "metadata": {"price_usd": request.POST.get("price_usd", "").strip(), "price_sar": request.POST.get("price_sar", "").strip(), "employee_price": request.POST.get("employee_price", "").strip()},
                            "sort_order": int(request.POST.get("sort_order", 0) or 0), "is_active": True,
                        })
                    elif action == "game":
                        GameProduct.objects.update_or_create(service=service, external_code=code, defaults={
                            "name": name, "price": dec(request.POST.get("price")), "currency": request.POST.get("currency", "YER").strip().upper(),
                            "metadata": {"player_field": request.POST.get("player_field", "").strip()}, "sort_order": int(request.POST.get("sort_order", 0) or 0), "is_active": True,
                        })
                    else:
                        DigitalProduct.objects.update_or_create(service=service, external_code=code, defaults={
                            "name": name, "price": dec(request.POST.get("price")), "currency": request.POST.get("currency", "YER").strip().upper(),
                            "validity_days": integer(request.POST.get("validity_days")), "metadata": {"details": request.POST.get("details", "").strip()},
                            "sort_order": int(request.POST.get("sort_order", 0) or 0), "is_active": True,
                        })
                    messages.success(request, "تم حفظ العنصر بنجاح.")
                elif action == "toggle":
                    mapping = {"plan": TelecomPlan, "denom": TelecomDenomination, "game": GameProduct, "digital": DigitalProduct}
                    model = mapping.get(request.POST.get("kind"))
                    if model is None:
                        raise ValueError("نوع العنصر غير معروف.")
                    obj = get_object_or_404(model, pk=request.POST.get("pk")); obj.is_active = not obj.is_active; obj.save(update_fields=["is_active"])
                    messages.success(request, "تم تحديث حالة العنصر.")
                elif action == "delete":
                    mapping = {"plan": TelecomPlan, "denom": TelecomDenomination, "game": GameProduct, "digital": DigitalProduct}; kind = request.POST.get("kind"); model = mapping.get(kind)
                    if model is None:
                        raise ValueError("نوع العنصر غير معروف.")
                    obj = get_object_or_404(model, pk=request.POST.get("pk"))
                    if has_history(kind, obj.pk):
                        obj.is_active = False; obj.save(update_fields=["is_active"]); messages.warning(request, "العنصر مستخدم في عمليات تاريخية؛ تم إيقافه بدل حذفه.")
                    else:
                        obj.delete(); messages.success(request, "تم حذف العنصر بأمان.")
                else:
                    raise ValueError("عملية غير معروفة.")
        except Exception as exc:
            messages.error(request, f"تعذر تنفيذ العملية: {exc}")
        return redirect(request.path)

    main_id = (request.GET.get("main_category") or request.GET.get("main") or "").strip()
    service_id = (request.GET.get("service") or "").strip()
    resource_type = (request.GET.get("type") or "").strip().lower()
    q = (request.GET.get("q") or "").strip()
    sort = (request.GET.get("sort") or "name").strip().lower()

    services = Service.objects.select_related("category__main_category").filter(is_active=True)
    if main_id.isdigit(): services = services.filter(category__main_category_id=int(main_id))
    services = services.order_by("category__main_category__sort_order", "category__sort_order", "name", "id")
    if service_id.isdigit(): services = services.filter(pk=int(service_id))

    plans = _filter_resource(TelecomPlan.objects.select_related("service__category__main_category").filter(is_active=True), main_id, service_id, q, sort, "price")
    denoms = _filter_resource(TelecomDenomination.objects.select_related("service__category__main_category").filter(is_active=True), main_id, service_id, q, sort, "sale_price")
    games = _filter_resource(GameProduct.objects.select_related("service__category__main_category").filter(is_active=True), main_id, service_id, q, sort, "price")
    digital = _filter_resource(DigitalProduct.objects.select_related("service__category__main_category").filter(is_active=True), main_id, service_id, q, sort, "price")

    return render(request, "services/resources_manage.html", {
        "main_categories": MainServiceCategory.objects.filter(is_active=True).order_by("sort_order", "id"),
        "services": services,
        "plans": plans[:300], "denoms": denoms[:300], "games": games[:300], "digital": digital[:300],
        "filters": {"main": main_id, "service": service_id, "type": resource_type, "q": q, "sort": sort},
    })
