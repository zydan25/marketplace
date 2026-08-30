import json
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_http_methods
from .visual_storefront_v8 import *


def builder_defaults():
    data = defaults()
    data.update({
        "rows": 2,
        "show_categories": False,
        "category_layout": "horizontal",
        "category_bar_title": "الأقسام والتصنيفات",
        "tab_bar": False,
        "tab_style": "pills",
    })
    return data


def visual_editor_v9(request):
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
        section_config = builder_defaults()
        section_config.update(config(section))
        section.builder_config_json = json.dumps(section_config, ensure_ascii=False)
    categories = list(Category.objects.filter(is_active=True).order_by("sort_order", "name"))
    products_qs = Product.objects.filter(is_published=True).select_related("vendor").order_by("name")
    if vendor:
        products_qs = products_qs.filter(vendor=vendor)
    catalog = {
        "categories": [{"id": c.id, "name": c.name, "slug": c.slug, "image": request.build_absolute_uri(c.image.url) if c.image else ""} for c in categories],
        "products": [{"id": p.id, "name": p.name, "vendor": p.vendor.store_name} for p in products_qs[:1000]],
        "global": _global_assets(request, vendor),
    }
    return render(request, "admin/marketplace/storefront_builder_v9.html", {
        "sections": sections,
        "section_types": ALLOWED_SECTION_TYPES,
        "catalog_json": json.dumps(catalog, ensure_ascii=False),
        "defaults_json": json.dumps(builder_defaults(), ensure_ascii=False),
    })


@require_http_methods(["POST"])
def import_global_media(request):
    if not is_admin(request.user):
        return JsonResponse({"detail": "استيراد المحتوى العام متاح للمدير فقط."}, status=403)
    media = list(StorefrontMedia.objects.filter(vendor__isnull=True, is_active=True).order_by("updated_at", "id"))
    if not media:
        return JsonResponse({"detail": "لا توجد وسائط عامة نشطة للاستيراد."}, status=404)
    existing = StorefrontSection.objects.filter(vendor__isnull=True, config__imported_global_media=True).first()
    if existing:
        return JsonResponse({"ok": True, "id": existing.id, "existing": True})
    slides = [{
        "id": f"global-media-{item.id}",
        "title": item.name,
        "subtitle": item.alt_text,
        "badge": "",
        "ctaLabel": "استكشف الآن" if item.target_url else "",
        "url": item.target_url or "",
        "imageUrl": item.image.url if item.image else "",
        "visible": True,
        "isActive": True,
        "sortOrder": index,
    } for index, item in enumerate(media)]
    section = StorefrontSection.objects.create(
        owner=request.user, vendor=None, title="العروض العامة", section_type="banner", sort_order=10,
        is_visible=False, config={**builder_defaults(), "slides": slides, "imported_global_media": True},
    )
    return JsonResponse({"ok": True, "id": section.id})


@require_http_methods(["POST"])
def import_global_categories(request):
    if not is_admin(request.user):
        return JsonResponse({"detail": "استيراد المحتوى العام متاح للمدير فقط."}, status=403)
    categories = list(Category.objects.filter(is_active=True).order_by("sort_order", "name"))
    if not categories:
        return JsonResponse({"detail": "لا توجد فئات عامة نشطة."}, status=404)
    existing = StorefrontSection.objects.filter(vendor__isnull=True, config__imported_global_categories=True).first()
    if existing:
        return JsonResponse({"ok": True, "id": existing.id, "existing": True})
    section = StorefrontSection.objects.create(
        owner=request.user, vendor=None, title="الفئات العامة", section_type="category", sort_order=5,
        is_visible=False, config={**builder_defaults(), "category_ids": [c.id for c in categories], "imported_global_categories": True, "category_layout": "circle"},
    )
    return JsonResponse({"ok": True, "id": section.id})
