import copy
import json
import uuid
from pathlib import Path

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_http_methods

from .models import Category, Product, StorefrontSection, VendorProfile

SECTION_TYPES = {
    "hero": "العرض الرئيسي",
    "banner": "بانر إعلاني",
    "category": "الفئات",
    "product_grid": "شبكة المنتجات",
    "trend": "المنتجات الرائجة",
    "tab": "التبويبات",
}

TYPE_HELP = {
    "hero": "قسم افتتاحي كبير للصفحة، مناسب لصورة أو أكثر مع عنوان ووصف وزر وتوجيه.",
    "banner": "إعلان بصري داخل الصفحة. يمكن ربطه بمنتج أو فئة أو قسم أو رابط.",
    "category": "يعرض فئات مختارة من الفئات الموجودة في المنصة، ويمكن ترتيبها يدويًا.",
    "product_grid": "شبكة منتجات بمصدر تختاره: أحدث، مبيعات، خصومات، فئة، متجر أو اختيار يدوي.",
    "trend": "قسم للمنتجات الرائجة مع نفس أدوات شبكة المنتجات.",
    "tab": "عدة تبويبات، وكل تبويب يمكن أن يحتوي مصدر منتجات مستقلًا.",
}


def _admin(user):
    return user.is_staff or getattr(user, "role", None) == "admin"


def _scope(user):
    if _admin(user):
        return None, user
    vendor = VendorProfile.objects.filter(owner=user, status="active").first()
    return (vendor, user) if vendor else (False, user)


def _can(user, section):
    if _admin(user):
        return True
    return bool(section.vendor_id and section.vendor and section.vendor.owner_id == user.id and section.vendor.status == "active")


def _default_config():
    return {
        "published": False,
        "subtitle": "",
        "description": "",
        "image_url": "",
        "mobile_image_url": "",
        "image_position": "center",
        "image_fit": "cover",
        "aspect_ratio": "16:7",
        "overlay": True,
        "overlay_opacity": 30,
        "text_position": "center",
        "text_align": "center",
        "button_label": "",
        "target_type": "none",
        "target_url": "",
        "target_id": "",
        "source": "latest",
        "category_ids": [],
        "product_ids": [],
        "vendor_slug": "",
        "limit": 8,
        "columns_desktop": 4,
        "columns_tablet": 3,
        "columns_mobile": 2,
        "show_images": True,
        "show_names": True,
        "show_prices": True,
        "show_discount": True,
        "show_rating": False,
        "show_arrows": True,
        "mobile_scroll": False,
        "card_style": "card",
        "image_shape": "rounded",
        "background": "#ffffff",
        "text_color": "#111827",
        "section_padding": "medium",
        "full_width": True,
        "tabs": [],
        "__editor_version": 6,
    }


def _cfg(section):
    result = _default_config()
    result.update(section.config or {})
    return result


def _save(uploaded):
    suffix = Path(uploaded.name or "image.jpg").suffix.lower() or ".jpg"
    path = f"storefront/{uuid.uuid4().hex}{suffix}"
    return default_storage.save(path, ContentFile(uploaded.read()))


def _json(data):
    return json.dumps(data, ensure_ascii=False)


@require_http_methods(["GET"])
def builder(request):
    if not (_admin(request.user) or getattr(request.user, "role", None) == "vendor"):
        return JsonResponse({"detail": "غير مصرح."}, status=403)
    vendor, _ = _scope(request.user)
    if vendor is False:
        return JsonResponse({"detail": "التاجر غير نشط أو لا يملك متجرًا."}, status=403)
    qs = StorefrontSection.objects.select_related("vendor").order_by("sort_order", "id")
    if vendor:
        qs = qs.filter(vendor=vendor)
    sections = list(qs)
    for item in sections:
        item.builder_config = _cfg(item)
    categories = list(Category.objects.filter(is_active=True).order_by("sort_order", "name"))
    products = Product.objects.filter(is_published=True).select_related("vendor").order_by("name")
    if vendor:
        products = products.filter(vendor=vendor)
    products = list(products[:500])
    catalog = {
        "categories": [{"id": c.id, "name": c.name} for c in categories],
        "products": [{"id": p.id, "name": p.name, "vendor": p.vendor.store_name} for p in products],
    }
    return render(request, "admin/marketplace/storefront_builder.html", {
        "sections": sections,
        "section_types": SECTION_TYPES,
        "type_help": TYPE_HELP,
        "catalog_json": _json(catalog),
        "defaults_json": _json(_default_config()),
    })


@require_http_methods(["POST"])
def create(request):
    vendor, owner = _scope(request.user)
    if vendor is False:
        return JsonResponse({"detail": "التاجر غير نشط أو لا يملك متجرًا."}, status=403)
    try:
        data = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"detail": "بيانات غير صالحة."}, status=400)
    kind = data.get("section_type", "banner")
    if kind not in SECTION_TYPES:
        return JsonResponse({"detail": "نوع القسم غير صالح."}, status=400)
    last = StorefrontSection.objects.filter(vendor=vendor).order_by("-sort_order", "-id").first()
    section = StorefrontSection.objects.create(
        owner=owner,
        vendor=vendor,
        title=str(data.get("title") or SECTION_TYPES[kind])[:180],
        section_type=kind,
        sort_order=(last.sort_order + 1 if last else 1),
        is_visible=True,
        config=_default_config(),
    )
    return JsonResponse({"ok": True, "id": section.id})


@require_http_methods(["POST"])
def save(request, pk):
    section = get_object_or_404(StorefrontSection.objects.select_related("vendor"), pk=pk)
    if not _can(request.user, section):
        return JsonResponse({"detail": "لا تملك صلاحية تعديل هذا القسم."}, status=403)
    try:
        data = json.loads(request.POST.get("payload", "{}")) if request.content_type.startswith("multipart/") else json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"detail": "بيانات غير صالحة."}, status=400)
    kind = data.get("section_type", section.section_type)
    if kind not in SECTION_TYPES:
        return JsonResponse({"detail": "نوع القسم غير صالح."}, status=400)
    cfg = _default_config()
    cfg.update(data.get("config") or {})
    cfg["published"] = bool(cfg.get("published", False))
    cfg["__editor_version"] = 6
    try:
        order = max(1, int(data.get("sort_order", section.sort_order)))
    except (TypeError, ValueError):
        return JsonResponse({"detail": "رقم الترتيب غير صالح."}, status=400)
    for field, key, path_key in (("image", "image_url", "image_path"), ("mobile_image", "mobile_image_url", "mobile_image_path")):
        upload = request.FILES.get(field)
        if upload:
            if upload.size > 8 * 1024 * 1024:
                return JsonResponse({"detail": "حجم الصورة أكبر من 8 ميجابايت."}, status=400)
            path = _save(upload)
            cfg[path_key] = path
            cfg[key] = default_storage.url(path)
    section.title = str(data.get("title", section.title))[:180]
    section.section_type = kind
    section.sort_order = order
    section.is_visible = bool(data.get("is_visible", True))
    section.config = cfg
    section.save(update_fields=["title", "section_type", "sort_order", "is_visible", "config", "updated_at"])
    return JsonResponse({"ok": True, "config": cfg, "order": section.sort_order})


@require_http_methods(["POST"])
def duplicate(request, pk):
    section = get_object_or_404(StorefrontSection.objects.select_related("vendor"), pk=pk)
    if not _can(request.user, section):
        return JsonResponse({"detail": "لا تملك صلاحية النسخ."}, status=403)
    cfg = copy.deepcopy(_cfg(section))
    cfg["published"] = False
    next_order = section.sort_order + 1
    StorefrontSection.objects.filter(vendor=section.vendor, sort_order__gte=next_order).update(sort_order=__import__("django").db.models.F("sort_order") + 1)
    clone = StorefrontSection.objects.create(owner=request.user, vendor=section.vendor, title=f"{section.title} — نسخة", section_type=section.section_type, sort_order=next_order, is_visible=False, config=cfg)
    return JsonResponse({"ok": True, "id": clone.id})


@require_http_methods(["POST"])
def remove(request, pk):
    section = get_object_or_404(StorefrontSection.objects.select_related("vendor"), pk=pk)
    if not _can(request.user, section):
        return JsonResponse({"detail": "لا تملك صلاحية الحذف."}, status=403)
    section.delete()
    return JsonResponse({"ok": True})


@require_http_methods(["POST"])
def publish(request, pk):
    section = get_object_or_404(StorefrontSection.objects.select_related("vendor"), pk=pk)
    if not _can(request.user, section):
        return JsonResponse({"detail": "لا تملك صلاحية النشر."}, status=403)
    value = str(request.POST.get("published", "0")) == "1"
    cfg = _cfg(section)
    cfg["published"] = value
    section.config = cfg
    section.is_visible = value
    section.save(update_fields=["config", "is_visible", "updated_at"])
    return JsonResponse({"ok": True, "published": value})


@require_http_methods(["POST"])
def reorder(request):
    try:
        items = json.loads(request.body or "{}").get("items", [])
    except (json.JSONDecodeError, TypeError):
        return JsonResponse({"detail": "بيانات الترتيب غير صالحة."}, status=400)
    ids = []
    orders = []
    for item in items:
        try:
            sid, order = int(item["id"]), int(item["order"])
        except (KeyError, TypeError, ValueError):
            return JsonResponse({"detail": "كل عنصر يحتاج رقم ترتيب صحيح."}, status=400)
        if order < 1:
            return JsonResponse({"detail": "الترتيب يبدأ من 1."}, status=400)
        ids.append(sid)
        orders.append(order)
    if len(ids) != len(set(ids)) or len(orders) != len(set(orders)):
        return JsonResponse({"detail": "أرقام الترتيب والمعرفات يجب أن تكون فريدة."}, status=400)
    sections = {s.id: s for s in StorefrontSection.objects.filter(id__in=ids).select_related("vendor")}
    if set(ids) != set(sections):
        return JsonResponse({"detail": "بعض الأقسام غير موجودة."}, status=400)
    if any(not _can(request.user, s) for s in sections.values()):
        return JsonResponse({"detail": "لا يمكنك إعادة ترتيب قسم لا تملكه."}, status=403)
    for item in items:
        sections[int(item["id"])].sort_order = int(item["order"])
        sections[int(item["id"])].save(update_fields=["sort_order", "updated_at"])
    return JsonResponse({"ok": True})


@require_http_methods(["POST"])
def upload(request):
    upload_file = request.FILES.get("image")
    if not upload_file:
        return JsonResponse({"detail": "اختر صورة."}, status=400)
    if upload_file.size > 8 * 1024 * 1024:
        return JsonResponse({"detail": "حجم الصورة يجب ألا يتجاوز 8 ميجابايت."}, status=400)
    path = _save(upload_file)
    return JsonResponse({"ok": True, "url": default_storage.url(path), "path": path})
