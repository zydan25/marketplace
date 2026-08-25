import json
from pathlib import Path

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_http_methods

from .models import Category, Product, StorefrontSection, VendorProfile

ALLOWED_SECTION_TYPES = {
    "hero": "العرض الرئيسي",
    "category": "الفئات",
    "product_grid": "شبكة المنتجات",
    "trend": "المنتجات الرائجة",
    "banner": "بانر إعلاني",
    "tab": "تبويبات",
}


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


def _normalize_config(config):
    return config if isinstance(config, dict) else {}


def _save_uploaded_image(uploaded, folder="storefront"):
    if not uploaded:
        return ""
    suffix = Path(uploaded.name or "image.jpg").suffix.lower() or ".jpg"
    safe_name = f"{folder}/{__import__('uuid').uuid4().hex}{suffix}"
    return default_storage.save(safe_name, ContentFile(uploaded.read()))


def _public_media_url(path):
    if not path:
        return ""
    return default_storage.url(path)


@require_http_methods(["GET"])
def visual_editor(request):
    if not (_is_admin(request.user) or getattr(request.user, "role", None) == "vendor"):
        return JsonResponse({"detail": "لا تملك صلاحية محرر المتجر."}, status=403)
    sections = _visible_sections_for_editor(request.user)
    categories = Category.objects.filter(is_active=True).order_by("sort_order", "name")
    products = Product.objects.filter(is_published=True).select_related("vendor").order_by("name")[:500]
    return render(
        request,
        "admin/marketplace/storefront_editor.html",
        {
            "sections": sections,
            "is_admin": _is_admin(request.user),
            "section_types": ALLOWED_SECTION_TYPES,
            "categories": categories,
            "products": products,
        },
    )


@require_http_methods(["POST"])
def create_section(request):
    if not (_is_admin(request.user) or getattr(request.user, "role", None) == "vendor"):
        return JsonResponse({"detail": "لا تملك صلاحية إنشاء قسم."}, status=403)
    try:
        payload = json.loads(request.POST.get("payload", "{}")) if request.content_type.startswith("multipart/") else json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"detail": "بيانات القسم غير صالحة."}, status=400)
    section_type = str(payload.get("section_type", "banner"))
    if section_type not in ALLOWED_SECTION_TYPES:
        return JsonResponse({"detail": "نوع القسم غير مسموح."}, status=400)

    if _is_admin(request.user):
        vendor = None
        owner = request.user
    else:
        vendor = VendorProfile.objects.filter(owner=request.user).first()
        if not vendor:
            return JsonResponse({"detail": "لا يوجد متجر مرتبط بالحساب."}, status=400)
        if vendor.status != "active":
            return JsonResponse({"detail": "لا يمكن تعديل متجر غير نشط."}, status=403)
        owner = request.user

    last = StorefrontSection.objects.filter(vendor=vendor).order_by("-sort_order", "-id").first()
    next_order = (last.sort_order + 1) if last else 0
    config = {
        "subtitle": "",
        "image_url": "",
        "image_position": "center",
        "image_fit": "cover",
        "overlay": False,
        "overlay_opacity": 35,
        "button_label": "",
        "target_url": "",
        "target_type": "url",
        "category_ids": [],
        "product_ids": [],
        "limit": 8,
        "columns": 2,
        "sort": "latest",
        "show_names": True,
        "show_prices": True,
        "show_arrows": True,
        "cards": [],
        "__editor_version": 2,
    }
    section = StorefrontSection.objects.create(
        owner=owner,
        vendor=vendor,
        title=str(payload.get("title", ALLOWED_SECTION_TYPES[section_type]))[:180],
        section_type=section_type,
        sort_order=next_order,
        is_visible=True,
        config=config,
    )
    return JsonResponse({"ok": True, "id": section.id, "title": section.title, "section_type": section.section_type, "config": config})


@require_http_methods(["POST"])
def update_section(request, pk):
    section = get_object_or_404(StorefrontSection.objects.select_related("vendor__owner"), pk=pk)
    if not _can_edit(request.user, section):
        return JsonResponse({"detail": "ليس لديك صلاحية تعديل هذا القسم."}, status=403)

    try:
        if request.content_type.startswith("multipart/"):
            payload = json.loads(request.POST.get("payload", "{}"))
        else:
            payload = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"detail": "بيانات القسم غير صالحة."}, status=400)

    section_type = str(payload.get("section_type", section.section_type))
    if section_type not in ALLOWED_SECTION_TYPES:
        return JsonResponse({"detail": "نوع القسم غير مسموح."}, status=400)
    try:
        sort_order = max(0, int(payload.get("sort_order", section.sort_order)))
    except (TypeError, ValueError):
        return JsonResponse({"detail": "الترتيب غير صالح."}, status=400)

    config = _normalize_config(payload.get("config", section.config))
    uploaded = request.FILES.get("image")
    if uploaded:
        saved = _save_uploaded_image(uploaded)
        config["image_path"] = saved
        config["image_url"] = _public_media_url(saved)

    section.title = str(payload.get("title", section.title))[:180]
    section.section_type = section_type
    section.sort_order = sort_order
    section.is_visible = bool(payload.get("is_visible", section.is_visible))
    config["__editor_version"] = 2
    section.config = config
    section.save(update_fields=["title", "section_type", "sort_order", "is_visible", "config", "updated_at"])
    return JsonResponse({"ok": True, "id": section.id, "title": section.title, "section_type": section.section_type, "sort_order": section.sort_order, "is_visible": section.is_visible, "config": section.config})


@require_http_methods(["POST"])
def upload_storefront_image(request):
    if not (_is_admin(request.user) or getattr(request.user, "role", None) == "vendor"):
        return JsonResponse({"detail": "لا تملك صلاحية رفع الصور."}, status=403)
    uploaded = request.FILES.get("image")
    if not uploaded:
        return JsonResponse({"detail": "اختر صورة أولًا."}, status=400)
    if uploaded.size > 8 * 1024 * 1024:
        return JsonResponse({"detail": "حجم الصورة يجب ألا يتجاوز 8 ميجابايت."}, status=400)
    path = _save_uploaded_image(uploaded)
    return JsonResponse({"ok": True, "path": path, "url": _public_media_url(path)})


@require_http_methods(["POST"])
def reorder_sections(request):
    if not (_is_admin(request.user) or getattr(request.user, "role", None) == "vendor"):
        return JsonResponse({"detail": "لا تملك صلاحية إعادة الترتيب."}, status=403)
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
