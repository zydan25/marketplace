from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_http_methods

from .forms import NotificationForm
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


@login_required
@require_http_methods(["GET", "POST"])
def notification_form(request, pk=None):
    user = request.user
    if not (user.is_staff or getattr(user, "role", None) == "admin"):
        return render(request, "admin/domains/form.html", {"title": "إشعار", "error": "إرسال الإشعارات من لوحة الإدارة فقط."}, status=403)
    instance = get_object_or_404(Notification.objects.all(), pk=pk) if pk else Notification()
    form = NotificationForm(request.POST or None, request.FILES or None, instance=instance)
    if request.method == "POST" and form.is_valid():
        obj = form.save(commit=False)
        obj.recipient = None
        obj.save()
        return redirect("admin-dashboard-communication")
    return render(request, "admin/domains/form.html", {"title": "إضافة / تعديل إشعار", "form": form, "cancel_url": "/admin/dashboard/communication/"})
