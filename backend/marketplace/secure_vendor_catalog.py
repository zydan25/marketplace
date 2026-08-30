from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import SAFE_METHODS
from django.db.models import Q

from .models import DesignTheme, Product, StorefrontSection, VendorProfile
from .secure_catalog import SecureDesignThemeViewSet, SecureProductViewSet, SecureStorefrontSectionViewSet
from .serializers import ProductSerializer


class VendorProductSerializer(ProductSerializer):
    """Keep vendor product edits backward-compatible when the client identifies variants by SKU."""

    def to_internal_value(self, data):
        if self.instance is not None and isinstance(data, dict) and "variants" in data and isinstance(data.get("variants"), list):
            existing_by_sku = {str(variant.sku).strip(): variant.id for variant in self.instance.variants.all() if variant.sku}
            normalized_rows = []
            for raw_row in data["variants"]:
                row = dict(raw_row) if isinstance(raw_row, dict) else raw_row
                if isinstance(row, dict) and not row.get("id"):
                    existing_id = existing_by_sku.get(str(row.get("sku", "")).strip())
                    if existing_id:
                        row["id"] = existing_id
                normalized_rows.append(row)
            payload = dict(data)
            payload["variants"] = normalized_rows
            data = payload
        return super().to_internal_value(data)


class VendorProductViewSet(SecureProductViewSet):
    serializer_class = VendorProductSerializer

    def get_queryset(self):
        user = self.request.user
        qs = Product.objects.select_related("vendor", "vendor__owner").prefetch_related("categories", "image_items", "variants")
        if getattr(user, "is_staff", False) or getattr(user, "role", None) == "admin":
            return qs
        public_qs = qs.filter(is_published=True, vendor__status="active")
        if getattr(user, "role", None) == "vendor":
            own_qs = qs.filter(vendor__owner=user)
            if self.action in {"retrieve"}:
                return qs.filter(Q(vendor__owner=user) | Q(is_published=True, vendor__status="active")).distinct()
            if self.request.query_params.get("mine") in {"1", "true", "yes"}:
                return own_qs
            return public_qs
        return public_qs

    def _vendor_for_write(self):
        user = self.request.user
        own_vendor = VendorProfile.objects.filter(owner=user).first()
        requested_id = self.request.data.get("vendor_id")
        if user.is_staff or getattr(user, "role", None) == "admin":
            if requested_id:
                vendor = VendorProfile.objects.filter(id=requested_id).first()
                if not vendor:
                    raise ValidationError({"vendor_id": "المتجر المحدد غير موجود."})
                if vendor.status != "active":
                    raise ValidationError({"vendor_id": "المتجر المحدد غير نشط."})
                return vendor
            if own_vendor and own_vendor.status == "active":
                return own_vendor
            active = VendorProfile.objects.filter(status="active").order_by("id")
            if active.count() == 1:
                return active.first()
            raise ValidationError({"vendor_id": "حدد المتجر الذي سيُضاف إليه المنتج."})
        if getattr(user, "role", None) != "vendor":
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
