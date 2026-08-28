from urllib.parse import quote

from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Category, DesignTheme, Product, StorefrontSection, VendorProfile
from .storefront_models import StorefrontMedia


def absolute(request, value):
    if not value:
        return ""
    text = str(value)
    if text.startswith(("http://", "https://")):
        return text
    return request.build_absolute_uri(text) if text.startswith("/") else text


def product_card(request, product):
    image = product.main_image.url if product.main_image else ""
    return {
        "id": product.id,
        "title": product.name,
        "name": product.name,
        "price": str(product.effective_price),
        "originalPrice": str(product.price),
        "salePrice": str(product.sale_price) if product.sale_price is not None else None,
        "currency": product.currency,
        "imageUrl": absolute(request, image),
        "url": f"/product/{product.id}",
        "slug": product.slug,
        "vendorSlug": product.vendor.slug,
        "rating": float(product.rating),
        "reviewsCount": product.reviews_count,
        "isTrending": product.is_trending,
        "availableStock": product.available_stock,
    }


def category_circles(request, categories):
    return [
        {
            "id": category.id,
            "title": category.name,
            "name": category.name,
            "targetCategory": category.slug,
            "categorySlug": category.slug,
            "url": f"/collection?category={quote(category.slug)}",
            "route": f"/collection?category={quote(category.slug)}",
            "imageUrl": absolute(request, category.image.url) if category.image else "",
            "visible": True,
            "isActive": True,
            "sortOrder": index,
        }
        for index, category in enumerate(categories)
    ]


def resolve_products(request, vendor, config):
    qs = Product.objects.filter(is_published=True, vendor__status="active")
    if vendor:
        qs = qs.filter(vendor=vendor)
    source = str(config.get("source", "latest")).lower()
    ids = [int(x) for x in config.get("product_ids", []) if str(x).isdigit()]
    category_id = config.get("category_id")
    if source == "selected" and ids:
        qs = qs.filter(id__in=ids)
    elif source == "category" and str(category_id).isdigit():
        qs = qs.filter(categories__id=int(category_id))
    elif source == "trending":
        qs = qs.filter(is_trending=True).order_by("-sold_count", "-created_at")
    else:
        qs = qs.order_by("-created_at")
    limit = max(1, min(int(config.get("limit", config.get("rows", 2)) or 2) * max(1, min(int(config.get("columns", 2) or 2), 4)), 40))
    products = list(qs.select_related("vendor").prefetch_related("categories")[:limit])
    return [product_card(request, product) for product in products]


def normalize_section_config(request, section, vendor):
    config = dict(section.config or {})
    if section.section_type in {"hero", "banner"} and not config.get("slides") and config.get("image_url"):
        target_type = config.get("target_type") or "none"
        target_id = config.get("target_id")
        url = config.get("target_url") or ""
        if target_type == "category" and target_id:
            category = Category.objects.filter(pk=target_id, is_active=True).first()
            if category:
                url = f"/collection?category={quote(category.slug)}"
        elif target_type == "product" and target_id:
            product = Product.objects.filter(pk=target_id, is_published=True).first()
            if product:
                url = f"/product/{product.pk}"
        config["slides"] = [{
            "id": f"{section.id}-main",
            "title": config.get("title") or section.title,
            "subtitle": config.get("subtitle") or "",
            "ctaLabel": config.get("button_label") or "",
            "url": url,
            "imageUrl": absolute(request, config.get("image_url")),
            "mobileImageUrl": absolute(request, config.get("mobile_image_url")),
            "visible": True,
            "isActive": True,
            "sortOrder": 0,
        }]
    if section.section_type == "category":
        ids = [int(x) for x in config.get("category_ids", []) if str(x).isdigit()]
        if ids:
            categories = list(Category.objects.filter(id__in=ids, is_active=True))
            by_id = {item.id: item for item in categories}
            ordered = [by_id[x] for x in ids if x in by_id]
        else:
            category_qs = Category.objects.filter(is_active=True)
            if vendor:
                category_qs = category_qs.filter(products__vendor=vendor, products__is_published=True).distinct()
            ordered = list(category_qs.order_by("sort_order", "name"))
        config["circles"] = category_circles(request, ordered)
        config["category_ids"] = [item.id for item in ordered]
    if section.section_type in {"product_grid", "trend"}:
        if section.section_type == "trend":
            config.setdefault("source", "trending")
        config["columns"] = max(2, min(int(config.get("columns", 2) or 2), 4))
        config["rows"] = max(1, min(int(config.get("rows", 2) or 2), 6))
        config["scroll"] = bool(config.get("scroll", True))
        config["products"] = resolve_products(request, vendor, config)
    return config


class DynamicHomeView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, slug=None):
        vendor = None
        if slug:
            vendor = VendorProfile.objects.filter(slug=slug, status="active").first()
            if not vendor:
                return Response({"detail": "المتجر غير موجود"}, status=404)
            raw_sections = StorefrontSection.objects.filter(vendor=vendor, is_visible=True).order_by("sort_order", "id")
            global_media = StorefrontMedia.objects.filter(vendor__isnull=True, is_active=True).order_by("updated_at", "id")
        else:
            raw_sections = StorefrontSection.objects.filter(vendor__isnull=True, is_visible=True).order_by("sort_order", "id")
            global_media = StorefrontMedia.objects.filter(vendor__isnull=True, is_active=True).order_by("updated_at", "id")

        sections = [section for section in raw_sections if (section.config or {}).get("published", True)]
        data = []
        for section in sections:
            config = normalize_section_config(request, section, vendor)
            data.append({
                "id": section.id,
                "type": section.section_type,
                "title": section.title,
                "sort_order": section.sort_order,
                "is_visible": section.is_visible,
                "config": config,
            })

        if vendor:
            own_categories = Category.objects.filter(is_active=True, products__vendor=vendor, products__is_published=True).distinct().order_by("sort_order", "name")
            if not any(item["type"] == "category" for item in data):
                data.append({"id": "system-categories", "type": "category", "title": "الفئات", "sort_order": -100, "is_visible": True, "config": {"circles": category_circles(request, own_categories)}})
        else:
            categories = list(Category.objects.filter(is_active=True).order_by("sort_order", "name"))
            if categories and not any(item["type"] == "category" for item in data):
                data.append({"id": "system-categories", "type": "category", "title": "الفئات", "sort_order": -100, "is_visible": True, "config": {"circles": category_circles(request, categories)}})

        media = list(global_media)
        if media and not any(item["type"] in {"hero", "banner"} for item in data):
            data.append({
                "id": "system-media",
                "type": "banner",
                "title": "العروض",
                "sort_order": -90,
                "is_visible": True,
                "config": {"slides": [{
                    "id": item.id,
                    "title": item.name,
                    "subtitle": item.alt_text,
                    "ctaLabel": "استكشف الآن" if item.target_url else "",
                    "url": item.target_url or "",
                    "imageUrl": absolute(request, item.image.url) if item.image else "",
                    "visible": True,
                    "isActive": True,
                    "sortOrder": index,
                } for index, item in enumerate(media)]},
            })

        theme = None
        if vendor:
            theme_obj = DesignTheme.objects.filter(vendor=vendor, is_active=True).order_by("-updated_at").first()
            if theme_obj:
                theme = {"id": theme_obj.id, "name": theme_obj.name, "tokens": theme_obj.tokens or {}, "layout": theme_obj.layout or {}}

        data.sort(key=lambda item: (item.get("sort_order", 0), str(item.get("id", ""))))
        return Response({"success": True, "store": {
            "id": vendor.id if vendor else None,
            "store_name": vendor.store_name if vendor else None,
            "slug": vendor.slug if vendor else None,
            "description": vendor.description if vendor else None,
            "logo_url": absolute(request, vendor.logo.url) if vendor and vendor.logo else None,
            "cover_url": absolute(request, vendor.cover.url) if vendor and vendor.cover else None,
        }, "theme": theme, "data": data})
