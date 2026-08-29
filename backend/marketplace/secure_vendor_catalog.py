from rest_framework.exceptions import PermissionDenied, ValidationError

from .models import DesignTheme, StorefrontSection, VendorProfile
from .secure_catalog import SecureDesignThemeViewSet, SecureStorefrontSectionViewSet

# Product ownership and variant-aware editing are now canonical in catalog.api.
from catalog.api import ProductViewSet as VendorProductViewSet
from catalog.api import VendorProductSerializer


class VendorDesignThemeViewSet(SecureDesignThemeViewSet):
    def get_queryset(self):
        user = self.request.user
        if getattr(user, "is_staff", False) or getattr(user, "role", None) == "admin":
            return DesignTheme.objects.all().select_related("vendor", "owner")
        if getattr(user, "role", None) == "vendor":
            return DesignTheme.objects.filter(vendor__owner=user).select_related("vendor", "owner")
        return DesignTheme.objects.filter(is_global=True, is_active=True)


class VendorStorefrontSectionViewSet(SecureStorefrontSectionViewSet):
    def get_queryset(self):
        user = self.request.user
        qs = StorefrontSection.objects.select_related("vendor", "owner")
        if getattr(user, "is_staff", False) or getattr(user, "role", None) == "admin":
            return qs
        if getattr(user, "role", None) == "vendor":
            return qs.filter(vendor__owner=user)
        return qs.filter(vendor__isnull=True, is_visible=True)

    def perform_create(self, serializer):
        user = self.request.user
        if user.is_staff or getattr(user, "role", None) == "admin":
            requested_id = self.request.data.get("vendor_id")
            vendor = VendorProfile.objects.filter(id=requested_id).first() if requested_id else VendorProfile.objects.filter(owner=user, status="active").first()
            if requested_id and not vendor:
                raise ValidationError({"vendor_id": "المتجر المحدد غير موجود."})
            serializer.save(owner=user, vendor=vendor)
            return
        if getattr(user, "role", None) != "vendor":
            raise PermissionDenied("إنشاء أقسام المتجر متاح للتاجر فقط")
        vendor = VendorProfile.objects.filter(owner=user, status="active").first()
        if not vendor:
            raise ValidationError("لا يوجد متجر نشط مرتبط بحساب التاجر")
        serializer.save(owner=user, vendor=vendor)
