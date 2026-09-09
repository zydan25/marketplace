from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.text import slugify

from .models import Service
from .settings_models import ServiceSetting


GROUP_LABELS = {
    "yemen_mobile": "يمن موبايل",
    "sabafon_north": "سبأفون - شمال",
    "sabafon_south": "سبأفون - جنوب",
    "you": "يو",
    "yemen4g": "يمن فورجي",
    "yemen_net": "يمن نت",
    "wai": "واي",
    "transfers": "الحوالات",
    "general_payments": "خدمات التسديد العامة",
    "general": "عام",
}


def staff_only(user):
    return bool(user.is_authenticated and (user.is_staff or getattr(user, "role", None) == "admin"))


def _group_label(value):
    return GROUP_LABELS.get(value, value.replace("_", " ").strip() or "عام")


def _parse_value(raw, setting_type):
    raw = (raw or "").strip()
    if setting_type == ServiceSetting.Types.BOOLEAN:
        return raw.lower() in {"1", "true", "yes", "on", "نعم"}
    if setting_type == ServiceSetting.Types.JSON:
        if not raw:
            return None
        import json
        return json.loads(raw)
    return raw or None


@user_passes_test(staff_only, login_url="/admin/dashboard/login/")
def settings_center(request):
    if request.method == "POST":
        action = request.POST.get("action", "")
        try:
            with transaction.atomic():
                if action == "save":
                    pk = request.POST.get("pk") or 0
                    setting = ServiceSetting.objects.filter(pk=pk).first()
                    is_new = setting is None
                    if is_new:
                        setting = ServiceSetting(is_system=False)

                    raw_key = (request.POST.get("key") or "").strip()
                    raw_name = (request.POST.get("name") or "").strip()
                    raw_group = (request.POST.get("group") or "").strip()

                    # Forms for existing/system settings intentionally send only pk + service.
                    # Preserve the immutable identity fields instead of rejecting the update.
                    if is_new and (not raw_key or not raw_name):
                        raise ValueError("مفتاح واسم الإعداد مطلوبان عند إضافة إعداد جديد.")

                    if raw_key:
                        setting.key = slugify(raw_key, allow_unicode=True).replace("-", "_") or raw_key
                    elif is_new:
                        raise ValueError("مفتاح الإعداد مطلوب عند الإضافة.")

                    if raw_name:
                        setting.name = raw_name
                    elif is_new:
                        raise ValueError("اسم الإعداد مطلوب عند الإضافة.")

                    if raw_group:
                        setting.group = slugify(raw_group, allow_unicode=True).replace("-", "_") or "general"

                    if "description" in request.POST:
                        setting.description = (request.POST.get("description") or "").strip()

                    posted_type = (request.POST.get("setting_type") or "").strip()
                    if posted_type:
                        if posted_type not in {choice[0] for choice in ServiceSetting.Types.choices}:
                            raise ValueError("نوع الإعداد غير صالح.")
                        setting.setting_type = posted_type
                    elif is_new:
                        setting.setting_type = ServiceSetting.Types.SERVICE

                    service_id = request.POST.get("service") or None
                    if setting.setting_type == ServiceSetting.Types.SERVICE:
                        if service_id:
                            setting.service = get_object_or_404(Service, pk=service_id, is_active=True)
                        elif is_new:
                            raise ValueError("إعداد الخدمة يجب أن يرتبط بخدمة.")
                        # For an existing setting, omitting service means keep its current service.
                        if setting.service_id is None:
                            raise ValueError("إعداد الخدمة يحتاج إلى خدمة فعلية.")
                        setting.value = None
                    else:
                        setting.service = None
                        if "value" in request.POST:
                            setting.value = _parse_value(request.POST.get("value"), setting.setting_type)

                    setting.is_active = True
                    if "sort_order" in request.POST:
                        setting.sort_order = max(0, int(request.POST.get("sort_order", 0) or 0))
                    setting.save()
                    messages.success(request, "تم حفظ الإعداد بنجاح.")
                elif action == "toggle":
                    setting = get_object_or_404(ServiceSetting, pk=request.POST.get("pk"))
                    setting.is_active = not setting.is_active
                    setting.save(update_fields=["is_active", "updated_at"])
                    messages.success(request, "تم تحديث حالة الإعداد.")
                elif action == "delete":
                    setting = get_object_or_404(ServiceSetting, pk=request.POST.get("pk"))
                    if setting.is_system:
                        raise ValueError("الإعدادات الأساسية لا تُحذف؛ يمكن إيقافها فقط.")
                    setting.delete()
                    messages.success(request, "تم حذف الإعداد المخصص.")
                else:
                    raise ValueError("عملية غير معروفة.")
        except Exception as exc:
            messages.error(request, f"تعذر حفظ الإعداد: {exc}")
        return redirect(request.path)

    settings_qs = ServiceSetting.objects.select_related("service", "service__category", "service__category__main_category").all()
    grouped = []
    for group, rows in _group_settings(settings_qs):
        grouped.append({"key": group, "label": _group_label(group), "settings": rows})

    edit = ServiceSetting.objects.select_related("service").filter(pk=request.GET.get("edit") or 0).first()
    services = Service.objects.select_related("category__main_category").filter(is_active=True).order_by("category__main_category__sort_order", "category__sort_order", "sort_order", "id")
    return render(
        request,
        "services/settings.html",
        {
            "groups": grouped,
            "edit": edit,
            "services": services,
            "type_choices": ServiceSetting.Types.choices,
            "group_labels": GROUP_LABELS,
        },
    )


def _group_settings(queryset):
    current = None
    rows = []
    for setting in queryset.order_by("group", "sort_order", "id"):
        if current is None:
            current = setting.group
        if setting.group != current:
            yield current, rows
            current = setting.group
            rows = []
        rows.append(setting)
    if current is not None:
        yield current, rows
