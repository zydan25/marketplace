import copy
import json
import re
import uuid
from pathlib import Path

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_http_methods
from PIL import Image

from .models import Category, Product, StorefrontSection, VendorProfile
from .storefront_models import StorefrontMedia

ALLOWED_SECTION_TYPES = {
    "hero": "العرض الرئيسي",
    "banner": "بانر إعلاني",
    "category": "الفئات",
    "product_grid": "شبكة المنتجات",
    "trend": "المنتجات الرائجة",
    "tab": "التبويبات",
}

MAX_IMAGE_SIZE = 12 * 1024 * 1024
ASSET_RE = re.compile(r"^asset:(slides|circles|cards):([0-9]+):image$")
NESTED_ALLOWED = {"slides", "circles", "cards"}


def is_admin(user):
    return user.is_staff or getattr(user, "role", None) == "admin"


def scope(user):
    if is_admin(user):
        return None, user
    vendor = VendorProfile.objects.filter(owner=user, status="active").first()
    return (vendor, user) if vendor else (False, user)


def can_edit(user, section):
    return is_admin(user) or bool(
        section.vendor_id
        and section.vendor
        and section.vendor.owner_id == user.id
        and section.vendor.status == "active"
    )


def defaults():
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
        "source_category_id": "",
        "category": "",
        "category_slug": "",
        "vendor_slug": "",
        "category_ids": [],
        "product_ids": [],
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
        "slides": [],
        "circles": [],
        "cards": [],
        "actions": [],
        "promo": {
            "enabled": False,
            "flashTitle": "",
            "flashSubtitle": "",
            "flashMode": "flash",
            "freeShippingTitle": "",
            "freeShippingSubtitle": "",
            "freeShippingCategory": "",
        },
        "__editor_version": 8,
    }


def config(section):
    data = defaults()
    raw = section.config or {}
    if isinstance(raw, dict):
        data.update(raw)
    # Keep nested collections usable even when older data had null/scalar values.
    for key in ("tabs", "slides", "circles", "cards", "actions"):
        if not isinstance(data.get(key), list):
            data[key] = []
    if not isinstance(data.get("promo"), dict):
        data["promo"] = copy.deepcopy(defaults()["promo"])
    return data


def _save_upload(uploaded):
    if uploaded.size > MAX_IMAGE_SIZE:
        raise ValueError("حجم الصورة أكبر من 12 ميجابايت.")
    suffix = Path(uploaded.name or "image.jpg").suffix.lower()
    if suffix not in {".jpg", ".jpeg", ".png", ".webp", ".gif"}:
        raise ValueError("نوع الصورة غير مدعوم. استخدم JPG أو PNG أو WebP أو GIF.")
    try:
        uploaded.seek(0)
        with Image.open(uploaded) as image:
            image.verify()
        uploaded.seek(0)
    except Exception as exc:
        raise ValueError("الصورة غير صالحة أو لا يمكن قراءتها على الخادم.") from exc
    path = f"storefront/{uuid.uuid4().hex}{suffix}"
    uploaded.seek(0)
    return default_storage.save(path, ContentFile(uploaded.read()))


def _absolute(request, path):
    url = default_storage.url(path) if path else ""
    return request.build_absolute_uri(url) if request and url.startswith("/") else url


def _media_items(vendor):
    qs = StorefrontMedia.objects.filter(is_active=True).order_by("updated_at", "id")
    return qs.filter(vendor=vendor) if vendor else qs.filter(vendor__isnull=True)


def _global_assets(request, vendor):
    categories = list(Category.objects.filter(is_active=True).order_by("sort_order", "name"))
    media = list(_media_items(vendor))
    return {
        "categories": [
            {
                "id": c.id,
                "name": c.name,
                "slug": c.slug,
                "image": request.build_absolute_uri(c.image.url) if c.image else "",
                "sort_order": c.sort_order,
            }
            for c in categories
        ],
        "media": [
            {
                "id": m.id,
                "name": m.name,
                "alt_text": m.alt_text,
                "image": request.build_absolute_uri(m.image.url) if m.image else "",
                "target_url": m.target_url or "",
                "sort_order": index,
            }
            for index, m in enumerate(media)
        ],
    }


def visual_editor(request):
    if not (is_admin(request.user) or getattr(request.user, "role", None) == "vendor"):
        return JsonResponse({"detail": "غير مصرح."}, status=403)
    vendor, _ = scope(request.user)
    if vendor is False:
        return JsonResponse({"detail": "التاجر غير نشط أو لا يملك متجرًا."}, status=403)
    qs = StorefrontSection.objects.select_related("vendor").order_by("sort_order", "id")
    if vendor:
        qs = qs.filter(vendor=vendor)
    sections = list(qs)
    for section in sections:
        section.builder_config_json = json.dumps(config(section), ensure_ascii=False)
    categories = list(Category.objects.filter(is_active=True).order_by("sort_order", "name"))
    products_qs = Product.objects.filter(is_published=True).select_related("vendor").order_by("name")
    if vendor:
        products_qs = products_qs.filter(vendor=vendor)
    catalog = {
        "categories": [{"id": c.id, "name": c.name, "slug": c.slug, "image": request.build_absolute_uri(c.image.url) if c.image else ""} for c in categories],
        "products": [{"id": p.id, "name": p.name, "vendor": p.vendor.store_name} for p in products_qs[:500]],
        "global": _global_assets(request, vendor),
    }
    return render(
        request,
        "admin/marketplace/storefront_builder_v8.html",
        {
            "sections": sections,
            "section_types": ALLOWED_SECTION_TYPES,
            "catalog_json": json.dumps(catalog, ensure_ascii=False),
            "defaults_json": json.dumps(defaults(), ensure_ascii=False),
        },
    )


def _target_to_url(section_config):
    target_type = section_config.get("target_type") or "none"
    target_id = section_config.get("target_id")
    if target_type == "url":
        return str(section_config.get("target_url") or "")
    if target_type == "category" and target_id:
        category = Category.objects.filter(pk=target_id, is_active=True).first()
        return f"/collection?category={category.name}" if category else ""
    if target_type == "product" and target_id:
        product = Product.objects.filter(pk=target_id, is_published=True).first()
        return f"/product/{product.pk}" if product else ""
    return ""


def _sync_visual_contract(section_config):
    data = dict(section_config)
    if not data.get("slides") and data.get("image_url"):
        data["slides"] = [{
            "id": "hero-main",
            "title": data.get("title") or "",
            "subtitle": data.get("subtitle") or "",
            "ctaLabel": data.get("button_label") or "",
            "url": _target_to_url(data),
            "imageUrl": data.get("image_url") or "",
            "mobileImageUrl": data.get("mobile_image_url") or "",
            "visible": True,
            "isActive": True,
            "sortOrder": 0,
        }]
    if data.get("category_ids") and not data.get("circles"):
        circles = []
        selected = Category.objects.filter(id__in=data.get("category_ids", []), is_active=True).order_by("sort_order", "name")
        by_id = {item.id: item for item in selected}
        for index, category_id in enumerate(data.get("category_ids", [])):
            category = by_id.get(category_id)
            if not category:
                continue
            circles.append({
                "id": category.id,
                "title": category.name,
                "targetCategory": category.slug,
                "categorySlug": category.slug,
                "url": f"/collection?category={category.name}",
                "imageUrl": category.image.url if category.image else "",
                "visible": True,
                "isActive": True,
                "sortOrder": index,
            })
        data["circles"] = circles
    if data.get("source") == "category" and data.get("source_category_id"):
        try:
            category = Category.objects.filter(pk=int(data["source_category_id"]), is_active=True).first()
        except (TypeError, ValueError):
            category = None
        if category:
            data["source_category_id"] = category.id
            data["category"] = category.name
            data["category_slug"] = category.slug
    return data


def _apply_nested_uploads(request, section_config):
    for field_name, uploaded in request.FILES.items():
        match = ASSET_RE.match(field_name)
        if not match:
            continue
        key, index_text, image_key = match.groups()
        index = int(index_text)
        items = section_config.setdefault(key, [])
        if index >= len(items):
            continue
        try:
            path = _save_upload(uploaded)
        except ValueError as exc:
            raise ValueError(f"صورة العنصر {key} رقم {index + 1}: {exc}") from exc
        url = _absolute(request, path)
        item = dict(items[index]) if isinstance(items[index], dict) else {}
        item["imageUrl"] = url
        item["image_url"] = url
        item["imagePath"] = path
        item["image_path"] = path
        items[index] = item


def _save_section_images(request, section_config):
    for field_name, key, path_key in (("image", "image_url", "image_path"), ("mobile_image", "mobile_image_url", "mobile_image_path")):
        upload = request.FILES.get(field_name)
        if not upload:
            continue
        try:
            path = _save_upload(upload)
        except ValueError as exc:
            raise ValueError(str(exc)) from exc
        section_config[path_key] = path
        section_config[key] = _absolute(request, path)


@require_http_methods(["POST"])
def create_section(request):
    vendor, owner = scope(request.user)
    if vendor is False:
        return JsonResponse({"detail": "التاجر غير نشط أو لا يملك متجرًا."}, status=403)
    try:
        data = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"detail": "بيانات غير صالحة."}, status=400)
    kind = data.get("section_type", "banner")
    if kind not in ALLOWED_SECTION_TYPES:
        return JsonResponse({"detail": "نوع القسم غير صالح."}, status=400)
    last = StorefrontSection.objects.filter(vendor=vendor).order_by("-sort_order", "-id").first()
    try:
        requested_order = int(data.get("sort_order") or 0)
    except (TypeError, ValueError):
        requested_order = 0
    order = requested_order if requested_order > 0 else (last.sort_order + 1 if last else 1)
    section = StorefrontSection.objects.create(
        owner=owner,
        vendor=vendor,
        title=str(data.get("title") or ALLOWED_SECTION_TYPES[kind])[:180],
        section_type=kind,
        sort_order=order,
        is_visible=False,
        config=defaults(),
    )
    return JsonResponse({"ok": True, "id": section.id})


@require_http_methods(["POST"])
def update_section(request, pk):
    section = get_object_or_404(StorefrontSection.objects.select_related("vendor"), pk=pk)
    if not can_edit(request.user, section):
        return JsonResponse({"detail": "لا تملك صلاحية هذا القسم."}, status=403)
    try:
        data = json.loads(request.POST.get("payload", "{}")) if request.content_type.startswith("multipart/") else json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"detail": "بيانات غير صالحة."}, status=400)
    if not isinstance(data, dict):
        return JsonResponse({"detail": "بيانات العملية يجب أن تكون كائنًا."}, status=400)
    action = data.get("action", "save")
    if action == "delete":
        section.delete()
        return JsonResponse({"ok": True})
    if action == "duplicate":
        cloned_config = copy.deepcopy(config(section))
        cloned_config["published"] = False
        new_order = section.sort_order + 1
        for item in StorefrontSection.objects.filter(vendor=section.vendor, sort_order__gte=new_order).order_by("-sort_order"):
            item.sort_order += 1
            item.save(update_fields=["sort_order", "updated_at"])
        clone = StorefrontSection.objects.create(owner=request.user, vendor=section.vendor, title=f"{section.title} — نسخة", section_type=section.section_type, sort_order=new_order, is_visible=False, config=cloned_config)
        return JsonResponse({"ok": True, "id": clone.id})
    if action in {"publish", "unpublish"}:
        published = action == "publish"
        section_config = config(section)
        section_config["published"] = published
        section_config = _sync_visual_contract(section_config)
        section.config = section_config
        section.is_visible = published
        section.save(update_fields=["config", "is_visible", "updated_at"])
        return JsonResponse({"ok": True, "published": published, "config": section_config})

    kind = data.get("section_type", section.section_type)
    if kind not in ALLOWED_SECTION_TYPES:
        return JsonResponse({"detail": "نوع القسم غير صالح."}, status=400)
    try:
        order = max(1, int(data.get("sort_order", section.sort_order)))
    except (TypeError, ValueError):
        return JsonResponse({"detail": "رقم الترتيب غير صالح."}, status=400)
    incoming = data.get("config", {})
    if not isinstance(incoming, dict):
        return JsonResponse({"detail": "إعدادات القسم يجب أن تكون كائن JSON."}, status=400)
    section_config = defaults()
    section_config.update(incoming)
    try:
        if kind in {"product_grid", "trend"} and section_config.get("source") == "category":
            raw_category = section_config.get("source_category_id")
            if raw_category in (None, ""):
                raise ValueError("اختر فئة لشبكة المنتجات.")
            category = Category.objects.filter(id=int(raw_category), is_active=True).first()
            if not category:
                raise ValueError("الفئة المختارة غير موجودة أو غير نشطة.")
            section_config["source_category_id"] = category.id
            section_config["category"] = category.name
            section_config["category_slug"] = category.slug
        _save_section_images(request, section_config)
        _apply_nested_uploads(request, section_config)
    except (ValueError, TypeError) as exc:
        return JsonResponse({"detail": str(exc)}, status=400)
    section_config = _sync_visual_contract(section_config)
    section.title = str(data.get("title", section.title))[:180]
    section.section_type = kind
    section.sort_order = order
    section.is_visible = bool(data.get("is_visible", section.is_visible))
    section.config = section_config
    section.save(update_fields=["title", "section_type", "sort_order", "is_visible", "config", "updated_at"])
    return JsonResponse({"ok": True, "config": section_config, "order": section.sort_order, "published": bool(section_config.get("published"))})


@require_http_methods(["POST"])
def reorder_sections(request):
    try:
        data = json.loads(request.body or "{}")
        items = data.get("items", [])
    except (json.JSONDecodeError, TypeError):
        return JsonResponse({"detail": "بيانات الترتيب غير صالحة."}, status=400)
    if not isinstance(items, list):
        return JsonResponse({"detail": "عناصر الترتيب يجب أن تكون قائمة."}, status=400)
    ids, orders = [], []
    for item in items:
        try:
            section_id, order = int(item["id"]), int(item["order"])
        except (KeyError, TypeError, ValueError):
            return JsonResponse({"detail": "كل قسم يحتاج رقم ترتيب صحيح."}, status=400)
        ids.append(section_id)
        orders.append(order)
    if len(ids) != len(set(ids)) or len(orders) != len(set(orders)) or any(order < 1 for order in orders):
        return JsonResponse({"detail": "أرقام الترتيب يجب أن تكون موجبة وفريدة."}, status=400)
    rows = {item.id: item for item in StorefrontSection.objects.filter(id__in=ids).select_related("vendor")}
    if set(ids) != set(rows):
        return JsonResponse({"detail": "بعض الأقسام غير موجودة."}, status=400)
    if any(not can_edit(request.user, item) for item in rows.values()):
        return JsonResponse({"detail": "لا يمكنك ترتيب قسم لا تملكه."}, status=403)
    for item in items:
        rows[int(item["id"])].sort_order = int(item["order"])
        rows[int(item["id"])].save(update_fields=["sort_order", "updated_at"])
    return JsonResponse({"ok": True})


@require_http_methods(["POST"])
def upload_storefront_image(request):
    upload = request.FILES.get("image")
    if not upload:
        return JsonResponse({"detail": "اختر صورة."}, status=400)
    try:
        path = _save_upload(upload)
    except ValueError as exc:
        return JsonResponse({"detail": str(exc)}, status=400)
    return JsonResponse({"ok": True, "url": _absolute(request, path), "path": path})
