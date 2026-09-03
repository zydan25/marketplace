from marketplace.models import Conversation as LegacyConversation, Message as LegacyMessage, Notification as LegacyNotification


class Notification(LegacyNotification):
    class Meta:
        proxy = True
        verbose_name = "إشعار"
        verbose_name_plural = "الإشعارات"


class Conversation(LegacyConversation):
    class Meta:
        proxy = True
        verbose_name = "محادثة"
        verbose_name_plural = "المحادثات"


class Message(LegacyMessage):
    class Meta:
        proxy = True
        verbose_name = "رسالة"
        verbose_name_plural = "الرسائل"
