from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_http_methods

from .models import StorefrontSection, VendorProfile


def _can_edit(user, section):
    if user.is_staff or getattr(user, "role", None) == "admin":
        return True
    return getattr(user, "role", None) == "vendor" and section.vendor_id and section.vendor.owner_id == user.id


@staff_member_required
def visual_editor(request):
    sections = StorefrontSection.objects.select_related("vendor").all().order_by("vendor_id", "sort_order", "id")
    return render(request, "admin/marketplace/storefront_editor.html", {"sections": sections})


@staff_member_required
@require_http_methods(["POST"])
def update_section(request, pk):
    section = get_object_or_404(StorefrontSection, pk=pk)
    if not _can_edit(request.user, section):
        return JsonResponse({"detail": "ليس لديك صلاحية تعديل هذا القسم."}, status=403)
    import json
    try:
        payload = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"detail": "JSON غير صالح."}, status=400)
    section.title = str(payload.get("title", section.title))[:180]
    section.sort_order = max(0, int(payload.get("sort_order", section.sort_order)))
    section.is_visible = bool(payload.get("is_visible", section.is_visible))
    config = payload.get("config")
    if config is not None:
        if not isinstance(config, dict):
            return JsonResponse({"detail": "إعدادات القسم يجب أن تكون JSON object."}, status=400)
        config["__editor_version"] = 1
        section.config = config
    section.save(update_fields=["title", "sort_order", "is_visible", "config", "updated_at"])
    return JsonResponse({"ok": True, "id": section.id, "title": section.title, "sort_order": section.sort_order, "is_visible": section.is_visible, "config": section.config})


@staff_member_required
@require_http_methods(["POST"])
def reorder_sections(request):
    import json
    try:
        payload = json.loads(request.body or "{}")
        ids = [int(value) for value in payload.get("ids", [])]
    except (json.JSONDecodeError, TypeError, ValueError):
        return JsonResponse({"detail": "قائمة الترتيب غير صالحة."}, status=400)
    sections = {section.id: section for section in StorefrontSection.objects.filter(id__in=ids).select_related("vendor")}
    if set(sections) != set(ids):
        return JsonResponse({"detail": "بعض الأقسام غير موجودة."}, status=400)
    if not (request.user.is_staff or getattr(request.user, "role", None) == "admin"):
        for section in sections.values():
            if not _can_edit(request.user, section):
                return JsonResponse({"detail": "لا يمكنك إعادة ترتيب أقسام لا تملكها."}, status=403)
    for index, section_id in enumerate(ids):
        section = sections[section_id]
        section.sort_order = index
        section.save(update_fields=["sort_order", "updated_at"])
    return JsonResponse({"ok": True})
