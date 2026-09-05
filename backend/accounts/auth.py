from django.contrib.auth import password_validation
from django.db.models import Q
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView

from marketplace.models import User, Wallet
from marketplace.serializers import UserSerializer
from accounting.models import Wallet as AccountingWallet
from accounting.services import ensure_wallet


class AuthBurstThrottle(AnonRateThrottle):
    scope = "auth"


class SecureLoginView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [AuthBurstThrottle]

    def post(self, request):
        identifier = str(request.data.get("identifier", request.data.get("username", request.data.get("phone", "")))).strip()
        password = str(request.data.get("password", ""))
        if not identifier or not password:
            return Response({"detail": "اسم المستخدم أو رقم الهاتف وكلمة المرور مطلوبان"}, status=status.HTTP_400_BAD_REQUEST)
        user = User.objects.filter(Q(username__iexact=identifier) | Q(phone=identifier)).first()
        if not user or not user.check_password(password) or not user.is_active:
            return Response({"detail": "اسم المستخدم/رقم الهاتف أو كلمة المرور غير صحيحة"}, status=status.HTTP_400_BAD_REQUEST)
        token, _ = Token.objects.get_or_create(user=user)
        try:
            ensure_wallet(user, AccountingWallet.Kinds.CUSTOMER, "YER")
            if getattr(user, "role", None) == "vendor":
                ensure_wallet(user, AccountingWallet.Kinds.VENDOR_PENDING, "YER")
                ensure_wallet(user, AccountingWallet.Kinds.VENDOR_AVAILABLE, "YER")
                ensure_wallet(user, AccountingWallet.Kinds.WITHDRAWAL_HOLD, "YER")
        except Exception:
            # Authentication must remain available even if an accounting migration is pending;
            # the first financial operation will retry wallet initialization atomically.
            pass
        display_name = user.get_full_name() or user.phone or user.username or "العميل"
        return Response({
            "token": token.key,
            "user": UserSerializer(user).data,
            "message": f"مرحبًا {display_name}، تم تسجيل الدخول بنجاح.",
        })


class SecureRegisterView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [AuthBurstThrottle]

    def post(self, request):
        phone = str(request.data.get("phone", "")).strip()
        username = str(request.data.get("username", "")).strip()
        password = str(request.data.get("password", ""))
        if not phone or not password:
            return Response({"detail": "رقم الهاتف وكلمة المرور مطلوبان"}, status=status.HTTP_400_BAD_REQUEST)
        if len(password) < 8:
            return Response({"detail": "كلمة المرور يجب أن تحتوي على 8 أحرف على الأقل"}, status=status.HTTP_400_BAD_REQUEST)
        if User.objects.filter(phone=phone).exists():
            return Response({"detail": "رقم الهاتف مسجل مسبقًا"}, status=status.HTTP_409_CONFLICT)
        if username and User.objects.filter(username__iexact=username).exists():
            return Response({"detail": "اسم المستخدم مستخدم مسبقًا"}, status=status.HTTP_409_CONFLICT)
        user = User(
            phone=phone,
            username=username or phone,
            first_name=request.data.get("first_name", ""),
            middle_name=request.data.get("middle_name", ""),
            third_name=request.data.get("third_name", ""),
            last_name=request.data.get("last_name", ""),
            governorate=request.data.get("governorate", ""),
            role="customer",
        )
        try:
            password_validation.validate_password(password, user=user)
        except Exception as exc:
            return Response({"detail": getattr(exc, "messages", [str(exc)])}, status=status.HTTP_400_BAD_REQUEST)
        user.set_password(password)
        user.save()
        Wallet.objects.get_or_create(user=user)
        ensure_wallet(user, AccountingWallet.Kinds.CUSTOMER, "YER")
        token = Token.objects.create(user=user)
        display_name = user.get_full_name() or user.phone or user.username or "العميل"
        return Response({
            "token": token.key,
            "user": UserSerializer(user).data,
            "message": f"مرحبًا {display_name}، تم إنشاء حسابك وتفعيل محفظتك.",
        }, status=status.HTTP_201_CREATED)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def me(request):
    return Response(UserSerializer(request.user).data)
