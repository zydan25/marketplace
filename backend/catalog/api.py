from django.db.models import Count, Q
from django.utils.text import slugify
from rest_framework import serializers, viewsets
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from marketplace.models import VendorProfile

from .models import Category, CatalogOption, PriceGroup, Product, ProductImage, ProductVariant
from .permissions import IsCatalogAdmin, IsCatalogManager
from .serializers import (
    CategorySerializer,
    CatalogOptionSerializer,
    PriceGroupSerializer,
    ProductImageSerializer,
    ProductSerializer,
    ProductVariantSerializer,
)


class CategoryViewSet(viewsets.ModelViewSet):
    serializer_class = CategorySerializer

    def get_queryset(self):
        qs = Category.objects.annotate(
            children_count=Count("children", distinct=True),
            products_count=Count("products", distinct=True),
        ).select_related("parent")
        if self.action in {"list", "retrieve"}:
            qs = qs.filter(is_active=True)
        return qs.order_by("sort_order", "name", "id")

    def get_permissions(self):
        if self.action in {"list", "retrieve"}:
            return [AllowAny()]
        return [IsAuthenticated(), IsCatalogAdmin()]


class VendorProductSerializer(ProductSerializer):
    """Backward-compatible nested variant editing when the client sends SKU only."""

    def to_internal_value(self, data):
        if self.instance is not None and isinstance(data, dict) and isinstance(data.get("variants"), list):
            existing_by_sku = {
                str(variant.sku).strip(): variant.id
                for variant in self.instance.variants.all()
                if variant.sku
            }
            normalized_rows = []
            for raw_row in data["variants"]:
                row = dict(raw_row) if isinstance(raw_row, dict) else raw_row
                if isinstance(row, dict) and not row.get("id"):
                    sku = str(row.get("sku", "")).strip()
                    if sku in existing_by_sku:
                        row["id"] = existing_by_sku[sku]
                normalized_rows.append(row)
            payload = dict(data)
            payload["variants"] = normalized_rows
            data = payload
        return super().to_internal_value(data)


class ProductViewSet(viewsets.ModelViewSet):
    serializer_class = ProductSerializer

    def get_queryset(self):
        user = self.request.user
        qs = Product.objects.select_related("vendor", "vendor__owner").prefetch_related(
            "categories", "image_items", "variants"
        )
        if user.is_authenticated and (user.is_staff or getattr(user, "role", None) == "admin"):
            return qs
        if user.is_authenticated and getattr(user, "role", None) == "vendor":
            return qs.filter(vendor__owner=user)
        qs = qs.filter(is_published=True, vendor__status="active")
        query = self.request.query_params.get("q", "").strip()
        if query:
            qs = qs.filter(Q(name__icontains=query) | Q(sku__icontains=query) | Q(description__icontains=query) | Q(brand__icontains=query))
        vendor = self.request.query_params.get("vendor", "").strip()
        category = self.request.query_params.get("category", "").strip()
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
        return [IsAuthenticated(), IsCatalogManager()]

    def _vendor_for_write(self):
        user = self.request.user
        requested_id = self.request.data.get("vendor_id")
        own_vendor = VendorProfile.objects.filter(owner=user).first()

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

    def perform_create(self, serializer):
        vendor = self._vendor_for_write()
        serializer.save(vendor=vendor)

    def _owns(self, instance):
        user = self.request.user
        return bool(user.is_staff or getattr(user, "role", None) == "admin" or instance.vendor.owner_id == user.id)

    def perform_update(self, serializer):
        if not self._owns(serializer.instance):
            raise PermissionDenied("لا يمكنك تعديل منتج متجر آخر")
        serializer.save(vendor=serializer.instance.vendor)

    def perform_destroy(self, instance):
        if not self._owns(instance):
            raise PermissionDenied("لا يمكنك حذف منتج متجر آخر")
        instance.is_published = False
        instance.save(update_fields=["is_published", "updated_at"])


class VariantViewSet(viewsets.ModelViewSet):
    serializer_class = ProductVariantSerializer

    def get_queryset(self):
        qs = ProductVariant.objects.select_related("product", "product__vendor", "product__vendor__owner")
        user = self.request.user
        if user.is_authenticated and (user.is_staff or getattr(user, "role", None) == "admin"):
            return qs
        if user.is_authenticated and getattr(user, "role", None) == "vendor":
            return qs.filter(product__vendor__owner=user)
        return qs.filter(is_active=True, product__is_published=True, product__vendor__status="active")

    def get_permissions(self):
        if self.action in {"list", "retrieve"}:
            return [AllowAny()]
        return [IsAuthenticated(), IsCatalogManager()]

    def _owns(self, instance):
        user = self.request.user
        return bool(user.is_staff or getattr(user, "role", None) == "admin" or instance.product.vendor.owner_id == user.id)

    def perform_create(self, serializer):
        user = self.request.user
        product_id = self.request.data.get("product") or self.request.data.get("product_id")
        if not product_id:
            raise ValidationError({"product": "المنتج مطلوب."})
        product = Product.objects.select_related("vendor").filter(pk=product_id).first()
        if not product:
            raise ValidationError({"product": "المنتج غير موجود."})
        if not (user.is_staff or getattr(user, "role", None) == "admin") and product.vendor.owner_id != user.id:
            raise PermissionDenied("لا يمكنك إضافة صنف إلى منتج متجر آخر")
        serializer.save(product=product)

    def perform_update(self, serializer):
        if not self._owns(serializer.instance):
            raise PermissionDenied("لا يمكنك تعديل صنف متجر آخر")
        serializer.save(product=serializer.instance.product)

    def perform_destroy(self, instance):
        if not self._owns(instance):
            raise PermissionDenied("لا يمكنك حذف صنف متجر آخر")
        instance.is_active = False
        instance.save(update_fields=["is_active", "updated_at"])


class ProductImageViewSet(viewsets.ModelViewSet):
    serializer_class = ProductImageSerializer
    permission_classes = [IsAuthenticated, IsCatalogManager]

    def get_queryset(self):
        qs = ProductImage.objects.select_related("product", "product__vendor", "product__vendor__owner")
        user = self.request.user
        if user.is_staff or getattr(user, "role", None) == "admin":
            return qs
        return qs.filter(product__vendor__owner=user)

    def perform_create(self, serializer):
        product_id = self.request.data.get("product")
        product = Product.objects.select_related("vendor").filter(pk=product_id).first()
        if not product:
            raise ValidationError({"product": "المنتج غير موجود."})
        user = self.request.user
        if not (user.is_staff or getattr(user, "role", None) == "admin") and product.vendor.owner_id != user.id:
            raise PermissionDenied("لا يمكنك إضافة صورة لمنتج متجر آخر")
        serializer.save(product=product)

    def perform_update(self, serializer):
        instance = serializer.instance
        user = self.request.user
        if not (user.is_staff or getattr(user, "role", None) == "admin") and instance.product.vendor.owner_id != user.id:
            raise PermissionDenied("لا يمكنك تعديل صورة متجر آخر")
        serializer.save(product=instance.product)

    def perform_destroy(self, instance):
        user = self.request.user
        if not (user.is_staff or getattr(user, "role", None) == "admin") and instance.product.vendor.owner_id != user.id:
            raise PermissionDenied("لا يمكنك حذف صورة متجر آخر")
        was_primary = instance.is_primary
        product = instance.product
        instance.delete()
        if was_primary:
            next_image = product.image_items.order_by("sort_order", "id").first()
            if next_image:
                ProductImage.objects.filter(product=product).update(is_primary=False)
                next_image.is_primary = True
                next_image.save(update_fields=["is_primary", "updated_at"])


class CatalogOptionViewSet(viewsets.ModelViewSet):
    serializer_class = CatalogOptionSerializer

    def get_queryset(self):
        qs = CatalogOption.objects.filter(is_active=True).select_related("category")
        if self.request.user.is_authenticated and (self.request.user.is_staff or getattr(self.request.user, "role", None) == "admin"):
            qs = CatalogOption.objects.all().select_related("category")
        group = self.request.query_params.get("group", "").strip()
        category = self.request.query_params.get("category", "").strip()
        if group:
            qs = qs.filter(group=group)
        if category:
            qs = qs.filter(category_id=category)
        return qs.order_by("group", "sort_order", "name", "id")

    def get_permissions(self):
        if self.action in {"list", "retrieve"}:
            return [AllowAny()]
        return [IsAuthenticated(), IsCatalogManager()]

    def perform_create(self, serializer):
        user = self.request.user
        if not (user.is_staff or getattr(user, "role", None) in {"admin", "vendor"}):
            raise PermissionDenied("إضافة الخيارات متاحة للتاجر أو الإدارة فقط")
        name = str(self.request.data.get("name", "")).strip()
        group = str(self.request.data.get("group", "")).strip().lower()
        category_id = self.request.data.get("category") or None
        raw_slug = slugify(name, allow_unicode=True) or f"option-{CatalogOption.objects.count() + 1}"
        slug = raw_slug
        counter = 2
        while CatalogOption.objects.filter(group=group, slug=slug, category_id=category_id).exists():
            slug = f"{raw_slug}-{counter}"
            counter += 1
        serializer.save(group=group, slug=slug, is_active=True)

    def perform_update(self, serializer):
        if not (self.request.user.is_staff or getattr(self.request.user, "role", None) == "admin"):
            raise PermissionDenied("تعديل الخيارات العامة متاح للإدارة فقط")
        serializer.save()

    def perform_destroy(self, instance):
        if not (self.request.user.is_staff or getattr(self.request.user, "role", None) == "admin"):
            raise PermissionDenied("حذف الخيارات العامة متاح للإدارة فقط")
        instance.is_active = False
        instance.save(update_fields=["is_active", "updated_at"])


class PriceGroupViewSet(viewsets.ModelViewSet):
    serializer_class = PriceGroupSerializer

    def get_queryset(self):
        qs = PriceGroup.objects.all().order_by("name", "id")
        if not (self.request.user.is_authenticated and (self.request.user.is_staff or getattr(self.request.user, "role", None) == "admin")):
            qs = qs.filter(is_active=True)
        return qs

    def get_permissions(self):
        if self.action in {"list", "retrieve"}:
            return [AllowAny()]
        return [IsAuthenticated(), IsCatalogAdmin()]

    def perform_create(self, serializer):
        serializer.save()

    def perform_destroy(self, instance):
        instance.is_active = False
        instance.save(update_fields=["is_active", "updated_at"])


class CatalogTreeView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        categories = list(Category.objects.filter(is_active=True).select_related("parent").order_by("sort_order", "name", "id"))
        by_parent = {}
        for category in categories:
            by_parent.setdefault(category.parent_id, []).append(category)

        def node(category):
            return {
                "id": category.id,
                "name": category.name,
                "slug": category.slug,
                "image": request.build_absolute_uri(category.image.url) if category.image else None,
                "children": [node(child) for child in by_parent.get(category.id, [])],
            }

        options = CatalogOption.objects.filter(is_active=True).select_related("category").order_by("group", "sort_order", "name")
        grouped = {}
        for option in options:
            grouped.setdefault(option.group, []).append(
                {
                    "id": option.id,
                    "name": option.name,
                    "slug": option.slug,
                    "category": option.category_id,
                    "category_name": option.category.name if option.category_id else None,
                }
            )
        return Response(
            {
                "categories": [node(x) for x in by_parent.get(None, [])],
                "options": grouped,
                "currencies": ["YER", "SAR", "USD"],
            }
        )