from urllib.parse import quote
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import Category, StorefrontSection, VendorProfile, Product
from .models_extra import Service, ServiceCategory


def absolute(request, value):
    if not value: return ""
    text = str(value)
    if text.startswith(("http://", "https://")): return text
    return request.build_absolute_uri(text) if text.startswith("/") else text

class DynamicHomeView(APIView):
    permission_classes = [AllowAny]
    def get(self, request, slug=None):
        vendor = VendorProfile.objects.filter(slug=slug, status="active").first() if slug else None
        if slug and not vendor: return Response({"detail": "المتجر غير موجود"}, status=404)
        sections = StorefrontSection.objects.filter(vendor=vendor, is_visible=True).order_by("sort_order", "id") if vendor else StorefrontSection.objects.filter(vendor__isnull=True, is_visible=True).order_by("sort_order", "id")
        data = []
        for section in sections:
            config = dict(section.config or {})
            if section.section_type == "category":
                ids = [int(x) for x in config.get("category_ids", []) if str(x).isdigit()]
                items = {c.id: c for c in Category.objects.filter(id__in=ids, is_active=True)}
                config["circles"] = [{"id": c.id, "title": c.name, "targetCategory": c.slug, "categorySlug": c.slug, "url": f"/collection?category={quote(c.slug)}", "imageUrl": absolute(request, c.image.url) if c.image else "", "visible": True, "sortOrder": i} for i, cid in enumerate(ids) if (c:=items.get(cid))]
            elif section.section_type == "service_grid":
                ids = [int(x) for x in config.get("service_ids", []) if str(x).isdigit()]
                services = {s.id: s for s in Service.objects.filter(id__in=ids, is_active=True).select_related("category")}
                cards = []
                for i, sid in enumerate(ids):
                    service = services.get(sid)
                    if not service: continue
                    cards.append({"id": service.id, "title": service.name, "subtitle": service.description, "price": str(service.price), "currency": service.currency, "url": f"/services/{service.slug}", "imageUrl": absolute(request, service.image.url) if service.image else "", "bannerUrl": absolute(request, service.banner.url) if service.banner else "", "visible": True, "sortOrder": i})
                config["cards"] = cards
            data.append({"id": section.id, "type": section.section_type, "title": section.title, "sort_order": section.sort_order, "is_visible": section.is_visible, "config": config})
        if not vendor and not any(x["type"] == "category" for x in data):
            categories = list(Category.objects.filter(is_active=True).order_by("sort_order", "name"))
            data.append({"id":"system-categories","type":"category","title":"الأصناف","sort_order":-900,"is_visible":True,"config":{"circles":[{"id":c.id,"title":c.name,"targetCategory":c.slug,"categorySlug":c.slug,"url":f"/collection?category={quote(c.slug)}","imageUrl":absolute(request,c.image.url) if c.image else "","visible":True,"sortOrder":i} for i,c in enumerate(categories)]}})
        data.sort(key=lambda x:(x.get("sort_order",0), str(x.get("id",""))))
        return Response({"success": True, "data": data})
