from rest_framework import serializers, viewsets, status
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import VendorProfile
from .marketplace_models import VendorOrder
from .order_chat_models import OrderChat, OrderChatMessage


class OrderChatMessageSerializer(serializers.ModelSerializer):
    sender_name = serializers.SerializerMethodField()
    attachment_url = serializers.SerializerMethodField()

    class Meta:
        model = OrderChatMessage
        fields = ["id", "sender", "sender_name", "body", "attachment", "attachment_url", "is_read", "created_at"]
        read_only_fields = ["id", "sender", "sender_name", "attachment_url", "is_read", "created_at"]

    def get_sender_name(self, obj):
        return obj.sender.get_full_name() or obj.sender.phone or obj.sender.username

    def get_attachment_url(self, obj):
        if not obj.attachment:
            return None
        request = self.context.get("request")
        return request.build_absolute_uri(obj.attachment.url) if request else obj.attachment.url


class OrderChatSerializer(serializers.ModelSerializer):
    messages = OrderChatMessageSerializer(many=True, read_only=True)
    vendor_name = serializers.CharField(source="vendor.store_name", read_only=True)
    order_number = serializers.CharField(source="order.order_number", read_only=True)

    class Meta:
        model = OrderChat
        fields = ["id", "order", "vendor_order", "vendor", "vendor_name", "order_number", "customer", "subject", "is_closed", "messages", "created_at", "updated_at"]
        read_only_fields = ["id", "vendor", "customer", "messages", "created_at", "updated_at"]


class OrderChatViewSet(viewsets.ModelViewSet):
    serializer_class = OrderChatSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self):
        user = self.request.user
        qs = OrderChat.objects.select_related("order", "vendor_order", "vendor", "customer").prefetch_related("messages__sender")
        if user.is_staff or user.role == "admin":
            return qs
        if user.role == "vendor":
            return qs.filter(vendor__owner=user)
        return qs.filter(customer=user)

    @action(detail=False, methods=["post"])
    def ensure_for_vendor_order(self, request):
        vendor_order_id = request.data.get("vendor_order_id")
        if not vendor_order_id:
            raise ValidationError({"vendor_order_id": "مطلوب"})
        try:
            vendor_order = VendorOrder.objects.select_related("order", "vendor", "vendor__owner").get(pk=int(vendor_order_id))
        except (ValueError, VendorOrder.DoesNotExist):
            raise ValidationError({"vendor_order_id": "طلب التاجر غير موجود"})
        user = request.user
        if user.role == "customer":
            if vendor_order.order.customer_id != user.id:
                raise PermissionDenied("لا تملك هذا الطلب")
        elif user.role == "vendor":
            if vendor_order.vendor.owner_id != user.id:
                raise PermissionDenied("لا تملك هذا الطلب")
        elif not (user.is_staff or user.role == "admin"):
            raise PermissionDenied("غير مصرح")
        chat, _ = OrderChat.objects.get_or_create(
            order=vendor_order.order,
            vendor=vendor_order.vendor,
            vendor_order=vendor_order,
            customer=vendor_order.order.customer,
            defaults={"subject": f"محادثة الطلب {vendor_order.order.order_number}"},
        )
        return Response(OrderChatSerializer(chat, context={"request": request}).data)

    @action(detail=True, methods=["post"])
    def send_message(self, request, pk=None):
        chat = self.get_object()
        if chat.is_closed:
            raise ValidationError("المحادثة مغلقة")
        body = str(request.data.get("body", "")).strip()
        attachment = request.FILES.get("attachment")
        if not body and not attachment:
            raise ValidationError({"body": "الرسالة فارغة"})
        message = OrderChatMessage.objects.create(chat=chat, sender=request.user, body=body, attachment=attachment)
        chat.save(update_fields=["updated_at"])
        return Response(OrderChatMessageSerializer(message, context={"request": request}).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def mark_read(self, request, pk=None):
        chat = self.get_object()
        chat.messages.exclude(sender=request.user).filter(is_read=False).update(is_read=True)
        return Response({"ok": True})
