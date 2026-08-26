import copy
import json
import uuid
from pathlib import Path

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_http_methods

from .models import Category, Product, StorefrontSection, VendorProfile

ALLOWED_SECTION_TYPES = {"hero":"العرض الرئيسي","banner":"بانر إعلاني","category":"الفئات","product_grid":"شبكة المنتجات","trend":"المنتجات الرائجة","tab":"التبويبات"}
TYPE_HELP = {"hero":"صورة رئيسية مع عنوان ووصف وزر وتوجيه وصورة خاصة للهاتف.","banner":"إعلان بصري داخل الصفحة مع صورة وتوجيه اختياري.","category":"فئات مختارة من قاعدة البيانات مع ترتيب وأعمدة.","product_grid":"شبكة منتجات بمصدر وعدد وأعمدة وخصائص بطاقة.","trend":"منتجات رائجة بنفس خيارات الشبكة.","tab":"تبويبات متعددة، لكل تبويب مصدر وعدد منتجات."}

def is_admin(user): return user.is_staff or getattr(user,"role",None)=="admin"
def scope(user):
    if is_admin(user): return None,user
    vendor=VendorProfile.objects.filter(owner=user,status="active").first()
    return (vendor,user) if vendor else (False,user)
def can_edit(user,section): return is_admin(user) or bool(section.vendor_id and section.vendor and section.vendor.owner_id==user.id and section.vendor.status=="active")
def defaults(): return {"published":False,"subtitle":"","image_url":"","mobile_image_url":"","image_position":"center","image_fit":"cover","aspect_ratio":"16:7","overlay":True,"overlay_opacity":30,"text_position":"center","text_align":"center","button_label":"","target_type":"none","target_url":"","target_id":"","source":"latest","category_ids":[],"product_ids":[],"limit":8,"columns_desktop":4,"columns_tablet":3,"columns_mobile":2,"show_images":True,"show_names":True,"show_prices":True,"show_discount":True,"show_rating":False,"show_arrows":True,"mobile_scroll":False,"card_style":"card","image_shape":"rounded","background":"#ffffff","text_color":"#111827","section_padding":"medium","full_width":True,"tabs":[],"__editor_version":8}
def config(section):
    d=defaults(); d.update(section.config or {}); return d
def upload_file(file):
    suffix=Path(file.name or "image.jpg").suffix.lower() or ".jpg"; path=f"storefront/{uuid.uuid4().hex}{suffix}"
    return default_storage.save(path,ContentFile(file.read()))

def visual_editor(request):
    if not (is_admin(request.user) or getattr(request.user,"role",None)=="vendor"): return JsonResponse({"detail":"غير مصرح."},status=403)
    vendor,_=scope(request.user)
    if vendor is False: return JsonResponse({"detail":"التاجر غير نشط أو لا يملك متجرًا."},status=403)
    qs=StorefrontSection.objects.select_related("vendor").order_by("sort_order","id")
    if vendor: qs=qs.filter(vendor=vendor)
    sections=list(qs)
    for s in sections: s.builder_config_json=json.dumps(config(s),ensure_ascii=False)
    cats=list(Category.objects.filter(is_active=True).order_by("sort_order","name"))
    pqs=Product.objects.filter(is_published=True).select_related("vendor").order_by("name")
    if vendor: pqs=pqs.filter(vendor=vendor)
    catalog={"categories":[{"id":c.id,"name":c.name} for c in cats],"products":[{"id":p.id,"name":p.name,"vendor":p.vendor.store_name} for p in pqs[:500]]}
    return render(request,"admin/marketplace/storefront_builder_v2.html",{"sections":sections,"section_types":ALLOWED_SECTION_TYPES,"catalog_json":json.dumps(catalog,ensure_ascii=False),"defaults_json":json.dumps(defaults(),ensure_ascii=False),"type_help":TYPE_HELP})

@require_http_methods(["POST"])
def create_section(request):
    vendor,owner=scope(request.user)
    if vendor is False:return JsonResponse({"detail":"التاجر غير نشط أو لا يملك متجرًا."},status=403)
    try:data=json.loads(request.body or "{}")
    except json.JSONDecodeError:return JsonResponse({"detail":"بيانات غير صالحة."},status=400)
    kind=data.get("section_type","banner")
    if kind not in ALLOWED_SECTION_TYPES:return JsonResponse({"detail":"نوع القسم غير صالح."},status=400)
    last=StorefrontSection.objects.filter(vendor=vendor).order_by("-sort_order","-id").first()
    try:req=int(data.get("sort_order") or 0)
    except (TypeError,ValueError):req=0
    order=req if req>0 else (last.sort_order+1 if last else 1)
    s=StorefrontSection.objects.create(owner=owner,vendor=vendor,title=str(data.get("title") or ALLOWED_SECTION_TYPES[kind])[:180],section_type=kind,sort_order=order,is_visible=False,config=defaults())
    return JsonResponse({"ok":True,"id":s.id})

@require_http_methods(["POST"])
def update_section(request,pk):
    s=get_object_or_404(StorefrontSection.objects.select_related("vendor"),pk=pk)
    if not can_edit(request.user,s):return JsonResponse({"detail":"لا تملك صلاحية هذا القسم."},status=403)
    try:data=json.loads(request.POST.get("payload","{}")) if request.content_type.startswith("multipart/") else json.loads(request.body or "{}")
    except json.JSONDecodeError:return JsonResponse({"detail":"بيانات غير صالحة."},status=400)
    action=data.get("action","save")
    if action=="delete": s.delete(); return JsonResponse({"ok":True})
    if action=="duplicate":
        c=copy.deepcopy(config(s)); c["published"]=False; n=s.sort_order+1
        for x in StorefrontSection.objects.filter(vendor=s.vendor,sort_order__gte=n).order_by("-sort_order"): x.sort_order+=1; x.save(update_fields=["sort_order","updated_at"])
        clone=StorefrontSection.objects.create(owner=request.user,vendor=s.vendor,title=f"{s.title} — نسخة",section_type=s.section_type,sort_order=n,is_visible=False,config=c)
        return JsonResponse({"ok":True,"id":clone.id})
    if action=="publish":
        c=config(s); c["published"]=bool(data.get("published")); s.config=c; s.is_visible=bool(data.get("published")); s.save(update_fields=["config","is_visible","updated_at"]); return JsonResponse({"ok":True,"published":c["published"]})
    kind=data.get("section_type",s.section_type)
    if kind not in ALLOWED_SECTION_TYPES:return JsonResponse({"detail":"نوع القسم غير صالح."},status=400)
    try:order=max(1,int(data.get("sort_order",s.sort_order)))
    except (TypeError,ValueError):return JsonResponse({"detail":"رقم الترتيب غير صالح."},status=400)
    c=defaults(); c.update(data.get("config") or {})
    for field,key,path_key in (("image","image_url","image_path"),("mobile_image","mobile_image_url","mobile_image_path")):
        f=request.FILES.get(field)
        if f:
            if f.size>8*1024*1024:return JsonResponse({"detail":"حجم الصورة يجب ألا يتجاوز 8 ميجابايت."},status=400)
            p=upload_file(f); c[path_key]=p; c[key]=default_storage.url(p)
    s.title=str(data.get("title",s.title))[:180]; s.section_type=kind; s.sort_order=order; s.is_visible=bool(data.get("is_visible",s.is_visible)); s.config=c
    s.save(update_fields=["title","section_type","sort_order","is_visible","config","updated_at"])
    return JsonResponse({"ok":True,"config":c,"order":order})

@require_http_methods(["POST"])
def reorder_sections(request):
    try:items=json.loads(request.body or "{}").get("items",[])
    except (json.JSONDecodeError,TypeError):return JsonResponse({"detail":"بيانات الترتيب غير صالحة."},status=400)
    ids=[];orders=[]
    for item in items:
        try:i,n=int(item["id"]),int(item["order"])
        except (KeyError,TypeError,ValueError):return JsonResponse({"detail":"كل عنصر يحتاج رقمًا صحيحًا."},status=400)
        ids.append(i);orders.append(n)
    if len(ids)!=len(set(ids)) or len(orders)!=len(set(orders)) or any(n<1 for n in orders):return JsonResponse({"detail":"أرقام الترتيب يجب أن تكون موجبة وفريدة."},status=400)
    rows={x.id:x for x in StorefrontSection.objects.filter(id__in=ids).select_related("vendor")}
    if set(ids)!=set(rows):return JsonResponse({"detail":"بعض الأقسام غير موجودة."},status=400)
    if any(not can_edit(request.user,x) for x in rows.values()):return JsonResponse({"detail":"لا يمكنك ترتيب قسم لا تملكه."},status=403)
    for item in items: rows[int(item["id"])].sort_order=int(item["order"]); rows[int(item["id"])].save(update_fields=["sort_order","updated_at"])
    return JsonResponse({"ok":True})

@require_http_methods(["POST"])
def upload_storefront_image(request):
    if not (is_admin(request.user) or getattr(request.user,"role",None)=="vendor"):return JsonResponse({"detail":"غير مصرح."},status=403)
    f=request.FILES.get("image")
    if not f:return JsonResponse({"detail":"اختر صورة."},status=400)
    if f.size>8*1024*1024:return JsonResponse({"detail":"حجم الصورة يجب ألا يتجاوز 8 ميجابايت."},status=400)
    p=upload_file(f);return JsonResponse({"ok":True,"url":default_storage.url(p),"path":p})
