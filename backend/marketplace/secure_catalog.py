from django.db.models import Q
from rest_framework import viewsets
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated

from .api_policy import IsAdminOrReadOnly, IsVendorOrAdmin
from .models import Category, DesignTheme, Product, StorefrontSection, VendorProfile
from .serializers import CategorySerializer, DesignThemeSerializer, ProductSerializer, StorefrontSectionSerializer, VendorSerializer


class SecureCategoryViewSet(viewsets.ModelViewSet):
    serializer_class = CategorySerializer

    def get_queryset(self):
        if self.action in {"list", "retrieve"}:
            return Category.objects.filter(is_active=True).select_related("parent")
        return Category.objects.all().select_related("parent")

    def get_permissions(self):
        if self.action in {"list", "retrieve"}:
            return [AllowAny()]
        return [IsAuthenticated(), IsAdminOrReadOnly()]


class SecureVendorViewSet(viewsets.ModelViewSet):
    serializer_class = VendorSerializer
    lookup_field = "slug"

    def get_queryset(self):
        user = self.request.user
        qs = VendorProfile.objects.select_related("owner")
        if user.is_authenticated and (user.is_staff or user.role == "admin"):
            pass
        elif user.is_authenticated and user.role == "vendor":
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
        if not (user.is_staff or user.role == "admin") and serializer.instance.owner_id != user.id:
            raise PermissionDenied("لا يمكنك تعديل متجر آخر")
        serializer.save()

    def perform_destroy(self, instance):
        user = self.request.user
        if not (user.is_staff or user.role == "admin") and instance.owner_id != user.id:
            raise PermissionDenied("لا يمكنك حذف متجر آخر")
        instance.status = "suspended"
        instance.save(update_fields=["status", "updated_at"])


class SecureProductViewSet(viewsets.ModelViewSet):
    serializer_class = ProductSerializer

    def get_queryset(self):
        user = self.request.user
        qs = Product.objects.select_related("vendor", "vendor__owner").prefetch_related("categories", "image_items", "variants")
        if user.is_authenticated and (user.is_staff or user.role == "admin"):
            pass
        elif user.is_authenticated and user.role == "vendor":
            qs = qs.filter(vendor__owner=user)
        else:
            qs = qs.filter(is_published=True, vendor__status="active")
        query = self.request.query_params.get("q", "").strip()
        vendor = self.request.query_params.get("vendor", "").strip()
        category = self.request.query_params.get("category", "").strip()
        if query:
            qs = qs.filter(Q(name__icontains=query) | Q(sku__icontains=query) | Q(description__icontains=query) | Q(brand__icontains=query))
        if vendor:
            qs = qs.filter(vendor__slug=vendor)
        if category:
            qs = qs.filter(categories__slug=category)
        if self.request.query_params.get("trending") == "1":
            qs = qs.filter(is_trending=True)
        return qs.distinct()

    def get_permissions(self):
        if self.action in {"list", "retrieve"}:
            return [AllowAny()]
        return [IsAuthenticated(), IsVendorOrAdmin()]

    def _vendor_for_write(self):
        user = self.request.user
        if user.is_staff or user.role == "admin":
            vendor_id = self.request.data.get("vendor_id")
            return VendorProfile.objects.filter(id=vendor_id, status="active").first() if vendor_id else None
        return VendorProfile.objects.filter(owner=user, status="active").first()

    def perform_create(self, serializer):
        vendor = self._vendor_for_write()
        if not vendor:
            raise ValidationError({"vendor_id": "لا يوجد متجر نشط مرتبط بالحساب"})
        serializer.save(vendor=vendor)

    def _owns(self, instance):
        user = self.request.user
        return bool(user.is_staff or user.role == "admin" or instance.vendor.owner_id == user.id)

    def perform_update(self, serializer):
        if not self._owns(serializer.instance):
            raise PermissionDenied("لا يمكنك تعديل منتج متجر آخر")
        serializer.save(vendor=serializer.instance.vendor)

    def perform_destroy(self, instance):
        if not self._owns(instance):
            raise PermissionDenied("لا يمكنك حذف منتج متجر آخر")
        instance.is_published = False
        instance.save(update_fields=["is_published", "updated_at"])


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
            serializer.save(owner=user, is_global=True, vendor=None)
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
    serializer_class = StorefrontSectionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        qs = StorefrontSection.objects.select_related("vendor", "owner")
        if user.is_staff or user.role == "admin":
            return qs
        if user.role == "vendor":
            return qs.filter(Q(vendor__owner=user) | Q(vendor__isnull=True), is_visible=True)
        return qs.filter(vendor__isnull=True, is_visible=True)

    def perform_create(self, serializer):
        user = self.request.user
        if user.is_staff or user.role == "admin":
            vendor_id = self.request.data.get("vendor_id")
            vendor = VendorProfile.objects.filter(id=vendor_id).first() if vendor_id else None
            serializer.save(owner=user, vendor=vendor)
            return
        if user.role != "vendor":
            raise PermissionDenied("إنشاء أقسام المتجر للتاجر فقط")
        vendor = VendorProfile.objects.filter(owner=user, status="active").first()
        if not vendor:
            raise ValidationError("لا يوجد متجر نشط مرتبط بالحساب")
        serializer.save(owner=user, vendor=vendor)

    def _owns(self, instance):
        user = self.request.user
        return bool(user.is_staff or user.role == "admin" or (instance.vendor_id and instance.vendor.owner_id == user.id))

    def perform_update(self, serializer):
        if not self._owns(serializer.instance):
            raise PermissionDenied("لا يمكنك تعديل قسم متجر آخر")
        serializer.save(vendor=serializer.instance.vendor)

    def perform_destroy(self, instance):
        if not self._owns(instance):
            raise PermissionDenied("لا يمكنك حذف قسم متجر آخر")
        instance.delete()
