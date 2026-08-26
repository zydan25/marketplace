from urllib.parse import quote

from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Category, StorefrontSection, VendorProfile, Product
from .storefront_models import StorefrontMedia


def absolute(request, value):
    if not value:
        return ""
    text = str(value)
    if text.startswith(("http://", "https://")):
        return text
    return request.build_absolute_uri(text) if text.startswith("/") else text


def normalize_section_config(request, section):
    config = dict(section.config or {})
    if section.section_type in {"hero", "banner"} and not config.get("slides") and config.get("image_url"):
        target_type = config.get("target_type") or "none"
        target_id = config.get("target_id")
        url = config.get("target_url") or ""
        if target_type == "category" and target_id:
            category = Category.objects.filter(pk=target_id, is_active=True).first()
            if category:
                url = f"/collection?category={quote(category.name)}"
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
            categories = []
            media = list(StorefrontMedia.objects.filter(vendor=vendor, is_active=True).order_by("updated_at", "id"))
        else:
            raw_sections = StorefrontSection.objects.filter(vendor__isnull=True, is_visible=True).order_by("sort_order", "id")
            categories = list(Category.objects.filter(is_active=True).order_by("sort_order", "name"))
            media = list(StorefrontMedia.objects.filter(vendor__isnull=True, is_active=True).order_by("updated_at", "id"))

        sections = [section for section in raw_sections if (section.config or {}).get("published", True)]
        data = []
        for section in sections:
            config = normalize_section_config(request, section)
            if section.section_type == "category":
                category_ids = []
                for value in config.get("category_ids", []):
                    try:
                        category_ids.append(int(value))
                    except (TypeError, ValueError):
                        continue
                selected = Category.objects.filter(id__in=category_ids, is_active=True).order_by("sort_order", "name")
                by_id = {item.id: item for item in selected}
                ordered = [by_id[item_id] for item_id in category_ids if item_id in by_id]
                config["circles"] = [
                    {
                        "id": item.id,
                        "title": item.name,
                        "name": item.name,
                        "targetCategory": item.slug,
                        "categorySlug": item.slug,
                        "url": f"/collection?category={quote(item.name)}",
                        "route": f"/collection?category={quote(item.name)}",
                        "imageUrl": absolute(request, item.image.url) if item.image else "",
                        "visible": True,
                        "sortOrder": index,
                    }
                    for index, item in enumerate(ordered)
                ]
                config["category_ids"] = [item.id for item in ordered]
            data.append({
                "id": section.id,
                "type": section.section_type,
                "title": section.title,
                "sort_order": section.sort_order,
                "is_visible": section.is_visible,
                "config": config,
            })

        if categories and not any(item["type"] == "category" for item in data):
            data.append({
                "id": "system-categories",
                "type": "category",
                "title": "الفئات",
                "sort_order": -900,
                "is_visible": True,
                "config": {
                    "circles": [
                        {
                            "id": category.id,
                            "title": category.name,
                            "name": category.name,
                            "targetCategory": category.slug,
                            "categorySlug": category.slug,
                            "url": f"/collection?category={quote(category.name)}",
                            "route": f"/collection?category={quote(category.name)}",
                            "imageUrl": absolute(request, category.image.url) if category.image else "",
                            "visible": True,
                            "sortOrder": index,
                        }
                        for index, category in enumerate(categories)
                    ]
                },
            })

        if media and not any(item["type"] in {"hero", "banner"} for item in data):
            data.append({
                "id": "system-media",
                "type": "banner",
                "title": "محتوى عام",
                "sort_order": -800,
                "is_visible": True,
                "config": {
                    "slides": [
                        {
                            "id": media_item.id,
                            "title": media_item.name,
                            "subtitle": media_item.alt_text,
                            "ctaLabel": "استكشف الآن" if media_item.target_url else "",
                            "url": media_item.target_url or "",
                            "imageUrl": absolute(request, media_item.image.url) if media_item.image else "",
                            "visible": True,
                            "sortOrder": index,
                        }
                        for index, media_item in enumerate(media)
                    ]
                },
            })

        data.sort(key=lambda item: (item.get("sort_order", 0), str(item.get("id", ""))))
        return Response({"success": True, "data": data})
