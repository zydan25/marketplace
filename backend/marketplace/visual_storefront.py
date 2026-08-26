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
from .storefront_models import StorefrontMedia

ALLOWED_SECTION_TYPES = {
    "hero": "العرض الرئيسي",
    "banner": "بانر إعلاني",
    "category": "الفئات",
    "product_grid": "شبكة المنتجات",
    "trend": "المنتجات الرائجة",
    "tab": "التبويبات",
}


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
        "promo": {"enabled": False},
        "__editor_version": 12,
    }


def config(section):
    data = defaults()
    data.update(section.config or {})
    return data


def upload_file(file_obj):
    suffix = Path(file_obj.name or "image.jpg").suffix.lower() or ".jpg"
    path = f"storefront/{uuid.uuid4().hex}{suffix}"
    return default_storage.save(path, ContentFile(file_obj.read()))


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
        "admin/marketplace/storefront_builder_v7.html",
        {
            "sections": sections,
            "section_types": ALLOWED_SECTION_TYPES,
            "catalog_json": json.dumps(catalog, ensure_ascii=False),
            "defaults_json": json.dumps(defaults(), ensure_ascii=False),
        },
    )


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


def _target_to_url(section_config, *, request=None):
    target_type = section_config.get("target_type") or "none"
    target_id = section_config.get("target_id")
    if target_type == "url":
        return str(section_config.get("target_url") or "")
    if target_type == "category" and target_id:
        category = Category.objects.filter(pk=target_id, is_active=True).first()
        if category:
            return f"/collection?category={category.name}".encode("utf-8").decode("utf-8")
    if target_type == "product" and target_id:
        product = Product.objects.filter(pk=target_id, is_published=True).first()
        if product:
            return f"/product/{product.pk}"
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
        for index, category in enumerate(Category.objects.filter(id__in=data.get("category_ids", []), is_active=True).order_by("sort_order", "name")):
            circles.append({
                "id": category.id,
                "title": category.name,
                "targetCategory": category.name,
                "categorySlug": category.slug,
                "url": f"/collection?category={category.name}",
                "imageUrl": category.image.url if category.image else "",
                "visible": True,
                "isActive": True,
                "sortOrder": index,
            })
        data["circles"] = circles
    if data.get("source") == "category" and data.get("source_category_id"):
        category = Category.objects.filter(pk=data["source_category_id"], is_active=True).first()
        if category:
            data["category"] = category.name
            data["category_slug"] = category.slug
    return data


@require_http_methods(["POST"])
def update_section(request, pk):
    section = get_object_or_404(StorefrontSection.objects.select_related("vendor"), pk=pk)
    if not can_edit(request.user, section):
        return JsonResponse({"detail": "لا تملك صلاحية هذا القسم."}, status=403)
    try:
        data = json.loads(request.POST.get("payload", "{}")) if request.content_type.startswith("multipart/") else json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"detail": "بيانات غير صالحة."}, status=400)

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
        section.config = _sync_visual_contract(section_config)
        section.is_visible = published
        section.save(update_fields=["config", "is_visible", "updated_at"])
        return JsonResponse({"ok": True, "published": published})

    kind = data.get("section_type", section.section_type)
    if kind not in ALLOWED_SECTION_TYPES:
        return JsonResponse({"detail": "نوع القسم غير صالح."}, status=400)
    try:
        order = max(1, int(data.get("sort_order", section.sort_order)))
    except (TypeError, ValueError):
        return JsonResponse({"detail": "رقم الترتيب غير صالح."}, status=400)

    section_config = defaults()
    section_config.update(data.get("config") or {})
    if kind in {"product_grid", "trend"} and section_config.get("source") == "category":
        raw_category = section_config.get("source_category_id")
        try:
            section_config["source_category_id"] = int(raw_category)
        except (TypeError, ValueError):
            return JsonResponse({"detail": "اختر فئة لشبكة المنتجات."}, status=400)
        category = Category.objects.filter(id=section_config["source_category_id"], is_active=True).first()
        if not category:
            return JsonResponse({"detail": "الفئة المختارة غير موجودة أو غير نشطة."}, status=400)
        section_config["category"] = category.name
        section_config["category_slug"] = category.slug

    for field_name, url_key, path_key in (("image", "image_url", "image_path"), ("mobile_image", "mobile_image_url", "mobile_image_path")):
        uploaded = request.FILES.get(field_name)
        if uploaded:
            if uploaded.size > 8 * 1024 * 1024:
                return JsonResponse({"detail": "حجم الصورة أكبر من 8 ميجابايت."}, status=400)
            saved_path = upload_file(uploaded)
            section_config[path_key] = saved_path
            section_config[url_key] = default_storage.url(saved_path)

    section_config = _sync_visual_contract(section_config)
    section.title = str(data.get("title", section.title))[:180]
    section.section_type = kind
    section.sort_order = order
    section.is_visible = bool(data.get("is_visible", section.is_visible))
    section.config = section_config
    section.save(update_fields=["title", "section_type", "sort_order", "is_visible", "config", "updated_at"])
    return JsonResponse({"ok": True, "config": section_config, "order": order})


@require_http_methods(["POST"])
def reorder_sections(request):
    try:
        items = json.loads(request.body or "{}").get("items", [])
    except (json.JSONDecodeError, TypeError):
        return JsonResponse({"detail": "بيانات الترتيب غير صالحة."}, status=400)
    ids, orders = [], []
    for item in items:
        try:
            section_id, order = int(item["id"]), int(item["order"])
        except (KeyError, TypeError, ValueError):
            return JsonResponse({"detail": "كل قسم يحتاج رقم ترتيب صحيح."}, status=400)
        ids.append(section_id); orders.append(order)
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
    if not (is_admin(request.user) or getattr(request.user, "role", None) == "vendor"):
        return JsonResponse({"detail": "غير مصرح."}, status=403)
    uploaded = request.FILES.get("image")
    if not uploaded:
        return JsonResponse({"detail": "اختر صورة."}, status=400)
    if uploaded.size > 8 * 1024 * 1024:
        return JsonResponse({"detail": "حجم الصورة أكبر من 8 ميجابايت."}, status=400)
    saved_path = upload_file(uploaded)
    return JsonResponse({"ok": True, "url": default_storage.url(saved_path), "path": saved_path})
