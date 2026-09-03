from django.db.models import Q
from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import BasePermission, IsAuthenticated
from rest_framework.response import Response

from marketplace.order_chat_api import OrderChatViewSet as LegacyOrderChatViewSet
from marketplace.secure_communication import SecureConversationViewSet, SecureNotificationViewSet

from .models import Conversation, Message, Notification


class MessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at", "sender")


class MessagePermission(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        user = request.user
        if user.is_staff or getattr(user, "role", None) == "admin":
            return True
        return obj.sender_id == user.id or obj.conversation.customer_id == user.id or bool(obj.conversation.vendor_id and obj.conversation.vendor.owner_id == user.id)


class NotificationViewSet(SecureNotificationViewSet):
    """Established notification contract exposed from the communication domain."""


class ConversationViewSet(SecureConversationViewSet):
    """Established conversation contract exposed from the communication domain."""


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
            raise serializers.ValidationError({"conversation": "المحادثة غير موجودة."})
        user = self.request.user
        allowed = user.is_staff or getattr(user, "role", None) == "admin" or conversation.customer_id == user.id or (conversation.vendor and conversation.vendor.owner_id == user.id)
        if not allowed:
            raise serializers.ValidationError({"conversation": "لا يمكنك الإرسال إلى هذه المحادثة."})
        if conversation.is_closed:
            raise serializers.ValidationError({"conversation": "المحادثة مغلقة."})
        body = str(self.request.data.get("body", "")).strip()
        if not body and not self.request.FILES.get("attachment"):
            raise serializers.ValidationError({"body": "الرسالة فارغة."})
        serializer.save(sender=user, attachment=self.request.FILES.get("attachment"))

    @action(detail=True, methods=["post"])
    def mark_read(self, request, pk=None):
        message = self.get_object()
        message.is_read = True
        message.save(update_fields=["is_read", "updated_at"])
        return Response({"ok": True})


class OrderChatViewSet(LegacyOrderChatViewSet):
    """Order chat remains business-compatible while its API boundary moves here."""


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def api_info(request):
    return Response({
        "domain": "communication",
        "version": "2",
        "resources": ["notifications", "conversations", "messages", "order-chats", "support"],
    })
