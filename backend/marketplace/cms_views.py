from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny

from .models import Category, StorefrontSection, VendorProfile
from .storefront_models import StorefrontMedia


class DynamicHomeView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, slug=None):
        vendor = None
        if slug:
            vendor = VendorProfile.objects.filter(slug=slug, status="active").first()
            if not vendor:
                return Response({"detail": "المتجر غير موجود"}, status=404)
            sections = list(StorefrontSection.objects.filter(vendor=vendor, is_visible=True).order_by("sort_order", "id"))
            categories = []
            media = list(StorefrontMedia.objects.filter(vendor=vendor, is_active=True).order_by("updated_at", "id"))
        else:
            sections = list(StorefrontSection.objects.filter(vendor__isnull=True, is_visible=True).order_by("sort_order", "id"))
            categories = list(Category.objects.filter(is_active=True).order_by("sort_order", "name"))
            media = list(StorefrontMedia.objects.filter(vendor__isnull=True, is_active=True).order_by("updated_at", "id"))

        data = []
        for section in sections:
            data.append({
                "id": section.id,
                "type": section.section_type,
                "title": section.title,
                "sort_order": section.sort_order,
                "is_visible": section.is_visible,
                "config": section.config or {},
            })

        # Legacy/admin categories are projected into the same visual format consumed by the app.
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
                            "targetCategory": category.slug,
                            "url": f"/collection?category={category.slug}",
                            "imageUrl": request.build_absolute_uri(category.image.url) if category.image else "",
                            "visible": True,
                            "sortOrder": index,
                        }
                        for index, category in enumerate(categories)
                    ]
                },
            })

        # Media created from Django Admin is projected into a hero/banner section.
        if media and not any(item["type"] in {"hero", "banner"} for item in data):
            data.append({
                "id": "system-media",
                "type": "banner",
                "title": "مميز لدينا",
                "sort_order": -800,
                "is_visible": True,
                "config": {
                    "slides": [
                        {
                            "id": media_item.id,
                            "title": media_item.name,
                            "subtitle": media_item.alt_text,
                            "ctaLabel": "استكشف الآن",
                            "url": media_item.target_url or "",
                            "imageUrl": request.build_absolute_uri(media_item.image.url) if media_item.image else "",
                            "visible": True,
                            "sortOrder": index,
                        }
                        for index, media_item in enumerate(media)
                    ]
                },
            })

        data.sort(key=lambda item: (item.get("sort_order", 0), str(item.get("id", ""))))
        return Response({"success": True, "data": data})
