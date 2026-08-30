from urllib.parse import quote

from django.db.models import F, Q
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
    categories = list(product.categories.values("id", "name", "slug"))
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
        "categories": categories,
        "hashtags": product.hashtags or [],
    }


def category_circles(request, categories):
    return [{
        "id": category.id,
        "title": category.name,
        "name": category.name,
        "targetCategory": category.slug,
        "categorySlug": category.slug,
        "url": f"/collection?category={quote(category.name)}",
        "route": f"/collection?category={quote(category.name)}",
        "imageUrl": absolute(request, category.image.url) if category.image else "",
        "visible": True,
        "isActive": True,
        "sortOrder": index,
    } for index, category in enumerate(categories)]


def resolve_products(request, vendor, config):
    qs = Product.objects.filter(is_published=True, vendor__status="active")
    if vendor:
        qs = qs.filter(vendor=vendor)

    source = str(config.get("source", "latest")).lower()
    ids = [int(x) for x in (config.get("product_ids") or []) if str(x).isdigit()]
    if not ids and isinstance(config.get("products"), list):
        ids = [
            int(item.get("id"))
            for item in config.get("products")
            if isinstance(item, dict) and str(item.get("id", "")).isdigit()
        ]

    category_id = config.get("category_id", config.get("source_category_id"))
    if source in {"selected", "manual"} and ids:
        qs = qs.filter(id__in=ids)
    elif source == "category" and str(category_id).isdigit():
        qs = qs.filter(categories__id=int(category_id))
    elif source == "trending":
        qs = qs.filter(is_trending=True).order_by("-sold_count", "-created_at")
    elif source == "best_selling":
        qs = qs.order_by("-sold_count", "-created_at")
    elif source == "discounts":
        qs = qs.filter(sale_price__isnull=False, sale_price__lt=F("price")).order_by("-created_at")
    elif source == "new":
        qs = qs.order_by("-created_at")
    else:
        qs = qs.order_by("-created_at")

    rows = max(1, min(int(config.get("rows", 2) or 2), 8))
    columns = max(1, min(int(config.get("columns", 2) or 2), 8))
    scroll = bool(config.get("scroll", True))
    pages = 3 if scroll else 1
    limit = min(rows * columns * pages, 60)
    products = list(qs.select_related("vendor").prefetch_related("categories")[:max(1, limit)])
    return products, [product_card(request, product) for product in products]


def vendor_categories(request, vendor):
    qs = Category.objects.filter(
        is_active=True,
        products__vendor=vendor,
        products__is_published=True,
    ).distinct().order_by("sort_order", "name")
    return category_circles(request, qs)


def normalize_section_config(request, section, vendor):
    config = dict(section.config or {})

    if section.section_type in {"hero", "banner"}:
        if not config.get("slides") and (config.get("image_url") or config.get("imageUrl")):
            image = config.get("image_url") or config.get("imageUrl")
            target_type = config.get("target_type") or config.get("targetType") or "none"
            target_id = config.get("target_id") or config.get("targetId")
            url = config.get("target_url") or config.get("url") or ""
            if target_type == "category" and str(target_id).isdigit():
                category = Category.objects.filter(pk=int(target_id), is_active=True).first()
                if category:
                    url = f"/collection?category={quote(category.name)}"
            elif target_type == "product" and str(target_id).isdigit():
                product = Product.objects.filter(pk=int(target_id), is_published=True).first()
                if product:
                    url = f"/product/{product.pk}"
            config["slides"] = [{
                "id": f"{section.id}-main",
                "title": config.get("title") or section.title,
                "subtitle": config.get("subtitle") or config.get("description") or "",
                "ctaLabel": config.get("button_label") or config.get("ctaLabel") or "",
                "url": url,
                "imageUrl": absolute(request, image),
                "mobileImageUrl": absolute(request, config.get("mobile_image_url") or config.get("mobileImageUrl")),
                "visible": True,
                "isActive": True,
                "sortOrder": 0,
            }]

        for slide in config.get("slides") or []:
            if not isinstance(slide, dict):
                continue
            if slide.get("imageUrl"):
                slide["imageUrl"] = absolute(request, slide["imageUrl"])
            if slide.get("mobileImageUrl"):
                slide["mobileImageUrl"] = absolute(request, slide["mobileImageUrl"])

    if section.section_type == "category":
        ids = [int(x) for x in (config.get("category_ids") or []) if str(x).isdigit()]
        if ids:
            cats = {item.id: item for item in Category.objects.filter(id__in=ids, is_active=True)}
            ordered = [cats[x] for x in ids if x in cats]
        else:
            filters = {"products__vendor": vendor, "products__is_published": True} if vendor else {}
            ordered = list(Category.objects.filter(is_active=True, **filters).distinct().order_by("sort_order", "name"))
        config["circles"] = category_circles(request, ordered)
        config["category_ids"] = [item.id for item in ordered]

    if section.section_type in {"product_grid", "trend"}:
        if section.section_type == "trend":
            config["source"] = "trending"
        if config.get("source") == "category" and not config.get("category_id"):
            config["category_id"] = config.get("source_category_id")
        config["columns"] = max(1, min(int(config.get("columns", 2) or 2), 8))
        config["rows"] = max(1, min(int(config.get("rows", 2) or 2), 8))
        config["scroll"] = bool(config.get("scroll", True))
        products, cards = resolve_products(request, vendor, config)
        config["resolved_product_ids"] = [product.id for product in products]
        config["products"] = cards
        if config.get("show_categories"):
            config["category_circles"] = vendor_categories(request, vendor) if vendor else category_circles(
                request,
                Category.objects.filter(is_active=True).order_by("sort_order", "name"),
            )
        # Optional named tab definitions used by the reference-style storefront.
        tabs = config.get("tabs")
        if isinstance(tabs, list):
            normalized_tabs = []
            for index, tab in enumerate(tabs):
                if not isinstance(tab, dict):
                    continue
                tab_copy = dict(tab)
                tab_cfg = dict(tab_copy.get("config") or tab_copy)
                tab_products, tab_cards = resolve_products(request, vendor, tab_cfg)
                tab_copy["id"] = tab_copy.get("id") or f"{section.id}-tab-{index}"
                tab_copy["title"] = tab_copy.get("title") or f"تبويب {index + 1}"
                tab_copy["sortOrder"] = int(tab_copy.get("sortOrder", index) or index)
                tab_copy["productIds"] = [product.id for product in tab_products]
                tab_copy["products"] = tab_cards
                normalized_tabs.append(tab_copy)
            config["tabs"] = sorted(normalized_tabs, key=lambda item: item.get("sortOrder", 0))

    if section.section_type == "banner":
        for card in config.get("cards") or []:
            if isinstance(card, dict):
                if card.get("imageUrl"):
                    card["imageUrl"] = absolute(request, card["imageUrl"])
                if card.get("mobileImageUrl"):
                    card["mobileImageUrl"] = absolute(request, card["mobileImageUrl"])

    return config


class DynamicHomeView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, slug=None):
        vendor = None
        if slug:
            vendor = VendorProfile.objects.filter(slug=slug, status="active").first()
            if not vendor:
                return Response({"detail": "المتجر غير موجود"}, status=404)
            raw_sections = StorefrontSection.objects.filter(
                vendor=vendor, is_visible=True
            ).order_by("sort_order", "id")
        else:
            raw_sections = StorefrontSection.objects.filter(
                vendor__isnull=True, is_visible=True
            ).order_by("sort_order", "id")

        data = []
        for section in raw_sections:
            if (section.config or {}).get("published", True):
                data.append({
                    "id": section.id,
                    "type": section.section_type,
                    "title": section.title,
                    "sort_order": section.sort_order,
                    "is_visible": section.is_visible,
                    "config": normalize_section_config(request, section, vendor),
                })

        categories = list(
            Category.objects.filter(is_active=True).order_by("sort_order", "name")
            if vendor is None
            else Category.objects.filter(
                is_active=True,
                products__vendor=vendor,
                products__is_published=True,
            ).distinct().order_by("sort_order", "name")
        )
        if categories and not any(item["id"] == "system-categories" for item in data):
            data.append({
                "id": "system-categories",
                "type": "category",
                "title": "الفئات",
                "sort_order": -100,
                "is_visible": True,
                "config": {"circles": category_circles(request, categories), "system": True},
            })

        media_qs = StorefrontMedia.objects.filter(is_active=True)
        if vendor:
            media = list(media_qs.filter(Q(vendor=vendor) | Q(vendor__isnull=True)).order_by("updated_at", "id"))
        else:
            media = list(media_qs.filter(vendor__isnull=True).order_by("updated_at", "id"))
        represented_media = {
            str(slide.get("id"))
            for section in data
            for slide in (section.get("config", {}).get("slides") or [])
            if isinstance(slide, dict) and slide.get("id") is not None
        }
        legacy_media = [item for item in media if str(item.id) not in represented_media]
        if legacy_media:
            data.append({
                "id": "system-media",
                "type": "banner",
                "title": "العروض",
                "sort_order": -90,
                "is_visible": True,
                "config": {
                    "slides": [
                        {
                            "id": item.id,
                            "title": item.name,
                            "subtitle": item.alt_text,
                            "ctaLabel": "استكشف الآن" if item.target_url else "",
                            "url": item.target_url or "",
                            "imageUrl": absolute(request, item.image.url) if item.image else "",
                            "visible": True,
                            "isActive": True,
                            "sortOrder": index,
                            "legacyMedia": True,
                        }
                        for index, item in enumerate(legacy_media)
                    ],
                    "legacy": True,
                },
            })

        theme_obj = (
            DesignTheme.objects.filter(
                Q(vendor=vendor) | Q(is_global=True, is_active=True)
            ).order_by("-vendor_id", "-updated_at").first()
            if vendor
            else DesignTheme.objects.filter(is_global=True, is_active=True).order_by("-updated_at").first()
        )
        theme = {
            "id": theme_obj.id,
            "name": theme_obj.name,
            "tokens": theme_obj.tokens or {},
            "layout": theme_obj.layout or {},
        } if theme_obj else None

        data.sort(key=lambda item: (item.get("sort_order", 0), str(item.get("id", ""))))
        return Response({
            "success": True,
            "store": {
                "id": vendor.id if vendor else None,
                "store_name": vendor.store_name if vendor else None,
                "slug": vendor.slug if vendor else None,
                "description": vendor.description if vendor else None,
                "logo_url": absolute(request, vendor.logo.url) if vendor and vendor.logo else None,
                "cover_url": absolute(request, vendor.cover.url) if vendor and vendor.cover else None,
            },
            "theme": theme,
            "data": data,
        })
