from urllib.parse import quote

from django.db.models import F
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
    return {"id": product.id, "title": product.name, "name": product.name, "price": str(product.effective_price), "originalPrice": str(product.price), "salePrice": str(product.sale_price) if product.sale_price is not None else None, "currency": product.currency, "imageUrl": absolute(request, image), "url": f"/product/{product.id}", "slug": product.slug, "vendorSlug": product.vendor.slug, "vendorName": product.vendor.store_name, "rating": float(product.rating), "reviewsCount": product.reviews_count, "isTrending": product.is_trending, "trendTags": product.hashtags or [], "availableStock": product.available_stock, "discountPercent": product.discount_percent}


def category_circles(request, categories):
    return [{"id": category.id, "title": category.name, "name": category.name, "targetCategory": category.slug, "categorySlug": category.slug, "url": f"/collection?category={quote(category.slug)}", "route": f"/collection?category={quote(category.slug)}", "imageUrl": absolute(request, category.image.url) if category.image else "", "visible": True, "isActive": True, "sortOrder": index} for index, category in enumerate(categories)]


def custom_category_circles(request, config):
    circles = []
    for index, item in enumerate(config.get("category_circles") or []):
        if not isinstance(item, dict) or not item.get("title"):
            continue
        target = item.get("targetCategory") or item.get("target_category") or ""
        circles.append({"id": item.get("id", f"custom-{index}"), "title": item.get("title"), "name": item.get("title"), "targetCategory": target, "categorySlug": target, "url": item.get("url", "") or (f"/collection?category={quote(str(target))}" if target else ""), "imageUrl": absolute(request, item.get("imageUrl") or item.get("image_url") or ""), "visible": item.get("visible", True), "isActive": item.get("isActive", True), "sortOrder": item.get("sortOrder", index)})
    return sorted(circles, key=lambda item: item.get("sortOrder", 0))


def resolve_products(request, vendor, config):
    qs = Product.objects.filter(is_published=True, vendor__status="active").select_related("vendor").prefetch_related("categories")
    if vendor:
        qs = qs.filter(vendor=vendor)
    source = str(config.get("source", "latest")).lower()
    ids = [int(x) for x in config.get("product_ids", []) if str(x).isdigit()]
    category_id = config.get("source_category_id", config.get("category_id"))
    category_slug = str(config.get("category_slug", "")).strip()
    if source in {"selected", "manual"} and ids:
        preserved = {item_id: index for index, item_id in enumerate(ids)}
        rows = list(qs.filter(id__in=ids))
        rows.sort(key=lambda item: preserved.get(item.id, 10**9))
    elif source in {"category", "from_category"} and str(category_id).isdigit():
        rows = list(qs.filter(categories__id=int(category_id)).order_by("-created_at"))
    elif source in {"category", "from_category"} and category_slug:
        rows = list(qs.filter(categories__slug=category_slug).order_by("-created_at"))
    elif source in {"trending", "trend"}:
        rows = list(qs.filter(is_trending=True).order_by("-sold_count", "-created_at"))
    elif source in {"best_selling", "bestsellers", "most_sold"}:
        rows = list(qs.order_by("-sold_count", "-created_at"))
    elif source in {"discounts", "deals", "offers"}:
        rows = list(qs.filter(sale_price__isnull=False, sale_price__lt=F("price")).order_by("-updated_at", "-sold_count"))
    else:
        rows = list(qs.order_by("-created_at"))
    limit = max(1, min(int(config.get("limit", config.get("rows", 2) * config.get("columns", 2)) or 8), 100))
    return [product_card(request, product) for product in rows[:limit]]


def vendor_categories(request, vendor):
    qs = Category.objects.filter(is_active=True, products__vendor=vendor, products__is_published=True).distinct().order_by("sort_order", "name")
    return category_circles(request, qs)


def normalize_section_config(request, section, vendor):
    config = dict(section.config or {})
    config.setdefault("rows", 2); config.setdefault("columns", 4); config.setdefault("columns_desktop", config.get("columns", 4)); config.setdefault("columns_tablet", 3); config.setdefault("columns_mobile", 2); config.setdefault("mobile_scroll", False)
    if section.section_type in {"hero", "banner"} and not config.get("slides") and config.get("image_url"):
        target_type = config.get("target_type") or "none"; target_id = config.get("target_id"); url = config.get("target_url") or ""
        if target_type == "category" and target_id:
            category = Category.objects.filter(pk=target_id, is_active=True).first()
            if category: url = f"/collection?category={quote(category.slug)}"
        elif target_type == "product" and target_id:
            product = Product.objects.filter(pk=target_id, is_published=True).first()
            if product: url = f"/product/{product.pk}"
        config["slides"] = [{"id": f"{section.id}-main", "title": config.get("title") or section.title, "subtitle": config.get("subtitle") or "", "ctaLabel": config.get("button_label") or "", "url": url, "imageUrl": absolute(request, config.get("image_url")), "mobileImageUrl": absolute(request, config.get("mobile_image_url")), "visible": True, "isActive": True, "sortOrder": 0}]
    if section.section_type == "category":
        custom = custom_category_circles(request, config)
        if custom:
            config["circles"] = custom
        else:
            ids = [int(x) for x in config.get("category_ids", []) if str(x).isdigit()]
            if ids:
                cats = {item.id: item for item in Category.objects.filter(id__in=ids, is_active=True)}; ordered = [cats[x] for x in ids if x in cats]
            else:
                ordered = list(Category.objects.filter(is_active=True, products__vendor=vendor, products__is_published=True).distinct().order_by("sort_order", "name")) if vendor else list(Category.objects.filter(is_active=True).order_by("sort_order", "name"))
            config["circles"] = category_circles(request, ordered); config["category_ids"] = [item.id for item in ordered]
        config["columns_desktop"] = int(config.get("columns_desktop") or 4); config["columns_tablet"] = int(config.get("columns_tablet") or 3); config["columns_mobile"] = int(config.get("columns_mobile") or 2)
    if section.section_type in {"product_grid", "trend"}:
        if section.section_type == "trend": config["source"] = "trending"
        config["columns"] = max(1, min(int(config.get("columns", config.get("columns_mobile", 2)) or 2), 6)); config["rows"] = max(1, min(int(config.get("rows", 2) or 2), 20)); config["limit"] = max(1, min(int(config.get("limit", config["rows"] * config["columns"]) or 8), 100)); config["scroll"] = bool(config.get("scroll", config.get("mobile_scroll", False))); config["products"] = resolve_products(request, vendor, config); config["show_categories"] = bool(config.get("show_categories", False))
        if config["show_categories"]:
            if vendor: config["category_circles"] = vendor_categories(request, vendor)
            elif config.get("category_ids"):
                ids = [int(x) for x in config.get("category_ids", []) if str(x).isdigit()]; cats = Category.objects.filter(id__in=ids, is_active=True).order_by("sort_order", "name"); config["category_circles"] = category_circles(request, cats)
    if section.section_type == "tab": config["tabs"] = sorted([item for item in (config.get("tabs") or []) if isinstance(item, dict) and item.get("title")], key=lambda item: item.get("sortOrder", item.get("sort_order", 0)))
    return config


class DynamicHomeView(APIView):
    permission_classes = [AllowAny]
    def get(self, request, slug=None):
        vendor = None
        if slug:
            vendor = VendorProfile.objects.filter(slug=slug, status="active").first()
            if not vendor: return Response({"detail": "المتجر غير موجود"}, status=404)
            raw_sections = StorefrontSection.objects.filter(vendor=vendor, is_visible=True).order_by("sort_order", "id")
        else:
            raw_sections = StorefrontSection.objects.filter(vendor__isnull=True, is_visible=True).order_by("sort_order", "id")
        data=[]
        for section in raw_sections:
            config=section.config or {}
            if config.get("published", True): data.append({"id":section.id,"type":section.section_type,"title":section.title,"sort_order":section.sort_order,"is_visible":section.is_visible,"config":normalize_section_config(request,section,vendor)})
        if vendor:
            own_categories=Category.objects.filter(is_active=True,products__vendor=vendor,products__is_published=True).distinct().order_by("sort_order","name")
            if not any(item["type"]=="category" for item in data): data.append({"id":"system-categories","type":"category","title":"الفئات","sort_order":10,"is_visible":True,"config":{"circles":category_circles(request,own_categories)}})
        else:
            categories=list(Category.objects.filter(is_active=True).order_by("sort_order","name"))
            if categories and not any(item["type"]=="category" for item in data): data.append({"id":"system-categories","type":"category","title":"الفئات","sort_order":10,"is_visible":True,"config":{"circles":category_circles(request,categories)}})
            global_media=list(StorefrontMedia.objects.filter(vendor__isnull=True,is_active=True).order_by("sort_order","id"))
            if global_media and not any(item["type"] in {"hero","banner"} for item in data): data.append({"id":"system-media","type":"banner","title":"العروض","sort_order":20,"is_visible":True,"config":{"slides":[{"id":item.id,"title":item.name,"subtitle":item.alt_text,"ctaLabel":"استكشف الآن" if item.target_url else "","url":item.target_url or "","imageUrl":absolute(request,item.image.url) if item.image else "","visible":True,"isActive":True,"sortOrder":index} for index,item in enumerate(global_media)]}})
        active_themes=DesignTheme.objects.filter(is_active=True)
        if vendor:
            theme_obj=active_themes.filter(vendor=vendor).order_by("-updated_at").first() or active_themes.filter(is_global=True).order_by("-updated_at").first()
        else:
            theme_obj=active_themes.filter(is_global=True).order_by("-updated_at").first()
        theme={"id":theme_obj.id,"name":theme_obj.name,"tokens":theme_obj.tokens or {},"layout":theme_obj.layout or {},"sections":theme_obj.sections or [],"is_global":theme_obj.is_global} if theme_obj else None
        data.sort(key=lambda item:(item.get("sort_order",0),str(item.get("id",""))))
        return Response({"success":True,"store":{"id":vendor.id if vendor else None,"store_name":vendor.store_name if vendor else None,"slug":vendor.slug if vendor else None,"description":vendor.description if vendor else None,"logo_url":absolute(request,vendor.logo.url) if vendor and vendor.logo else None,"cover_url":absolute(request,vendor.cover.url) if vendor and vendor.cover else None},"theme":theme,"data":data})
