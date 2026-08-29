from django.db.models import Q
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .models import VendorApplication, VendorProfile
from .permissions import IsVendorApplicantOrAdmin, IsVendorOwnerOrAdmin
from .serializers import VendorApplicationSerializer, VendorSerializer
from .services import approve_application, reject_application


class VendorViewSet(viewsets.ModelViewSet):
    serializer_class = VendorSerializer
    lookup_field = "slug"

    def get_queryset(self):
        user = self.request.user
        queryset = VendorProfile.objects.select_related("owner")
        if user.is_authenticated and (user.is_staff or user.role == "admin"):
            pass
        elif user.is_authenticated and user.role == "vendor":
            queryset = queryset.filter(owner=user)
        else:
            queryset = queryset.filter(status="active")
        query = self.request.query_params.get("q", "").strip()
        if query:
            queryset = queryset.filter(Q(store_name__icontains=query) | Q(description__icontains=query) | Q(slug__icontains=query))
        status_filter = self.request.query_params.get("status", "").strip()
        if user.is_authenticated and (user.is_staff or user.role == "admin") and status_filter in {"pending", "active", "suspended"}:
            queryset = queryset.filter(status=status_filter)
        return queryset

    def get_permissions(self):
        if self.action in {"list", "retrieve"}:
            return [AllowAny()]
        return [IsAuthenticated(), IsVendorOwnerOrAdmin()]

    def perform_create(self, serializer):
        user = self.request.user
        if user.role != "vendor":
            raise PermissionDenied("إنشاء المتجر متاح للتاجر فقط")
        if VendorProfile.objects.filter(owner=user).exists():
            raise ValidationError("لديك متجر مرتبط بالحساب بالفعل")
        serializer.save(owner=user, status="pending")

    def perform_update(self, serializer):
        user = self.request.user
        if not (user.is_staff or user.role == "admin") and serializer.instance.owner_id != user.id:
            raise PermissionDenied("لا يمكنك تعديل متجر آخر")
        serializer.save()

    def perform_destroy(self, instance):
        user = self.request.user
        if not (user.is_staff or user.role == "admin") and instance.owner_id != user.id:
            raise PermissionDenied("لا يمكنك تعديل متجر آخر")
        instance.status = "suspended"
        instance.save(update_fields=["status", "updated_at"])

    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated, IsVendorOwnerOrAdmin])
    def suspend(self, request, slug=None):
        vendor = self.get_object()
        vendor.status = "suspended"
        vendor.save(update_fields=["status", "updated_at"])
        return Response(VendorSerializer(vendor).data)

    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated, IsVendorOwnerOrAdmin])
    def activate(self, request, slug=None):
        vendor = self.get_object()
        vendor.status = "active"
        vendor.save(update_fields=["status", "updated_at"])
        return Response(VendorSerializer(vendor).data)


class VendorApplicationViewSet(viewsets.ModelViewSet):
    serializer_class = VendorApplicationSerializer
    permission_classes = [IsAuthenticated, IsVendorApplicantOrAdmin]
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
    def approve(self, request, pk=None):
        if not (request.user.is_staff or request.user.role == "admin"):
            raise PermissionDenied("اعتماد طلبات التجار للإدارة فقط")
        _, application = approve_application(self.get_object(), request.user)
        return Response(VendorApplicationSerializer(application).data)

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        if not (request.user.is_staff or request.user.role == "admin"):
            raise PermissionDenied("رفض طلبات التجار للإدارة فقط")
        application = reject_application(self.get_object(), request.user, request.data.get("review_note", ""))
        return Response(VendorApplicationSerializer(application).data)
