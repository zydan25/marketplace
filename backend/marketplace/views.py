import uuid
from decimal import Decimal

from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.authtoken.models import Token
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import (
    Category,
    Conversation,
    Coupon,
    DesignTheme,
    Message,
    Notification,
    Order,
    OrderItem,
    Product,
    StorefrontSection,
    User,
    VendorProfile,
    Wallet,
    WalletTransaction,
)
from .permissions import IsAdminRole, IsVendorRole
from .serializers import (
    CategorySerializer,
    ConversationSerializer,
    CouponSerializer,
    DesignThemeSerializer,
    MessageSerializer,
    NotificationSerializer,
    OrderSerializer,
    ProductSerializer,
    StorefrontSectionSerializer,
    UserSerializer,
    VendorSerializer,
    WalletSerializer,
)


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        phone = str(request.data.get("phone", "")).strip()
        password = request.data.get("password", "")
        user = User.objects.filter(phone=phone).first()
        if not user or not user.check_password(password) or not user.is_active:
            return Response({"detail": "رقم الهاتف أو كلمة المرور غير صحيحة"}, status=status.HTTP_400_BAD_REQUEST)
        token, _ = Token.objects.get_or_create(user=user)
        return Response({"token": token.key, "user": UserSerializer(user).data})


class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        phone = str(request.data.get("phone", "")).strip()
        password = request.data.get("password", "")
        if not phone or len(password) < 6:
            return Response({"detail": "رقم الهاتف وكلمة مرور من ستة أحرف على الأقل مطلوبان"}, status=status.HTTP_400_BAD_REQUEST)
        if User.objects.filter(phone=phone).exists():
            return Response({"detail": "رقم الهاتف مسجل مسبقًا"}, status=status.HTTP_409_CONFLICT)
        user = User(
            phone=phone,
            username=phone,
            first_name=request.data.get("first_name", ""),
            middle_name=request.data.get("middle_name", ""),
            third_name=request.data.get("third_name", ""),
            last_name=request.data.get("last_name", ""),
            governorate=request.data.get("governorate", ""),
            role="customer",
        )
        user.set_password(password)
        user.save()
        Wallet.objects.create(user=user)
        token = Token.objects.create(user=user)
        return Response({"token": token.key, "user": UserSerializer(user).data}, status=status.HTTP_201_CREATED)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def me(request):
    return Response(UserSerializer(request.user).data)


class VendorViewSet(viewsets.ModelViewSet):
    queryset = VendorProfile.objects.filter(status="active").select_related("owner")
    serializer_class = VendorSerializer
    lookup_field = "slug"

    def get_permissions(self):
        if self.action in {"create", "update", "partial_update", "destroy"}:
            return [IsAuthenticated(), IsVendorRole()]
        return [AllowAny()]

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.request.user.is_authenticated and self.request.user.role in {"admin", "vendor"} and self.action in {"list", "retrieve"}:
            if self.request.user.role == "vendor":
                return VendorProfile.objects.filter(owner=self.request.user).select_related("owner")
            return VendorProfile.objects.all().select_related("owner")
        return queryset


class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.filter(is_active=True)
    serializer_class = CategorySerializer
    permission_classes = [AllowAny]


class ProductViewSet(viewsets.ModelViewSet):
    serializer_class = ProductSerializer
    # التطبيق يمرر رقم المنتج من البطاقة؛ هذا يمنع ظهور «الصنف غير موجود».
    lookup_field = "pk"

    def get_queryset(self):
        queryset = Product.objects.filter(is_published=True).select_related("vendor", "vendor__owner").prefetch_related("categories", "image_items")
        if self.request.user.is_authenticated and self.request.user.role == "vendor":
            queryset = Product.objects.filter(vendor__owner=self.request.user).select_related("vendor", "vendor__owner").prefetch_related("categories", "image_items")
        query = self.request.query_params.get("q")
        vendor = self.request.query_params.get("vendor")
        category = self.request.query_params.get("category")
        trending = self.request.query_params.get("trending")
        if query:
            queryset = queryset.filter(Q(name__icontains=query) | Q(sku__icontains=query) | Q(description__icontains=query))
        if vendor:
            queryset = queryset.filter(vendor__slug=vendor)
        if category:
            queryset = queryset.filter(categories__slug=category)
        if trending == "1":
            queryset = queryset.filter(is_trending=True)
        return queryset.distinct()

    def get_permissions(self):
        if self.action in {"create", "update", "partial_update", "destroy"}:
            return [IsAuthenticated(), IsVendorRole()]
        return [AllowAny()]

    def perform_create(self, serializer):
        vendor = VendorProfile.objects.get(owner=self.request.user)
        serializer.save(vendor=vendor)

    def perform_update(self, serializer):
        vendor = VendorProfile.objects.get(owner=self.request.user)
        if serializer.instance.vendor_id != vendor.id:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("لا يمكنك تعديل منتج متجر آخر")
        serializer.save()


class DesignThemeViewSet(viewsets.ModelViewSet):
    serializer_class = DesignThemeSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        global_themes = DesignTheme.objects.filter(is_global=True, is_active=True)
        if self.request.user.role == "vendor":
            vendor_themes = DesignTheme.objects.filter(vendor__owner=self.request.user)
            return (global_themes | vendor_themes).distinct()
        if self.request.user.role == "admin" or self.request.user.is_staff:
            return DesignTheme.objects.all()
        return global_themes

    def perform_create(self, serializer):
        if self.request.user.role == "vendor":
            vendor = VendorProfile.objects.get(owner=self.request.user)
            serializer.save(owner=self.request.user, vendor=vendor, is_global=False)
        else:
            serializer.save(owner=self.request.user, is_global=True)


class StorefrontSectionViewSet(viewsets.ModelViewSet):
    serializer_class = StorefrontSectionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = StorefrontSection.objects.filter(is_visible=True)
        if self.request.user.role == "vendor":
            return StorefrontSection.objects.filter(Q(vendor__owner=self.request.user) | Q(vendor__isnull=True), is_visible=True)
        if self.request.user.role in {"admin", "vendor"} or self.request.user.is_staff:
            return StorefrontSection.objects.all()
        return queryset.filter(vendor__isnull=True)

    def perform_create(self, serializer):
        vendor = None
        if self.request.user.role == "vendor":
            vendor = VendorProfile.objects.get(owner=self.request.user)
        serializer.save(owner=self.request.user, vendor=vendor)


class WalletViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = WalletSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Wallet.objects.filter(user=self.request.user).prefetch_related("transactions")

    @action(detail=True, methods=["post"])
    def top_up_request(self, request, pk=None):
        wallet = self.get_object()
        if wallet.is_locked:
            return Response({"detail": "المحفظة مقفلة"}, status=status.HTTP_403_FORBIDDEN)
        amount = Decimal(str(request.data.get("amount", "0")))
        if amount <= 0:
            return Response({"detail": "أدخل مبلغًا موجبًا"}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"status": "pending", "amount": str(amount), "message": "تم إنشاء طلب شحن الرصيد للمراجعة"}, status=status.HTTP_202_ACCEPTED)


from .cart_service import CartService

class CartCalculateView(APIView):
    permission_classes = [AllowAny]
    
    def post(self, request):
        items = request.data.get("items", [])
        city_id = request.data.get("city_id")
        
        result = CartService.calculate_cart(items, city_id)
        
        if not result["valid"]:
            return Response({"detail": "يوجد مشكلة في السلة", "errors": result["errors"]}, status=status.HTTP_400_BAD_REQUEST)
            
        return Response(result)

class OrderViewSet(viewsets.ModelViewSet):
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_queryset(self):
        user = self.request.user
        if user.role == "vendor":
            return Order.objects.filter(items__vendor__owner=user).distinct().prefetch_related("items")
        if user.role == "admin" or user.is_staff:
            return Order.objects.all().prefetch_related("items")
        return Order.objects.filter(customer=user).prefetch_related("items")

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        if request.user.role != "customer":
            return Response({"detail": "إنشاء الطلب متاح للعملاء فقط"}, status=status.HTTP_403_FORBIDDEN)
        items = request.data.get("items", [])
        if not items:
            return Response({"detail": "لا يمكن إنشاء طلب فارغ"}, status=status.HTTP_400_BAD_REQUEST)
        subtotal = Decimal("0")
        prepared = []
        for row in items:
            try:
                product = Product.objects.select_for_update().get(pk=row["product_id"], is_published=True)
                quantity = int(row.get("quantity", 1))
            except (Product.DoesNotExist, KeyError, TypeError, ValueError):
                return Response({"detail": "أحد المنتجات غير صالح"}, status=status.HTTP_400_BAD_REQUEST)
            if quantity < 1 or product.stock < quantity:
                return Response({"detail": f"الكمية غير متاحة للمنتج {product.name}"}, status=status.HTTP_400_BAD_REQUEST)
            
            from .services import PricingEngine
            from .models import City
            city_id = request.data.get("shipping_address", {}).get("city_id")
            city = City.objects.filter(id=city_id).first() if city_id else None
            
            pricing = PricingEngine.calculate(product, city, quantity)
            unit_price = pricing["unit_final_price"]
            line_total = pricing["total_price"]
            
            subtotal += line_total
            prepared.append((product, quantity, row, unit_price, line_total))
        
        shipping_fee = city.shipping_fee if city else Decimal(str(request.data.get("shipping_fee", "0")))
        discount = Decimal(str(request.data.get("discount", "0")))
        total = max(Decimal("0"), subtotal + shipping_fee - discount)
        order = Order.objects.create(
            customer=request.user,
            order_number=f"ORD-{timezone.now():%Y%m%d}-{uuid.uuid4().hex[:6].upper()}",
            subtotal=subtotal,
            shipping_fee=shipping_fee,
            discount=discount,
            total=total,
            currency=request.data.get("currency", "YER"),
            shipping_address=request.data.get("shipping_address", {}),
            payment_method=request.data.get("payment_method", "cash_on_delivery"),
        )
        for product, quantity, row, unit_price, line_total in prepared:
            vendor = product.vendor
            commission = (line_total * vendor.commission_percent / Decimal("100")).quantize(Decimal("0.01"))
            OrderItem.objects.create(
                order=order,
                vendor=vendor,
                product=product,
                name_snapshot=product.name,
                sku_snapshot=product.sku,
                quantity=quantity,
                unit_price=unit_price,
                color=row.get("color", ""),
                size=row.get("size", ""),
                vendor_total=line_total,
                commission=commission,
                vendor_net=line_total - commission,
            )
            product.stock -= quantity
            product.save(update_fields=["stock", "updated_at"])
        return Response(OrderSerializer(order).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def update_status(self, request, pk=None):
        order = self.get_object()
        if request.user.role == "vendor" and not order.items.filter(vendor__owner=request.user).exists():
            return Response({"detail": "لا تملك صلاحية هذا الطلب"}, status=status.HTTP_403_FORBIDDEN)
        new_status = request.data.get("status")
        valid = {choice.value for choice in Order.Status}
        if new_status not in valid:
            return Response({"detail": "حالة الطلب غير صالحة"}, status=status.HTTP_400_BAD_REQUEST)
        old_status = order.status
        order.status = new_status
        order.save(update_fields=["status", "updated_at"])
        
        from .models import OrderStatusHistory
        OrderStatusHistory.objects.create(
            order=order,
            old_status=old_status,
            new_status=new_status,
            changed_by=request.user
        )
        
        from .notification_service import NotificationService
        NotificationService.send_order_status_update(order)
        
        return Response(OrderSerializer(order).data)


class NotificationViewSet(viewsets.ModelViewSet):
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return Notification.objects.filter(Q(recipient=user) | Q(recipient__isnull=True)).select_related("product")

    def perform_create(self, serializer):
        serializer.save(recipient=self.request.user)

    @action(detail=True, methods=["post"])
    def mark_read(self, request, pk=None):
        notification = self.get_object()
        notification.is_read = True
        notification.save(update_fields=["is_read", "updated_at"])
        return Response({"ok": True})


class ConversationViewSet(viewsets.ModelViewSet):
    serializer_class = ConversationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role == "vendor":
            return Conversation.objects.filter(vendor__owner=user).prefetch_related("messages")
        if user.role == "admin" or user.is_staff:
            return Conversation.objects.all().prefetch_related("messages")
        return Conversation.objects.filter(customer=user).prefetch_related("messages")

    def perform_create(self, serializer):
        serializer.save(customer=self.request.user)

    @action(detail=True, methods=["post"])
    def send_message(self, request, pk=None):
        conversation = self.get_object()
        message = Message.objects.create(conversation=conversation, sender=request.user, body=request.data.get("body", ""), attachment=request.FILES.get("attachment"))
        return Response(MessageSerializer(message).data, status=status.HTTP_201_CREATED)


class AdminDashboardView(APIView):
    permission_classes = [IsAuthenticated, IsAdminRole]

    def get(self, request):
        return Response({
            "users": User.objects.count(),
            "customers": User.objects.filter(role="customer").count(),
            "vendors": VendorProfile.objects.count(),
            "pending_vendors": VendorProfile.objects.filter(status="pending").count(),
            "products": Product.objects.count(),
            "orders": Order.objects.count(),
            "pending_orders": Order.objects.filter(status="pending").count(),
            "wallets": Wallet.objects.count(),
        })
