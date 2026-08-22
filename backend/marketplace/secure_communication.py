from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Conversation, Message, Notification, VendorProfile
from .serializers import ConversationSerializer, MessageSerializer, NotificationSerializer


class SecureNotificationViewSet(viewsets.ModelViewSet):
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self):
        user = self.request.user
        if user.is_staff or user.role == "admin":
            return Notification.objects.all().select_related("product", "recipient")
        return Notification.objects.filter(recipient=user).select_related("product")

    def create(self, request, *args, **kwargs):
        if not (request.user.is_staff or request.user.role == "admin"):
            raise PermissionDenied("إنشاء الإشعارات متاح للإدارة فقط")
        return super().create(request, *args, **kwargs)

    def perform_create(self, serializer):
        recipient_id = self.request.data.get("recipient_id")
        if recipient_id:
            from .models import User
            recipient = User.objects.filter(id=recipient_id).first()
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


class SecureConversationViewSet(viewsets.ModelViewSet):
    serializer_class = ConversationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        qs = Conversation.objects.select_related("customer", "vendor", "order").prefetch_related("messages")
        if user.is_staff or user.role == "admin":
            return qs
        if user.role == "vendor":
            return qs.filter(vendor__owner=user)
        return qs.filter(customer=user)

    def perform_create(self, serializer):
        user = self.request.user
        if user.role != "customer":
            raise PermissionDenied("بدء المحادثة متاح للعميل فقط")
        vendor_id = self.request.data.get("vendor")
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
        if not body and not request.FILES.get("attachment"):
            raise ValidationError({"body": "الرسالة فارغة"})
        message = Message.objects.create(
            conversation=conversation,
            sender=request.user,
            body=body,
            attachment=request.FILES.get("attachment"),
        )
        return Response(MessageSerializer(message, context={"request": request}).data, status=status.HTTP_201_CREATED)
