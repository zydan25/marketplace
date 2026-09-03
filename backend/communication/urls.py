from django.urls import include, path
from rest_framework.routers import DefaultRouter

from marketplace.support_api import (
    AdminSupportCloseView,
    AdminSupportMessageView,
    AdminSupportView,
    SupportEmployeesView,
    SupportMessageView,
    SupportView,
)

from .api import ConversationViewSet, MessageViewSet, NotificationViewSet, OrderChatViewSet, api_info

router = DefaultRouter()
router.register("notifications", NotificationViewSet, basename="notification")
router.register("conversations", ConversationViewSet, basename="conversation")
router.register("messages", MessageViewSet, basename="message")
router.register("order-chats", OrderChatViewSet, basename="order-chat")

urlpatterns = [
    path("", api_info, name="communication-api-info"),
    path("support/", SupportView.as_view(), name="communication-support"),
    path("support/messages/", SupportMessageView.as_view(), name="communication-support-messages"),
    path("support/employees/", SupportEmployeesView.as_view(), name="communication-support-employees"),
    path("support/admin/", AdminSupportView.as_view(), name="communication-admin-support"),
    path("support/admin/<int:conversation_id>/messages/", AdminSupportMessageView.as_view(), name="communication-admin-support-message"),
    path("support/admin/<int:conversation_id>/close/", AdminSupportCloseView.as_view(), name="communication-admin-support-close"),
]
urlpatterns += router.urls
