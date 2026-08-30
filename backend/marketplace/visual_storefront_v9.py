import json
from django.http import JsonResponse
from django.shortcuts import render
from .visual_storefront_v8 import *


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
    base_defaults = defaults()
    base_defaults.update({
        "rows": 2,
        "show_categories": False,
        "category_layout": "horizontal",
        "category_bar_title": "الأقسام والتصنيفات",
        "tab_bar": False,
        "tab_style": "pills",
        "button_target_type": "none",
    })
    for section in sections:
        data = dict(base_defaults)
        data.update(config(section))
        section.builder_config_json = json.dumps(data, ensure_ascii=False)
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
        "defaults_json": json.dumps(base_defaults(), ensure_ascii=False),
    })
