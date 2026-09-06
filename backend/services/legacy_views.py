from decimal import Decimal, InvalidOperation
import json
from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.text import slugify
from .models import DigitalProduct, GameProduct, MainServiceCategory, ProviderConnection, Service, ServiceCategory, ServiceDistribution, ServiceField, ServiceTransaction, TelecomDenomination, TelecomPlan
from .provider import ProviderClient
from .provider_setup import create_or_update_sanaacash_provider

FIELD_LIBRARY=[("full_name","الاسم الرباعي مع اللقب","text"),("name_en","الاسم بالإنجليزي","text"),("card_number","رقم البطاقة","text"),("issue_date","تاريخ الإصدار","date"),("birth_date","تاريخ الميلاد","date"),("mobile","رقم الهاتف","phone"),("sim_number","رقم الشريحة","text"),("card_image","صورة البطاقة الشخصية","image"),("audio","الاستديو / الصوت","audio"),("points","النقاط","number"),("internet_type","أنواع باقات الانترنت","select"),("sim_type","نوع الشريحة","select"),("program","الشريحة / برمجة","select"),("amount","المبلغ","decimal"),("wallet","المحفظة","text"),("wallet_number","رقم المحفظة","text"),("wallet_company","اسم شركة الحوالة","text"),("currency","العملات","select"),("wifi_network","شبكات الواي فاي","select"),("wifi_card","فئات كروت شبكات الواي فاي","select"),("city_from","قائمة المدن (من)","select"),("city_to","قائمة المدن (إلى)","select"),("transport_company","شركات النقل البري","select"),("ticket_type","فئات التذاكر","select"),("travel_date","تاريخ السفر","date"),("sender_name","اسم المرسل","text"),("receiver_name","اسم المستلم","text"),("address","العنوان","text"),("wallet_reference","مرجع الحوالة","text"),("email","البريد الإلكتروني","email"),("player_id","رقم اللاعب","text"),("player_name","اسم اللاعب","text"),("zone_id","زون ايدي","text"),("uniqcode","الكود الموحد","text"),("product_price","سعر المنتج","decimal"),("quantity","الكمية","number"),("total","الإجمالي","decimal"),("contract_number","رقم العقد","text"),("service_details","تفاصيل الخدمة","text")]
FIELD_MAP=dict(FIELD_LIBRARY)
def staff_only(user): return bool(user.is_authenticated and (user.is_staff or getattr(user,"role",None)=="admin"))
def dec(v):
 try:return Decimal(str(v or "0"))
 except (InvalidOperation,ValueError):raise ValueError("القيمة المالية غير صالحة.")
def js(v,d):
 if not v:return d
 try:return json.loads(v)
 except json.JSONDecodeError:raise ValueError("JSON غير صالح.")
def ctx(section):return {"section":section,"mains":MainServiceCategory.objects.all(),"categories":ServiceCategory.objects.select_related("main_category").all(),"services":Service.objects.select_related("category__main_category").prefetch_related("fields").all(),"fields":ServiceField.objects.select_related("service").all(),"providers":ProviderConnection.objects.prefetch_related("links").all(),"links":ProviderConnection.objects.prefetch_related("links").all(),"distributions":ServiceDistribution.objects.select_related("service","provider_link__provider").all(),"plans":TelecomPlan.objects.select_related("service").all(),"denoms":TelecomDenomination.objects.select_related("service").all(),"games":GameProduct.objects.select_related("service").all(),"digital":DigitalProduct.objects.select_related("service").all(),"transactions_count":ServiceTransaction.objects.count(),"field_library":FIELD_LIBRARY}
def choose_link(s,p):
 links=list(p.links.filter(is_active=True).order_by("priority","id"));m=s.metadata or {};code=str(m.get("provider_link_code") or "").strip();x=next((x for x in links if x.code==code),None) if code else None
 if x:return x
 op=str(m.get("provider_operation") or "").lower().strip() or ("query" if s.service_kind==Service.ServiceKinds.QUERY else "catalog" if s.service_kind==Service.ServiceKinds.CATALOG else "bill");xs=[x for x in links if x.operation.lower()==op or op in x.code.lower()];return xs[0] if xs else (links[0] if links else None)
def save_fields(s,keys):
 keys=set(keys)
 for i,k in enumerate(keys):
  label,typ=FIELD_MAP[k];ServiceField.objects.update_or_create(service=s,key=k,defaults={"label":label,"field_type":typ,"required":False,"sort_order":i*10,"is_active":True})
 ServiceField.objects.filter(service=s,key__in=FIELD_MAP).exclude(key__in=keys).update(is_active=False)
@user_passes_test(staff_only,login_url="/admin/dashboard/login/")
def service_center(request,section="overview"):
 if request.method=="POST":
  try:
   a=request.POST.get("action")
   with transaction.atomic():
    if a=="main":
     n=request.POST.get("name","").strip();MainServiceCategory.objects.update_or_create(slug=request.POST.get("slug") or slugify(n,allow_unicode=True),defaults={"name":n,"description":request.POST.get("description","")})
    elif a=="category":
     n=request.POST.get("name","").strip();ServiceCategory.objects.update_or_create(main_category_id=request.POST.get("main_category"),parent_id=request.POST.get("parent") or None,slug=request.POST.get("slug") or slugify(n,allow_unicode=True),defaults={"name":n,"description":request.POST.get("description","")})
    elif a=="service":
     s=Service.objects.filter(pk=request.POST.get("pk") or 0).first() or Service();s.category=get_object_or_404(ServiceCategory,pk=request.POST.get("category"));s.name=request.POST.get("name","").strip();s.code=request.POST.get("code","").strip() or s.code;s.slug=request.POST.get("slug") or slugify(s.name,allow_unicode=True);s.description=request.POST.get("description","");s.service_kind=request.POST.get("service_kind",Service.ServiceKinds.PURCHASE);s.requires_balance=request.POST.get("requires_balance")=="1";s.pricing_mode=request.POST.get("pricing_mode",Service.PricingModes.FIXED);s.price=dec(request.POST.get("price"));s.min_amount=dec(request.POST.get("min_amount")) if request.POST.get("min_amount") else None;s.max_amount=dec(request.POST.get("max_amount")) if request.POST.get("max_amount") else None;s.currency=request.POST.get("currency","YER").upper();s.sort_order=int(request.POST.get("sort_order",0) or 0);m=dict(s.metadata or {});m.update({k:request.POST.get(k,"") for k in ("service_number","price_usd","price_sar","employee_price","submit_label","unified_link_number","duplicate_guard","provider_link_code","provider_operation")});s.metadata=m;s.is_active=True;s.save();save_fields(s,request.POST.getlist("field_keys"))
    elif a=="field":
     s=get_object_or_404(Service,pk=request.POST.get("service"));k=request.POST.get("key","").strip();ServiceField.objects.update_or_create(service=s,key=k,defaults={"label":request.POST.get("label",k),"field_type":request.POST.get("field_type","text"),"required":request.POST.get("required")=="1","secret":request.POST.get("secret")=="1","choices":js(request.POST.get("choices"),[]),"validation":js(request.POST.get("validation"),{}),"default_value":js(request.POST.get("default_value"),None),"sort_order":int(request.POST.get("sort_order",0) or 0),"is_active":True})
    elif a=="toggle":
     mp={"main":MainServiceCategory,"category":ServiceCategory,"service":Service,"field":ServiceField};o=get_object_or_404(mp[request.POST.get("model")],pk=request.POST.get("pk"));o.is_active=not o.is_active;o.save(update_fields=["is_active"])
    elif a=="delete_service":
     s=get_object_or_404(Service,pk=request.POST.get("pk"))
     if s.transactions.exists():s.is_active=False;s.save(update_fields=["is_active"]);messages.warning(request,"للخدمة عمليات تاريخية؛ تم إيقافها بدل حذفها.")
     else:ServiceDistribution.objects.filter(service=s).delete();ServiceField.objects.filter(service=s).delete();TelecomPlan.objects.filter(service=s).delete();TelecomDenomination.objects.filter(service=s).delete();GameProduct.objects.filter(service=s).delete();DigitalProduct.objects.filter(service=s).delete();s.delete();messages.success(request,"تم حذف الخدمة بأمان.")
    else:raise ValueError("عملية غير معروفة.")
   if a not in {"delete_service"}:messages.success(request,"تم الحفظ بنجاح.")
  except Exception as e:messages.error(request,f"تعذر الحفظ: {e}")
  return redirect(request.POST.get("next") or request.path)
 c=ctx(section);sid=request.GET.get("edit_service");c["editing_service"]=Service.objects.prefetch_related("fields").filter(pk=sid).first() if sid else None;return render(request,"services/legacy_dashboard.html",c)
@user_passes_test(staff_only,login_url="/admin/dashboard/login/")
def provider_setup_v2(request):
 if request.method=="POST":
  try:
   a=request.POST.get("action","save");p=get_object_or_404(ProviderConnection,pk=request.POST.get("provider")) if request.POST.get("provider") else None
   if a=="save":p=create_or_update_sanaacash_provider(code=(request.POST.get("code") or slugify(request.POST.get("name", ""))).strip(),name=request.POST.get("name","").strip(),userid=request.POST.get("userid","").strip(),username=request.POST.get("username","").strip(),password=request.POST.get("password") or "",note=request.POST.get("note","").strip(),base_url=request.POST.get("base_url","").strip(),domain_name="");messages.success(request,"تم حفظ الربطية وتهيئة المسارات القياسية.")
   elif a=="balance":r=ProviderClient(p).check_balance();messages.success(request,f"الرصيد: {r.response.get('balance')}") if r.success else messages.error(request,r.description or "تعذر فحص الرصيد")
   elif a=="activate":p.is_active=True;p.links.update(is_active=True);p.save(update_fields=["is_active","updated_at"])
   elif a in {"archive","delete"}:
    if p.links.filter(transactions__isnull=False).exists():ServiceDistribution.objects.filter(provider_link__provider=p).update(is_active=False);p.links.update(is_active=False);p.is_active=False;p.save(update_fields=["is_active","updated_at"]);messages.warning(request,"للربطية عمليات تاريخية؛ تم أرشفتها.")
    else:ServiceDistribution.objects.filter(provider_link__provider=p).delete();p.links.all().delete();p.delete();messages.success(request,"تم حذف الربطية بأمان.")
   else:raise ValueError("عملية غير معروفة")
  except Exception as e:messages.error(request,f"تعذر التنفيذ: {e}")
  return redirect(request.path)
 return render(request,"services/provider_setup_v2.html",{"providers":ProviderConnection.objects.prefetch_related("links").all()})
@user_passes_test(staff_only,login_url="/admin/dashboard/login/")
def distribution_v2(request):
 if request.method=="POST":
  try:
   p=get_object_or_404(ProviderConnection,pk=request.POST.get("provider"),is_active=True);selected={int(x) for x in request.POST.getlist("services") if x.isdigit()};priority=max(1,int(request.POST.get("priority",100) or 100))
   with transaction.atomic():
    ServiceDistribution.objects.filter(provider_link__provider=p).update(is_active=False)
    for s in Service.objects.filter(pk__in=selected,is_active=True):
     link=choose_link(s,p)
     if not link:raise ValueError(f"لا يوجد مسار API فعال للخدمة: {s.name}")
     ServiceDistribution.objects.update_or_create(service=s,provider_link=link,defaults={"priority":priority,"is_active":True,"conditions":{}})
   messages.success(request,f"تم حفظ توزيع {len(selected)} خدمة للربطية {p.name}.")
  except Exception as e:messages.error(request,f"تعذر حفظ التوزيع: {e}")
  return redirect(f"{request.path}?provider={request.POST.get('provider','')}")
 ps=list(ProviderConnection.objects.filter(is_active=True).prefetch_related("links").order_by("name"));pid=request.GET.get("provider") or (str(ps[0].id) if ps else "");selected=set(ServiceDistribution.objects.filter(is_active=True,provider_link__provider_id=pid).values_list("service_id",flat=True)) if pid else set();groups=[]
 for m in MainServiceCategory.objects.filter(is_active=True).order_by("sort_order","id"):
  rows=[(c.name,s) for c in m.categories.filter(is_active=True).order_by("sort_order","id") for s in c.services.filter(is_active=True).order_by("sort_order","id")]
  if rows:groups.append((m,rows))
 return render(request,"services/distribution_v2.html",{"providers":ps,"selected_provider_id":pid,"selected_services":selected,"groups":groups})
