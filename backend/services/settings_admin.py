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
                    key = (request.POST.get("key") or "").strip()
                    name = (request.POST.get("name") or "").strip()
                    if not key or not name:
                        raise ValueError("مفتاح واسم الإعداد مطلوبان.")
                    setting_type = request.POST.get("setting_type", ServiceSetting.Types.SERVICE)
                    if setting_type not in {choice[0] for choice in ServiceSetting.Types.choices}:
                        raise ValueError("نوع الإعداد غير صالح.")
                    setting = ServiceSetting.objects.filter(pk=request.POST.get("pk") or 0).first()
                    if not setting:
                        setting = ServiceSetting()
                    setting.key = slugify(key, allow_unicode=True).replace("-", "_") or key
                    setting.name = name
                    setting.group = slugify((request.POST.get("group") or "general").strip(), allow_unicode=True).replace("-", "_") or "general"
                    setting.description = (request.POST.get("description") or "").strip()
                    setting.setting_type = setting_type
                    service_id = request.POST.get("service") or None
                    if setting_type == ServiceSetting.Types.SERVICE:
                        if not service_id:
                            raise ValueError("إعداد الخدمة يجب أن يرتبط بخدمة.")
                        setting.service = get_object_or_404(Service, pk=service_id, is_active=True)
                        setting.value = None
                    else:
                        setting.service = None
                        setting.value = _parse_value(request.POST.get("value"), setting_type)
                    setting.is_system = bool(setting.is_system and not setting.pk) or setting.is_system
                    setting.is_active = True
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
