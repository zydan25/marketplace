import json

from django.http import JsonResponse
from django.shortcuts import render

from .visual_storefront_v8 import (
    ALLOWED_SECTION_TYPES,
    Product,
    StorefrontSection,
    Category,
    _global_assets,
    config,
    is_admin,
    scope,
)


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
        section.builder_config_json = json.dumps(config(section), ensure_ascii=False)

    categories = list(Category.objects.filter(is_active=True).order_by("sort_order", "name"))
    products_qs = Product.objects.filter(is_published=True).select_related("vendor").order_by("name")
    if vendor:
        products_qs = products_qs.filter(vendor=vendor)
    catalog = {
        "categories": [
            {"id": c.id, "name": c.name, "slug": c.slug,
             "image": request.build_absolute_uri(c.image.url) if c.image else ""}
            for c in categories
        ],
        "products": [
            {"id": p.id, "name": p.name,
             "vendor": p.vendor.store_name if p.vendor_id else ""}
            for p in products_qs[:500]
        ],
        "global": _global_assets(request, vendor),
    }
    return render(
        request,
        "admin/marketplace/storefront_builder_v9.html",
        {
            "sections": sections,
            "section_types": ALLOWED_SECTION_TYPES,
            "catalog_json": json.dumps(catalog, ensure_ascii=False),
        },
    )
