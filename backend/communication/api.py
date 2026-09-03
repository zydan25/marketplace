from django.db.models import Q
from rest_framework import status, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import AllowAny, BasePermission, IsAuthenticated
from rest_framework.response import Response

from .models import Conversation, Message, Notification
from .order_chat_api import OrderChatViewSet
from .serializers import ConversationSerializer, MessageSerializer, NotificationSerializer


class MessagePermission(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        user = request.user
        if user.is_staff or getattr(user, "role", None) == "admin":
            return True
        return (
            obj.sender_id == user.id
            or obj.conversation.customer_id == user.id
            or bool(obj.conversation.vendor_id and obj.conversation.vendor.owner_id == user.id)
        )


class NotificationViewSet(viewsets.ModelViewSet):
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self):
        user = self.request.user
        if user.is_staff or getattr(user, "role", None) == "admin":
            return Notification.objects.all().select_related("product", "recipient")
        return Notification.objects.filter(recipient=user).select_related("product")

    def create(self, request, *args, **kwargs):
        if not (request.user.is_staff or getattr(request.user, "role", None) == "admin"):
            raise PermissionDenied("إنشاء الإشعارات متاح للإدارة فقط")
        return super().create(request, *args, **kwargs)

    def perform_create(self, serializer):
        recipient_id = self.request.data.get("recipient_id")
        if recipient_id:
            recipient = Notification._meta.get_field("recipient").remote_field.model.objects.filter(id=recipient_id).first()
            if not recipient:
                raise ValidationError({"recipient_id": "المستخدم غير موجود"})
            serializer.save(recipient=recipient)
            return
        serializer.save(recipient=None)

    @action(detail=True, methods=["post"])
    def mark_read(self, request, pk=None):
        notification = self.get_object()
        notification.is_read = True
        notification.save(update_fields=["is_read", "updated_at"])
        return Response({"ok": True})


class ConversationViewSet(viewsets.ModelViewSet):
    serializer_class = ConversationSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_queryset(self):
        user = self.request.user
        qs = Conversation.objects.select_related("customer", "vendor", "order").prefetch_related("messages")
        if user.is_staff or getattr(user, "role", None) == "admin":
            return qs
        if getattr(user, "role", None) == "vendor":
            return qs.filter(vendor__owner=user)
        return qs.filter(customer=user)

    def perform_create(self, serializer):
        user = self.request.user
        if getattr(user, "role", None) != "customer":
            raise PermissionDenied("بدء المحادثة متاح للعميل فقط")
        vendor_id = self.request.data.get("vendor")
        from vendors.models import VendorProfile
        vendor = VendorProfile.objects.filter(id=vendor_id, status="active").first() if vendor_id else None
        if not vendor:
            raise ValidationError({"vendor": "التاجر غير موجود أو غير نشط"})
        serializer.save(customer=user, vendor=vendor)

    @action(detail=True, methods=["post"])
    def send_message(self, request, pk=None):
        conversation = self.get_object()
        if conversation.is_closed:
            raise ValidationError("المحادثة مغلقة")
        body = str(request.data.get("body", "")).strip()
        attachment = request.FILES.get("attachment")
        if not body and not attachment:
            raise ValidationError({"body": "الرسالة فارغة"})
        message = Message.objects.create(conversation=conversation, sender=request.user, body=body, attachment=attachment)
        conversation.save(update_fields=["updated_at"])
        return Response(MessageSerializer(message, context={"request": request}).data, status=status.HTTP_201_CREATED)


class MessageViewSet(viewsets.ModelViewSet):
    serializer_class = MessageSerializer
    permission_classes = [MessagePermission]
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_queryset(self):
        user = self.request.user
        qs = Message.objects.select_related("conversation", "sender", "conversation__vendor", "conversation__customer")
        if user.is_staff or getattr(user, "role", None) == "admin":
            return qs
        return qs.filter(Q(sender=user) | Q(conversation__customer=user) | Q(conversation__vendor__owner=user)).distinct()

    def perform_create(self, serializer):
        conversation_id = self.request.data.get("conversation")
        conversation = Conversation.objects.select_related("customer", "vendor").filter(pk=conversation_id).first()
        if not conversation:
            raise ValidationError({"conversation": "المحادثة غير موجودة."})
        user = self.request.user
        allowed = user.is_staff or getattr(user, "role", None) == "admin" or conversation.customer_id == user.id or (conversation.vendor and conversation.vendor.owner_id == user.id)
        if not allowed:
            raise PermissionDenied("لا يمكنك الإرسال إلى هذه المحادثة.")
        if conversation.is_closed:
            raise ValidationError({"conversation": "المحادثة مغلقة."})
        body = str(self.request.data.get("body", "")).strip()
        if not body and not self.request.FILES.get("attachment"):
            raise ValidationError({"body": "الرسالة فارغة."})
        serializer.save(sender=user, attachment=self.request.FILES.get("attachment"))

    @action(detail=True, methods=["post"])
    def mark_read(self, request, pk=None):
        message = self.get_object()
        message.is_read = True
        message.save(update_fields=["is_read", "updated_at"])
        return Response({"ok": True})


@api_view(["GET"])
@permission_classes([AllowAny])
def api_info(request):
    return Response({
        "domain": "communication",
        "version": "2",
        "resources": ["notifications", "conversations", "messages", "order-chats", "support"],
    })
