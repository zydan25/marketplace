from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.views.decorators.http import require_GET

from .models import Conversation, Message, Notification


@login_required
@require_GET
def dashboard(request):
    user = request.user
    allowed = user.is_staff or getattr(user, "role", None) in {"admin", "vendor"}
    if not allowed:
        return render(request, "admin/domains/dashboard.html", {"error": "لا تملك صلاحية إدارة التواصل والدعم."}, status=403)
    conversations = Conversation.objects.all()
    messages = Message.objects.all()
    notifications = Notification.objects.all()
    if getattr(user, "role", None) == "vendor" and not user.is_staff:
        conversations = conversations.filter(vendor__owner=user)
        messages = messages.filter(conversation__vendor__owner=user)
        notifications = notifications.filter(recipient=user)
    return render(request, "admin/domains/dashboard.html", {
        "domain_title": "إدارة التواصل والدعم",
        "domain_key": "communication",
        "stats": [
            {"label": "المحادثات", "value": conversations.count()},
            {"label": "الرسائل", "value": messages.count()},
            {"label": "الإشعارات", "value": notifications.count()},
        ],
        "api_prefix": "/api/v2/communication/",
    })
