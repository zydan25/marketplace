import base64
import binascii
import hashlib

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.db.models import Q
from rest_framework import serializers, viewsets
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated

from .api_policy import IsVendorOrAdmin
from .models import DesignTheme, StorefrontSection, VendorProfile
from .serializers import DesignThemeSerializer, VendorSerializer
from catalog.api import CategoryViewSet as SecureCategoryViewSet
from catalog.api import ProductViewSet as SecureProductViewSet


class MediaStorefrontSectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = StorefrontSection
        fields = ["id", "title", "section_type", "vendor", "config", "sort_order", "is_visible"]
        read_only_fields = ["id"]

    def _persist_storefront_data_urls(self, value, section_id):
        if isinstance(value, list):
            return [self._persist_storefront_data_urls(item, section_id) for item in value]
        if not isinstance(value, dict):
            return value
        result = dict(value)
        request = self.context.get("request")
        for key, item in list(result.items()):
            if key in {"imageUrl", "image_url"} and isinstance(item, str) and item.startswith("data:image/") and ";base64," in item:
                try:
                    header, encoded = item.split(";base64,", 1)
                    mime = header.split("/", 1)[1].split(";", 1)[0].lower() or "jpeg"
                    extension = "jpg" if mime == "jpeg" else mime if mime in {"png", "webp", "gif"} else "jpg"
                    raw = base64.b64decode(encoded, validate=True)
                    digest = hashlib.sha256(raw).hexdigest()[:20]
                    name = f"storefront/{section_id}/{digest}.{extension}"
                    if not default_storage.exists(name):
                        default_storage.save(name, ContentFile(raw))
                    url = default_storage.url(name)
                    result[key] = request.build_absolute_uri(url) if request and url.startswith("/") else url
                except (ValueError, binascii.Error, TypeError):
                    raise ValidationError({key: "تعذر حفظ الصورة المرفوعة. تأكد من أنها صورة صحيحة."})
            else:
                result[key] = self._persist_storefront_data_urls(item, section_id)
        return result

    def create(self, validated_data):
        validated_data["config"] = self._persist_storefront_data_urls(validated_data.get("config", {}), "new")
        return super().create(validated_data)

    def update(self, instance, validated_data):
        if "config" in validated_data:
            validated_data["config"] = self._persist_storefront_data_urls(validated_data["config"], instance.pk)
        return super().update(instance, validated_data)


class SecureVendorViewSet(viewsets.ModelViewSet):
    serializer_class = VendorSerializer
    lookup_field = "slug"

    def get_queryset(self):
        user = self.request.user
        qs = VendorProfile.objects.select_related("owner")
        if user.is_authenticated and (user.is_staff or getattr(user, "role", None) == "admin"):
            pass
        elif user.is_authenticated and getattr(user, "role", None) == "vendor":
            qs = qs.filter(owner=user)
        else:
            qs = qs.filter(status="active")
        query = self.request.query_params.get("q", "").strip()
        if query:
            qs = qs.filter(Q(store_name__icontains=query) | Q(description__icontains=query) | Q(slug__icontains=query))
        return qs

    def get_permissions(self):
        if self.action in {"list", "retrieve"}:
            return [AllowAny()]
        return [IsAuthenticated(), IsVendorOrAdmin()]

    def perform_create(self, serializer):
        user = self.request.user
        if user.role != "vendor":
            raise PermissionDenied("إنشاء متجر متاح للتاجر فقط")
        if VendorProfile.objects.filter(owner=user).exists():
            raise ValidationError("لديك متجر مسجل بالفعل")
        serializer.save(owner=user, status="pending")

    def perform_update(self, serializer):
        user = self.request.user
        if not (user.is_staff or getattr(user, "role", None) == "admin") and serializer.instance.owner_id != user.id:
            raise PermissionDenied("لا يمكنك تعديل متجر آخر")
        serializer.save()

    def perform_destroy(self, instance):
        user = self.request.user
        if not (user.is_staff or getattr(user, "role", None) == "admin") and instance.owner_id != user.id:
            raise PermissionDenied("لا يمكنك حذف متجر آخر")
        instance.status = "suspended"
        instance.save(update_fields=["status", "updated_at"])


class SecureDesignThemeViewSet(viewsets.ModelViewSet):
    serializer_class = DesignThemeSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_staff or user.role == "admin":
            return DesignTheme.objects.all().select_related("vendor", "owner")
        if user.role == "vendor":
            return DesignTheme.objects.filter(Q(is_global=True, is_active=True) | Q(vendor__owner=user)).distinct()
        return DesignTheme.objects.filter(is_global=True, is_active=True)

    def _vendor(self):
        vendor = VendorProfile.objects.filter(owner=self.request.user, status="active").first()
        if not vendor:
            raise ValidationError("لا يوجد متجر نشط مرتبط بالحساب")
        return vendor

    def perform_create(self, serializer):
        user = self.request.user
        if user.is_staff or user.role == "admin":
            own_vendor = VendorProfile.objects.filter(owner=user, status="active").first()
            serializer.save(owner=user, is_global=not bool(own_vendor), vendor=own_vendor)
        elif user.role == "vendor":
            serializer.save(owner=user, vendor=self._vendor(), is_global=False)
        else:
            raise PermissionDenied("التصميمات الخاصة بالتاجر للتجار فقط")

    def perform_update(self, serializer):
        instance = serializer.instance
        user = self.request.user
        if user.is_staff or user.role == "admin":
            serializer.save()
            return
        if instance.vendor_id and instance.vendor.owner_id == user.id and not instance.is_global:
            serializer.save(vendor=instance.vendor, is_global=False)
            return
        raise PermissionDenied("لا يمكنك تعديل هذا التصميم")

    def perform_destroy(self, instance):
        user = self.request.user
        if user.is_staff or user.role == "admin" or (instance.vendor_id and instance.vendor.owner_id == user.id and not instance.is_global):
            instance.delete()
            return
        raise PermissionDenied("لا يمكنك حذف هذا التصميم")


class SecureStorefrontSectionViewSet(viewsets.ModelViewSet):
    serializer_class = MediaStorefrontSectionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        qs = StorefrontSection.objects.select_related("vendor", "owner")
        if user.is_staff or user.role == "admin":
            return qs
        if user.role == "vendor":
            # Vendors must retain access to hidden sections so they can edit, re-enable, or delete them.
            return qs.filter(vendor__owner=user)
        return qs.filter(vendor__isnull=True, is_visible=True)

    def perform_create(self, serializer):
        user = self.request.user
        if user.is_staff or user.role == "admin":
            requested_id = self.request.data.get("vendor_id")
            vendor = VendorProfile.objects.filter(id=requested_id).first() if requested_id else VendorProfile.objects.filter(owner=user, status="active").first()
            if requested_id and not vendor:
                raise ValidationError({"vendor_id": "المتجر المحدد غير موجود."})
            serializer.save(owner=user, vendor=vendor)
            return
        if user.role != "vendor":
            raise PermissionDenied("إنشاء أقسام المتجر للتاجر فقط")
        vendor = VendorProfile.objects.filter(owner=user, status="active").first()
        if not vendor:
            raise ValidationError("لا يوجد متجر نشط مرتبط بالحساب")
        serializer.save(owner=user, vendor=vendor)

    def perform_update(self, serializer):
        user = self.request.user
        instance = serializer.instance
        if user.is_staff or user.role == "admin":
            serializer.save()
            return
        if user.role == "vendor" and instance.vendor_id and instance.vendor.owner_id == user.id:
            serializer.save(vendor=instance.vendor, owner=instance.owner)
            return
        raise PermissionDenied("لا يمكنك تعديل قسم متجر آخر")

    def perform_destroy(self, instance):
        user = self.request.user
        if user.is_staff or user.role == "admin" or (user.role == "vendor" and instance.vendor_id and instance.vendor.owner_id == user.id):
            instance.delete()
            return
        raise PermissionDenied("لا يمكنك حذف قسم متجر آخر")
