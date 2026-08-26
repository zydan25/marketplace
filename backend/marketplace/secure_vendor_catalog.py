from rest_framework.exceptions import PermissionDenied, ValidationError

from .models import DesignTheme, Product, StorefrontSection, VendorProfile
from .secure_catalog import (
    SecureDesignThemeViewSet,
    SecureProductViewSet,
    SecureStorefrontSectionViewSet,
)
from .serializers import ProductSerializer


class VendorProductSerializer(ProductSerializer):
    """Accept legacy/edit forms that identify variants by SKU instead of id."""

    def update(self, instance, validated_data):
        variants = validated_data.get("variants")
        if variants is not None:
            existing_by_sku = {
                str(variant.sku).strip(): variant.id
                for variant in instance.variants.all()
                if variant.sku
            }
            normalized = []
            for row in variants:
                item = dict(row)
                if not item.get("id"):
                    sku = str(item.get("sku", "")).strip()
                    existing_id = existing_by_sku.get(sku)
                    if existing_id:
                        item["id"] = existing_id
                normalized.append(item)
            validated_data["variants"] = normalized
        return super().update(instance, validated_data)


class VendorProductViewSet(SecureProductViewSet):
    serializer_class = VendorProductSerializer

    def get_queryset(self):
        user = self.request.user
        qs = Product.objects.select_related("vendor", "vendor__owner").prefetch_related(
            "categories", "image_items", "variants"
        )
        if user.is_staff or user.role == "admin":
            return qs
        if user.role != "vendor":
            return qs.filter(is_published=True, vendor__status="active")
        return qs.filter(vendor__owner=user)

    def _vendor_for_write(self):
        user = self.request.user
        own_vendor = VendorProfile.objects.filter(owner=user).first()
        requested_id = self.request.data.get("vendor_id")

        if user.is_staff or user.role == "admin":
            if requested_id:
                vendor = VendorProfile.objects.filter(id=requested_id).first()
                if not vendor:
                    raise ValidationError({"vendor_id": "المتجر المحدد غير موجود."})
                if vendor.status != "active":
                    raise ValidationError({"vendor_id": "المتجر المحدد غير نشط."})
                return vendor
            active = VendorProfile.objects.filter(status="active").order_by("id")
            if active.count() == 1:
                return active.first()
            raise ValidationError({"vendor_id": "حدد المتجر الذي سيُضاف إليه المنتج."})

        if user.role != "vendor":
            raise PermissionDenied("إدارة المنتجات متاحة للتاجر فقط")
        if not own_vendor:
            raise ValidationError({"vendor_id": "لا يوجد متجر مرتبط بحساب التاجر."})
        if own_vendor.status != "active":
            raise ValidationError({"vendor_id": "متجرك غير نشط حاليًا. لا يمكن إضافة منتجات قبل اعتماد المتجر."})
        if requested_id and str(requested_id) != str(own_vendor.id):
            raise PermissionDenied("لا يمكنك إضافة منتج إلى متجر آخر")
        return own_vendor


class VendorDesignThemeViewSet(SecureDesignThemeViewSet):
    def get_queryset(self):
        user = self.request.user
        if user.is_staff or user.role == "admin":
            return DesignTheme.objects.all().select_related("vendor", "owner")
        if user.role == "vendor":
            return DesignTheme.objects.filter(vendor__owner=user).select_related("vendor", "owner")
        return DesignTheme.objects.filter(is_global=True, is_active=True)


class VendorStorefrontSectionViewSet(SecureStorefrontSectionViewSet):
    def get_queryset(self):
        user = self.request.user
        qs = StorefrontSection.objects.select_related("vendor", "owner")
        if user.is_staff or user.role == "admin":
            return qs
        if user.role == "vendor":
            # Include the vendor's own drafts/hidden sections too.
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
            raise PermissionDenied("إنشاء أقسام المتجر متاح للتاجر فقط")
        vendor = VendorProfile.objects.filter(owner=user, status="active").first()
        if not vendor:
            raise ValidationError("لا يوجد متجر نشط مرتبط بحساب التاجر")
        serializer.save(owner=user, vendor=vendor)
