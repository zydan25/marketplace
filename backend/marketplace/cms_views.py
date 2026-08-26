from urllib.parse import quote
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import Category, StorefrontSection, VendorProfile, Product
from .models_extra import Service
from .storefront_models import StorefrontMedia

def absolute(request, value):
    if not value: return ""
    text = str(value)
    if text.startswith(("http://", "https://")): return text
    return request.build_absolute_uri(text) if text.startswith("/") else text

def normalize_section_config(request, section):
    config = dict(section.config or {})
    if section.section_type in {"hero", "banner"} and not config.get("slides") and config.get("image_url"):
        target_type=config.get("target_type") or "none"; target_id=config.get("target_id"); url=config.get("target_url") or ""
        if target_type == "category" and target_id:
            category=Category.objects.filter(pk=target_id,is_active=True).first()
            if category: url=f"/collection?category={quote(category.name)}"
        elif target_type == "product" and target_id:
            product=Product.objects.filter(pk=target_id,is_published=True).first()
            if product: url=f"/product/{product.pk}"
        config["slides"]=[{"id":f"{section.id}-main","title":config.get("title") or section.title,"subtitle":config.get("subtitle") or "","ctaLabel":config.get("button_label") or "","url":url,"imageUrl":absolute(request,config.get("image_url")),"mobileImageUrl":absolute(request,config.get("mobile_image_url")),"visible":True,"isActive":True,"sortOrder":0}]
    return config

class DynamicHomeView(APIView):
    permission_classes=[AllowAny]
    def get(self,request,slug=None):
        vendor=VendorProfile.objects.filter(slug=slug,status="active").first() if slug else None
        if slug and not vendor: return Response({"detail":"المتجر غير موجود"},status=404)
        if vendor:
            raw_sections=StorefrontSection.objects.filter(vendor=vendor,is_visible=True).order_by("sort_order","id"); categories=[]; media=list(StorefrontMedia.objects.filter(vendor=vendor,is_active=True).order_by("updated_at","id"))
        else:
            raw_sections=StorefrontSection.objects.filter(vendor__isnull=True,is_visible=True).order_by("sort_order","id"); categories=list(Category.objects.filter(is_active=True).order_by("sort_order","name")); media=list(StorefrontMedia.objects.filter(vendor__isnull=True,is_active=True).order_by("updated_at","id"))
        data=[]
        for section in [s for s in raw_sections if (s.config or {}).get("published",True)]:
            config=normalize_section_config(request,section)
            if section.section_type=="category":
                ids=[]
                for value in config.get("category_ids",[]):
                    try: ids.append(int(value))
                    except (TypeError,ValueError): continue
                selected=Category.objects.filter(id__in=ids,is_active=True).order_by("sort_order","name"); by_id={x.id:x for x in selected}; ordered=[by_id[x] for x in ids if x in by_id]
                config["circles"]=[{"id":item.id,"title":item.name,"name":item.name,"targetCategory":item.slug,"categorySlug":item.slug,"url":f"/collection?category={quote(item.name)}","route":f"/collection?category={quote(item.name)}","imageUrl":absolute(request,item.image.url) if item.image else "","visible":True,"sortOrder":i} for i,item in enumerate(ordered)]; config["category_ids"]=[item.id for item in ordered]
            elif section.section_type=="product_grid" and str(config.get("source","")).lower()=="services":
                ids=[]
                for value in config.get("service_ids",[]):
                    try: ids.append(int(value))
                    except (TypeError,ValueError): continue
                selected={x.id:x for x in Service.objects.filter(id__in=ids,is_active=True).select_related("category")}
                cards=[{"id":item.id,"title":item.name,"subtitle":item.description,"price":str(item.price),"currency":item.currency,"url":f"/services/{item.slug}","imageUrl":absolute(request,item.image.url) if item.image else "","bannerUrl":absolute(request,item.banner.url) if item.banner else "","visible":True,"isActive":True,"sortOrder":i} for i,sid in enumerate(ids) if (item:=selected.get(sid))]
                config["cards"]=cards; config["service_ids"]=[item["id"] for item in cards]
            data.append({"id":section.id,"type":section.section_type,"title":section.title,"sort_order":section.sort_order,"is_visible":section.is_visible,"config":config})
        if categories and not any(item["type"]=="category" for item in data):
            data.append({"id":"system-categories","type":"category","title":"الفئات","sort_order":-900,"is_visible":True,"config":{"circles":[{"id":c.id,"title":c.name,"name":c.name,"targetCategory":c.slug,"categorySlug":c.slug,"url":f"/collection?category={quote(c.name)}","route":f"/collection?category={quote(c.name)}","imageUrl":absolute(request,c.image.url) if c.image else "","visible":True,"sortOrder":i} for i,c in enumerate(categories)]}})
        if media and not any(item["type"] in {"hero","banner"} for item in data):
            data.append({"id":"system-media","type":"banner","title":"محتوى عام","sort_order":-800,"is_visible":True,"config":{"slides":[{"id":m.id,"title":m.name,"subtitle":m.alt_text,"ctaLabel":"استكشف الآن" if m.target_url else "","url":m.target_url or "","imageUrl":absolute(request,m.image.url) if m.image else "","visible":True,"sortOrder":i} for i,m in enumerate(media)]}})
        data.sort(key=lambda item:(item.get("sort_order",0),str(item.get("id",""))))
        return Response({"success":True,"data":data})
