import hashlib
import secrets
from datetime import timedelta
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from .models import User
from .engagement_models import PasswordResetRequest

class PasswordResetWhatsAppRequestView(APIView):
    permission_classes=[AllowAny]
    def post(self,request):
        phone=str(request.data.get("phone","")).strip()
        if not phone: raise ValidationError({"phone":"رقم واتساب مطلوب."})
        user=User.objects.filter(phone=phone,is_active=True).first()
        # لا نكشف وجود الحساب للعميل.
        if user:
            raw=secrets.token_urlsafe(32); digest=hashlib.sha256(raw.encode()).hexdigest()
            PasswordResetRequest.objects.filter(user=user,used_at__isnull=True).update(used_at=timezone.now())
            PasswordResetRequest.objects.create(user=user,token_hash=digest,expires_at=timezone.now()+timedelta(minutes=15),requested_phone=phone)
            reset_url=request.build_absolute_uri(f"/api/auth/reset-password/{raw}/")
            store_phone=getattr(settings,"WHATSAPP_STORE_NUMBER","") or getattr(settings,"MARKETPLACE_WHATSAPP_NUMBER","")
            text=f"طلب استعادة كلمة المرور\nرقم العميل: {phone}\nرابط الاستعادة: {reset_url}\nينتهي الرابط خلال 15 دقيقة."
            from urllib.parse import quote
            wa_url=f"https://wa.me/{store_phone}?text={quote(text)}" if store_phone else ""
        else: wa_url=""
        return Response({"success":True,"message":"إذا كان الرقم مسجلاً فسيتم تجهيز رسالة الاستعادة.","whatsapp_url":wa_url})

class PasswordResetConfirmView(APIView):
    permission_classes=[AllowAny]
    @transaction.atomic
    def post(self,request,token):
        digest=hashlib.sha256(str(token).encode()).hexdigest()
        reset=PasswordResetRequest.objects.select_for_update().select_related("user").filter(token_hash=digest,used_at__isnull=True,expires_at__gt=timezone.now()).first()
        if not reset: raise ValidationError({"token":"رابط الاستعادة غير صالح أو منتهي."})
        password=str(request.data.get("password", ""))
        if len(password)<6: raise ValidationError({"password":"كلمة المرور يجب أن تكون 6 أحرف على الأقل."})
        reset.user.set_password(password); reset.user.save(update_fields=["password"]); reset.used_at=timezone.now(); reset.save(update_fields=["used_at","updated_at"])
        return Response({"success":True,"message":"تم تحديث كلمة المرور بنجاح."})
