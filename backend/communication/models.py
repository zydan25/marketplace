from django.conf import settings
from django.db import models


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Notification(TimeStampedModel):
    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications", null=True, blank=True)
    title = models.CharField(max_length=180)
    body = models.TextField()
    image = models.ImageField(upload_to="notifications/", blank=True, null=True)
    product = models.ForeignKey("catalog.Product", on_delete=models.SET_NULL, null=True, blank=True, related_name="notifications")
    is_read = models.BooleanField(default=False)
    audience = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "marketplace_notification"


class Conversation(TimeStampedModel):
    customer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="customer_conversations")
    vendor = models.ForeignKey("vendors.VendorProfile", on_delete=models.CASCADE, related_name="conversations", null=True, blank=True)
    order = models.OneToOneField("orders.Order", on_delete=models.CASCADE, related_name="conversation", null=True, blank=True)
    subject = models.CharField(max_length=180, blank=True)
    is_closed = models.BooleanField(default=False)

    class Meta:
        db_table = "marketplace_conversation"


class Message(TimeStampedModel):
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="sent_messages")
    body = models.TextField(blank=True)
    attachment = models.ImageField(upload_to="messages/", blank=True, null=True)
    is_read = models.BooleanField(default=False)

    class Meta:
        db_table = "marketplace_message"


__all__ = ["Conversation", "Message", "Notification"]
