from django.db import transaction
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .marketplace_models import VendorApplication
from .models import User, VendorProfile
from .serializers import VendorApplicationSerializer


class VendorApplicationViewSet(viewsets.ModelViewSet):
    serializer_class = VendorApplicationSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_queryset(self):
        user = self.request.user
        if user.is_staff or user.role == "admin":
            return VendorApplication.objects.select_related("applicant", "reviewed_by")
        return VendorApplication.objects.filter(applicant=user)

    def perform_create(self, serializer):
        user = self.request.user
        if user.role == "vendor":
            raise ValidationError("الحساب مرتبط بتاجر بالفعل")
        if VendorApplication.objects.filter(applicant=user).exists():
            raise ValidationError("يوجد طلب تاجر سابق لهذا الحساب")
        serializer.save(applicant=user, status=VendorApplication.Status.PENDING)

    @action(detail=True, methods=["post"])
    @transaction.atomic
    def approve(self, request, pk=None):
        if not (request.user.is_staff or request.user.role == "admin"):
            raise PermissionDenied("اعتماد التجار للإدارة فقط")
        application = self.get_object()
        if application.status != VendorApplication.Status.PENDING:
            raise ValidationError("الطلب ليس بانتظار المراجعة")
        user = User.objects.select_for_update().get(pk=application.applicant_id)
        if VendorProfile.objects.filter(owner=user).exists():
            application.status = VendorApplication.Status.APPROVED
            application.reviewed_by = request.user
            application.reviewed_at = timezone.now()
            application.save(update_fields=["status", "reviewed_by", "reviewed_at", "updated_at"])
            return Response(VendorApplicationSerializer(application).data)
        user.role = User.Roles.VENDOR
        user.save(update_fields=["role"])
        VendorProfile.objects.create(owner=user, store_name=application.store_name, description=application.description, phone=application.phone, address=application.address, status="active")
        application.status = VendorApplication.Status.APPROVED
        application.reviewed_by = request.user
        application.reviewed_at = timezone.now()
        application.save(update_fields=["status", "reviewed_by", "reviewed_at", "updated_at"])
        return Response(VendorApplicationSerializer(application).data)

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        if not (request.user.is_staff or request.user.role == "admin"):
            raise PermissionDenied("رفض التجار للإدارة فقط")
        application = self.get_object()
        if application.status != VendorApplication.Status.PENDING:
            raise ValidationError("الطلب ليس بانتظار المراجعة")
        application.status = VendorApplication.Status.REJECTED
        application.reviewed_by = request.user
        application.reviewed_at = timezone.now()
        application.review_note = str(request.data.get("review_note", "")).strip()
        application.save(update_fields=["status", "reviewed_by", "reviewed_at", "review_note", "updated_at"])
        return Response(VendorApplicationSerializer(application).data)
