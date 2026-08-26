import copy, json, uuid
from pathlib import Path
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.db.models import F
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_http_methods
from .models import Category, Product, StorefrontSection, VendorProfile

SECTION_TYPES={"hero":"العرض الرئيسي","banner":"بانر إعلاني","category":"الفئات","product_grid":"شبكة المنتجات","trend":"المنتجات الرائجة","tab":"التبويبات"}
TYPE_HELP={"hero":"صورة رئيسية مع عنوان ووصف وزر وتوجيه وصورة هاتف.","banner":"بانر ترويجي مع صورة وتوجيه.","category":"اختيار فئات من قاعدة البيانات وترتيبها.","product_grid":"مصدر منتجات وعدد وأعمدة وخصائص بطاقة.","trend":"منتجات رائجة بنفس خيارات الشبكة.","tab":"تبويبات متعددة، لكل تبويب مصدر وعدد منتجات."}

def admin(u): return u.is_staff or getattr(u,"role",None)=="admin"
def vendor_scope(u):
    if admin(u): return None,u
    v=VendorProfile.objects.filter(owner=u,status="active").first()
    return (v,u) if v else (False,u)
def can_edit(u,s): return admin(u) or bool(s.vendor_id and s.vendor and s.vendor.owner_id==u.id and s.vendor.status=="active")
def defaults(): return {"published":False,"subtitle":"","image_url":"","mobile_image_url":"","image_position":"center","image_fit":"cover","aspect_ratio":"16:7","overlay":True,"overlay_opacity":30,"text_position":"center","text_align":"center","button_label":"","target_type":"none","target_url":"","target_id":"","source":"latest","category_ids":[],"product_ids":[],"limit":8,"columns_desktop":4,"columns_tablet":3,"columns_mobile":2,"show_images":True,"show_names":True,"show_prices":True,"show_discount":True,"show_rating":False,"show_arrows":True,"mobile_scroll":False,"card_style":"card","image_shape":"rounded","background":"#ffffff","text_color":"#111827","section_padding":"medium","full_width":True,"tabs":[],"__editor_version":7}
def cfg(s):
    d=defaults(); d.update(s.config or {}); return d
def save_image(f):
    suffix=Path(f.name or "image.jpg").suffix.lower() or ".jpg"; p=f"storefront/{uuid.uuid4().hex}{suffix}"; return default_storage.save(p,ContentFile(f.read()))

@require_http_methods(["GET"])
def builder(request):
    if not (admin(request.user) or getattr(request.user,"role",None)=="vendor"): return JsonResponse({"detail":"غير مصرح."},status=403)
    v,_=vendor_scope(request.user)
    if v is False: return JsonResponse({"detail":"التاجر غير نشط أو لا يملك متجرًا."},status=403)
    qs=StorefrontSection.objects.select_related("vendor").order_by("sort_order","id")
    if v: qs=qs.filter(vendor=v)
    sections=list(qs)
    for s in sections:
        s.builder_config_json=json.dumps(cfg(s),ensure_ascii=False)
    cats=list(Category.objects.filter(is_active=True).order_by("sort_order","name"))
    pqs=Product.objects.filter(is_published=True).select_related("vendor").order_by("name")
    if v: pqs=pqs.filter(vendor=v)
    catalog={"categories":[{"id":c.id,"name":c.name} for c in cats],"products":[{"id":p.id,"name":p.name,"vendor":p.vendor.store_name} for p in pqs[:500]]}
    return render(request,"admin/marketplace/storefront_builder_v2.html",{"sections":sections,"section_types":SECTION_TYPES,"type_help":TYPE_HELP,"catalog_json":json.dumps(catalog,ensure_ascii=False),"defaults_json":json.dumps(defaults(),ensure_ascii=False)})

@require_http_methods(["POST"])
def create(request):
    v,owner=vendor_scope(request.user)
    if v is False: return JsonResponse({"detail":"التاجر غير نشط أو لا يملك متجرًا."},status=403)
    try:d=json.loads(request.body or "{}")
    except json.JSONDecodeError:return JsonResponse({"detail":"بيانات غير صالحة."},status=400)
    kind=d.get("section_type","banner")
    if kind not in SECTION_TYPES:return JsonResponse({"detail":"نوع القسم غير صالح."},status=400)
    last=StorefrontSection.objects.filter(vendor=v).order_by("-sort_order","-id").first()
    requested=int(d.get("sort_order") or 0); order=requested if requested>0 else (last.sort_order+1 if last else 1)
    s=StorefrontSection.objects.create(owner=owner,vendor=v,title=str(d.get("title") or SECTION_TYPES[kind])[:180],section_type=kind,sort_order=order,is_visible=False,config=defaults())
    return JsonResponse({"ok":True,"id":s.id})

@require_http_methods(["POST"])
def save(request,pk):
    s=get_object_or_404(StorefrontSection.objects.select_related("vendor"),pk=pk)
    if not can_edit(request.user,s): return JsonResponse({"detail":"لا تملك صلاحية تعديل هذا القسم."},status=403)
    try:d=json.loads(request.POST.get("payload","{}")) if request.content_type.startswith("multipart/") else json.loads(request.body or "{}")
    except json.JSONDecodeError:return JsonResponse({"detail":"بيانات غير صالحة."},status=400)
    kind=d.get("section_type",s.section_type)
    if kind not in SECTION_TYPES:return JsonResponse({"detail":"نوع القسم غير صالح."},status=400)
    try:order=max(1,int(d.get("sort_order",s.sort_order)))
    except (TypeError,ValueError):return JsonResponse({"detail":"رقم الترتيب غير صالح."},status=400)
    c=defaults(); c.update(d.get("config") or {})
    for field,key,pathkey in (("image","image_url","image_path"),("mobile_image","mobile_image_url","mobile_image_path")):
        f=request.FILES.get(field)
        if f:
            if f.size>8*1024*1024:return JsonResponse({"detail":"حجم الصورة أكبر من 8 ميجابايت."},status=400)
            p=save_image(f); c[pathkey]=p; c[key]=default_storage.url(p)
    s.title=str(d.get("title",s.title))[:180]; s.section_type=kind; s.sort_order=order; s.is_visible=bool(d.get("is_visible",s.is_visible)); s.config=c
    s.save(update_fields=["title","section_type","sort_order","is_visible","config","updated_at"])
    return JsonResponse({"ok":True,"config":c,"order":order})

@require_http_methods(["POST"])
def duplicate(request,pk):
    s=get_object_or_404(StorefrontSection.objects.select_related("vendor"),pk=pk)
    if not can_edit(request.user,s):return JsonResponse({"detail":"لا تملك صلاحية النسخ."},status=403)
    c=copy.deepcopy(cfg(s)); c["published"]=False; n=s.sort_order+1
    StorefrontSection.objects.filter(vendor=s.vendor,sort_order__gte=n).update(sort_order=F("sort_order")+1)
    clone=StorefrontSection.objects.create(owner=request.user,vendor=s.vendor,title=f"{s.title} — نسخة",section_type=s.section_type,sort_order=n,is_visible=False,config=c)
    return JsonResponse({"ok":True,"id":clone.id})

@require_http_methods(["POST"])
def remove(request,pk):
    s=get_object_or_404(StorefrontSection.objects.select_related("vendor"),pk=pk)
    if not can_edit(request.user,s):return JsonResponse({"detail":"لا تملك صلاحية الحذف."},status=403)
    s.delete(); return JsonResponse({"ok":True})

@require_http_methods(["POST"])
def publish(request,pk):
    s=get_object_or_404(StorefrontSection.objects.select_related("vendor"),pk=pk)
    if not can_edit(request.user,s):return JsonResponse({"detail":"لا تملك صلاحية النشر."},status=403)
    val=request.POST.get("published")=="1"; c=cfg(s); c["published"]=val; s.config=c; s.is_visible=val; s.save(update_fields=["config","is_visible","updated_at"]); return JsonResponse({"ok":True,"published":val})

@require_http_methods(["POST"])
def reorder(request):
    try:items=json.loads(request.body or "{}").get("items",[])
    except (json.JSONDecodeError,TypeError):return JsonResponse({"detail":"بيانات الترتيب غير صالحة."},status=400)
    ids=[];nums=[]
    for x in items:
        try:i,n=int(x["id"]),int(x["order"])
        except (KeyError,TypeError,ValueError):return JsonResponse({"detail":"كل عنصر يحتاج رقمًا صحيحًا."},status=400)
        ids.append(i);nums.append(n)
    if len(ids)!=len(set(ids)) or len(nums)!=len(set(nums)) or any(n<1 for n in nums):return JsonResponse({"detail":"أرقام الترتيب يجب أن تكون موجبة وفريدة."},status=400)
    rows={x.id:x for x in StorefrontSection.objects.filter(id__in=ids).select_related("vendor")}
    if set(ids)!=set(rows):return JsonResponse({"detail":"بعض الأقسام غير موجودة."},status=400)
    if any(not can_edit(request.user,x) for x in rows.values()):return JsonResponse({"detail":"لا يمكنك ترتيب قسم لا تملكه."},status=403)
    for x in items: rows[int(x["id"])].sort_order=int(x["order"]); rows[int(x["id"])].save(update_fields=["sort_order","updated_at"])
    return JsonResponse({"ok":True})

@require_http_methods(["POST"])
def upload(request):
    f=request.FILES.get("image")
    if not f:return JsonResponse({"detail":"اختر صورة."},status=400)
    if f.size>8*1024*1024:return JsonResponse({"detail":"حجم الصورة يجب ألا يتجاوز 8 ميجابايت."},status=400)
    p=save_image(f); return JsonResponse({"ok":True,"url":default_storage.url(p),"path":p})
