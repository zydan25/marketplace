import json

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_http_methods

from .models import StorefrontSection


def _is_admin(user):
    return user.is_staff or getattr(user, "role", None) == "admin"


def _can_edit(user, section):
    if _is_admin(user):
        return True
    return getattr(user, "role", None) == "vendor" and section.vendor_id and section.vendor.owner_id == user.id


def _visible_sections_for_editor(user):
    qs = StorefrontSection.objects.select_related("vendor", "vendor__owner")
    if _is_admin(user):
        return qs.order_by("vendor_id", "sort_order", "id")
    if getattr(user, "role", None) == "vendor":
        return qs.filter(vendor__owner=user).order_by("sort_order", "id")
    return qs.none()


@login_required
def visual_editor(request):
    if not (_is_admin(request.user) or getattr(request.user, "role", None) == "vendor"):
        return JsonResponse({"detail": "لا تملك صلاحية محرر المتجر."}, status=403)
    sections = _visible_sections_for_editor(request.user)
    return render(request, "admin/marketplace/storefront_editor.html", {"sections": sections, "is_admin": _is_admin(request.user)})


@login_required
@require_http_methods(["POST"])
def update_section(request, pk):
    section = get_object_or_404(StorefrontSection.objects.select_related("vendor__owner"), pk=pk)
    if not _can_edit(request.user, section):
        return JsonResponse({"detail": "ليس لديك صلاحية تعديل هذا القسم."}, status=403)
    try:
        payload = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"detail": "JSON غير صالح."}, status=400)
    try:
        sort_order = max(0, int(payload.get("sort_order", section.sort_order)))
    except (TypeError, ValueError):
        return JsonResponse({"detail": "الترتيب غير صالح."}, status=400)
    section.title = str(payload.get("title", section.title))[:180]
    section.sort_order = sort_order
    section.is_visible = bool(payload.get("is_visible", section.is_visible))
    config = payload.get("config")
    if config is not None:
        if not isinstance(config, dict):
            return JsonResponse({"detail": "إعدادات القسم يجب أن تكون JSON object."}, status=400)
        config = dict(config)
        config["__editor_version"] = 1
        section.config = config
    section.save(update_fields=["title", "sort_order", "is_visible", "config", "updated_at"])
    return JsonResponse({"ok": True, "id": section.id, "title": section.title, "sort_order": section.sort_order, "is_visible": section.is_visible, "config": section.config})


@login_required
@require_http_methods(["POST"])
def reorder_sections(request):
    try:
        payload = json.loads(request.body or "{}")
        ids = [int(value) for value in payload.get("ids", [])]
    except (json.JSONDecodeError, TypeError, ValueError):
        return JsonResponse({"detail": "قائمة الترتيب غير صالحة."}, status=400)
    sections = {section.id: section for section in StorefrontSection.objects.filter(id__in=ids).select_related("vendor__owner")}
    if set(sections) != set(ids):
        return JsonResponse({"detail": "بعض الأقسام غير موجودة."}, status=400)
    if not _is_admin(request.user) and any(not _can_edit(request.user, section) for section in sections.values()):
        return JsonResponse({"detail": "لا يمكنك إعادة ترتيب أقسام لا تملكها."}, status=403)
    for index, section_id in enumerate(ids):
        section = sections[section_id]
        section.sort_order = index
        section.save(update_fields=["sort_order", "updated_at"])
    return JsonResponse({"ok": True})
