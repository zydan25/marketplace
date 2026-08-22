from django.conf import settings
from django.db import models


class OrderChat(models.Model):
    """One private customer↔vendor chat for each vendor side of an order."""

    order = models.ForeignKey("marketplace.Order", on_delete=models.CASCADE, related_name="order_chats")
    vendor_order = models.OneToOneField("marketplace.VendorOrder", on_delete=models.CASCADE, related_name="order_chat")
    customer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="order_chats_as_customer")
    vendor = models.ForeignKey("marketplace.VendorProfile", on_delete=models.CASCADE, related_name="order_chats")
    subject = models.CharField(max_length=180, blank=True)
    is_closed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at", "-id"]
        constraints = [
            models.UniqueConstraint(fields=["order", "vendor"], name="uniq_order_chat_per_vendor"),
        ]
        indexes = [
            models.Index(fields=["customer", "updated_at"]),
            models.Index(fields=["vendor", "updated_at"]),
            models.Index(fields=["order", "vendor"]),
        ]


class OrderChatMessage(models.Model):
    chat = models.ForeignKey(OrderChat, on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="order_chat_messages")
    body = models.TextField(blank=True)
    attachment = models.ImageField(upload_to="order_chats/", blank=True, null=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "id"]
        indexes = [
            models.Index(fields=["chat", "created_at"]),
            models.Index(fields=["chat", "is_read"]),
        ]
