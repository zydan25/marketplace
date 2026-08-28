from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Conversation, Message, User


def message_payload(request, message):
    attachment = request.build_absolute_uri(message.attachment.url) if message.attachment else None
    role = "admin" if message.sender.role == "admin" or message.sender.is_staff else "customer"
    return {"id": message.id, "senderRole": role, "senderId": message.sender_id, "senderName": message.sender.get_full_name() or message.sender.phone or "موظف", "body": message.body, "attachmentUrl": attachment, "createdAt": message.created_at.isoformat()}


def conversation_payload(request, conversation):
    return {
        "id": conversation.id,
        "customerId": conversation.customer_id,
        "subject": conversation.subject,
        "isClosed": conversation.is_closed,
        "messages": [message_payload(request, message) for message in conversation.messages.select_related("sender").order_by("created_at")],
    }


class SupportView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        conversation = Conversation.objects.filter(customer=request.user, vendor__isnull=True).order_by("-updated_at").first()
        if not conversation:
            conversation = Conversation.objects.create(customer=request.user, vendor=None, subject="تواصل مع الإدارة")
        staff = User.objects.filter(is_active=True).filter(role="admin") | User.objects.filter(is_active=True, is_staff=True)
        staff = staff.distinct().order_by("first_name", "last_name", "id")
        employees = [{"id": item.id, "name": item.get_full_name() or item.phone or "موظف الإدارة", "role": "مدير" if item.role == "admin" else "موظف دعم", "avatar": request.build_absolute_uri(item.avatar.url) if item.avatar else None} for item in staff]
        return Response({"conversation": conversation_payload(request, conversation), "employees": employees})


class SupportMessageView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if request.user.role != "customer":
            raise PermissionDenied("مراسلة دعم العملاء مخصصة للعميل")
        body = str(request.data.get("body", "")).strip()
        if not body:
            raise ValidationError({"body": "اكتب الرسالة أولًا."})
        conversation = Conversation.objects.filter(customer=request.user, vendor__isnull=True).order_by("-updated_at").first()
        if not conversation:
            conversation = Conversation.objects.create(customer=request.user, vendor=None, subject="تواصل مع الإدارة")
        if conversation.is_closed:
            conversation.is_closed = False
            conversation.save(update_fields=["is_closed", "updated_at"])
        message = Message.objects.create(conversation=conversation, sender=request.user, body=body)
        return Response({"conversation": conversation_payload(request, conversation), "message": message_payload(request, message)}, status=201)


class SupportEmployeesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not (request.user.role == "admin" or request.user.is_staff):
            raise PermissionDenied("للوصول إلى قائمة الموظفين يلزم حساب الإدارة")
        staff = (User.objects.filter(is_active=True, role="admin") | User.objects.filter(is_active=True, is_staff=True)).distinct().order_by("first_name", "last_name", "id")
        return Response({"employees": [{"id": item.id, "name": item.get_full_name() or item.phone or "موظف الإدارة", "role": "مدير" if item.role == "admin" else "موظف دعم"} for item in staff]})
