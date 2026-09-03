from django.contrib import admin

from .order_chat_models import OrderChat, OrderChatMessage


@admin.register(OrderChat)
class OrderChatAdmin(admin.ModelAdmin):
    list_display = ("order", "vendor", "customer", "is_closed", "updated_at")
    list_filter = ("is_closed", "vendor")
    search_fields = ("order__order_number", "vendor__store_name", "customer__phone")
    readonly_fields = ("order", "vendor_order", "vendor", "customer", "created_at", "updated_at")
    ordering = ("-updated_at",)


@admin.register(OrderChatMessage)
class OrderChatMessageAdmin(admin.ModelAdmin):
    list_display = ("chat", "sender", "is_read", "created_at")
    list_filter = ("is_read", "created_at")
    search_fields = ("chat__order__order_number", "sender__phone", "body")
    readonly_fields = ("chat", "sender", "created_at")
