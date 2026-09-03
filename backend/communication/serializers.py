from rest_framework import serializers

from .models import Conversation, Message, Notification, OrderChat, OrderChatMessage


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ["id", "recipient", "title", "body", "image", "product", "is_read", "audience", "created_at", "updated_at"]
        read_only_fields = ["id", "recipient", "created_at", "updated_at"]


class MessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = ["id", "conversation", "sender", "body", "attachment", "is_read", "created_at", "updated_at"]
        read_only_fields = ["id", "conversation", "sender", "is_read", "created_at", "updated_at"]


class ConversationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Conversation
        fields = ["id", "customer", "vendor", "order", "subject", "is_closed", "created_at", "updated_at"]
        read_only_fields = ["id", "customer", "created_at", "updated_at"]


class OrderChatSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderChat
        fields = ["id", "order", "vendor_order", "customer", "vendor", "subject", "is_closed", "created_at", "updated_at"]
        read_only_fields = fields


class OrderChatMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderChatMessage
        fields = ["id", "chat", "sender", "body", "attachment", "is_read", "created_at"]
        read_only_fields = ["id", "chat", "sender", "is_read", "created_at"]
