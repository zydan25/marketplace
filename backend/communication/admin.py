from django.contrib import admin

from .models import Conversation, Message, Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("title", "recipient", "product", "is_read", "created_at")
    list_filter = ("is_read", "created_at")
    search_fields = ("title", "body", "recipient__phone", "recipient__username", "product__name")


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ("customer", "vendor", "order", "subject", "is_closed", "updated_at")
    list_filter = ("is_closed",)
    search_fields = ("customer__phone", "customer__username", "vendor__store_name", "subject", "order__order_number")


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ("conversation", "sender", "body", "is_read", "created_at")
    list_filter = ("is_read",)
    search_fields = ("body", "sender__phone", "sender__username", "conversation__subject")
