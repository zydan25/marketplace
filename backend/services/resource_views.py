from decimal import Decimal
from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from django.shortcuts import get_object_or_404, redirect, render
from .models import DigitalProduct, GameProduct, Service, TelecomDenomination, TelecomPlan

def staff_only(user): return bool(user.is_authenticated and (user.is_staff or getattr(user,"role",None)=="admin"))
def d(v): return Decimal(str(v or "0"))
@user_passes_test(staff_only,login_url="/admin/dashboard/login/")
def resources(request):
 if request.method=="POST":
  try:
   a=request.POST.get("action");s=get_object_or_404(Service,pk=request.POST.get("service"))
   common={"name":request.POST.get("name","").strip(),"external_code":request.POST.get("external_code","").strip()}
   if a=="plan":
    TelecomPlan.objects.update_or_create(service=s,external_code=common["external_code"],defaults={"name":common["name"],"provider_num":request.POST.get("provider_num","").strip(),"package_number":request.POST.get("package_number","").strip(),"price":d(request.POST.get("price")),"quota":d(request.POST.get("quota")) if request.POST.get("quota") else None,"quota_unit":request.POST.get("quota_unit","") ,"validity_days":int(request.POST["validity_days"]) if request.POST.get("validity_days") else None,"payment_type":request.POST.get("payment_type","") ,"line_type":request.POST.get("line_type","") ,"metadata":{}})
   elif a=="denom":
    TelecomDenomination.objects.update_or_create(service=s,external_code=common["external_code"],defaults={"name":common["name"],"provider_num":request.POST.get("provider_num","").strip(),"face_value":d(request.POST.get("face_value")),"sale_price":d(request.POST.get("sale_price")),"payment_type":request.POST.get("payment_type","") ,"line_type":request.POST.get("line_type","") ,"metadata":{}})
   elif a=="game":
    GameProduct.objects.update_or_create(service=s,external_code=common["external_code"],defaults={"name":common["name"],"price":d(request.POST.get("price")),"currency":request.POST.get("currency","YER").upper(),"validity_days":int(request.POST["validity_days"]) if request.POST.get("validity_days") else None,"metadata":{}})
   elif a=="digital":
    DigitalProduct.objects.update_or_create(service=s,external_code=common["external_code"],defaults={"name":common["name"],"price":d(request.POST.get("price")),"currency":request.POST.get("currency","YER").upper(),"validity_days":int(request.POST["validity_days"]) if request.POST.get("validity_days") else None,"metadata":{}})
   else: raise ValueError("نوع المورد غير معروف")
   messages.success(request,"تم حفظ الباقة/الخدمة بنجاح.")
  except Exception as e: messages.error(request,f"تعذر الحفظ: {e}")
  return redirect(request.path)
 return render(request,"services/resources_manage.html",{"services":Service.objects.filter(is_active=True).order_by("name"),"plans":TelecomPlan.objects.select_related("service"),"denoms":TelecomDenomination.objects.select_related("service"),"games":GameProduct.objects.select_related("service"),"digital":DigitalProduct.objects.select_related("service")})
