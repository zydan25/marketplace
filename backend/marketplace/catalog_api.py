from django.utils.text import slugify
from rest_framework import serializers, viewsets
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.exceptions import PermissionDenied, ValidationError

from accounts.preferences_api import PreferencesView
from .models import Category
from .models_extra import CatalogOption, CurrencyRate


class CatalogOptionSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True)

    class Meta:
        model = CatalogOption
        fields = ["id", "group", "name", "slug", "category", "category_name", "sort_order", "is_active"]
        read_only_fields = ["id", "slug"]


class CatalogOptionViewSet(viewsets.ModelViewSet):
    serializer_class = CatalogOptionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = CatalogOption.objects.filter(is_active=True).select_related("category")
        group = self.request.query_params.get("group")
        category = self.request.query_params.get("category")
        if group:
            qs = qs.filter(group=group)
        if category:
            qs = qs.filter(category_id=category)
        return qs.order_by("group", "sort_order", "name")

    def get_permissions(self):
        if self.action in {"list", "retrieve"}:
            return [AllowAny()]
        return [IsAuthenticated()]

    def perform_create(self, serializer):
        user = self.request.user
        if user.role not in {"vendor", "admin"} and not user.is_staff:
            raise PermissionDenied("إضافة الخيارات متاحة للتاجر أو الإدارة فقط")
        name = str(self.request.data.get("name", "")).strip()
        group = str(self.request.data.get("group", "")).strip().lower()
        if not name or not group:
            raise ValidationError({"name": "اسم الخيار مطلوب", "group": "نوع الخيار مطلوب"})
        raw_slug = slugify(name, allow_unicode=True) or f"option-{CatalogOption.objects.count() + 1}"
        slug = raw_slug
        counter = 2
        category_id = self.request.data.get("category") or None
        while CatalogOption.objects.filter(group=group, slug=slug, category_id=category_id).exists():
            slug = f"{raw_slug}-{counter}"
            counter += 1
        serializer.save(slug=slug, is_active=True)

    def perform_update(self, serializer):
        if not (self.request.user.is_staff or self.request.user.role == "admin"):
            raise PermissionDenied("تعديل الخيارات العامة متاح للإدارة فقط")
        serializer.save()

    def perform_destroy(self, instance):
        if not (self.request.user.is_staff or self.request.user.role == "admin"):
            raise PermissionDenied("حذف الخيارات العامة متاح للإدارة فقط")
        instance.is_active = False
        instance.save(update_fields=["is_active", "updated_at"])


class CatalogTreeView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        categories = list(Category.objects.filter(is_active=True).select_related("parent").order_by("sort_order", "name"))
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
            grouped.setdefault(option.group, []).append({
                "id": option.id,
                "name": option.name,
                "slug": option.slug,
                "category": option.category_id,
                "category_name": option.category.name if option.category_id else None,
            })
        return Response({"categories": [node(x) for x in by_parent.get(None, [])], "options": grouped, "currencies": ["YER", "SAR", "USD"]})


class CurrencyRateSerializer(serializers.ModelSerializer):
    class Meta:
        model = CurrencyRate
        fields = ["id", "base_currency", "target_currency", "rate", "is_active", "updated_at"]
        read_only_fields = ["id", "updated_at"]


class CurrencyRateViewSet(viewsets.ModelViewSet):
    serializer_class = CurrencyRateSerializer

    def get_queryset(self):
        qs = CurrencyRate.objects.all().order_by("base_currency", "target_currency")
        if not (self.request.user.is_authenticated and (self.request.user.is_staff or self.request.user.role == "admin")):
            qs = qs.filter(is_active=True)
        return qs

    def get_permissions(self):
        return [AllowAny()] if self.action in {"list", "retrieve"} else [IsAuthenticated()]

    def _admin(self):
        return self.request.user.is_staff or self.request.user.role == "admin"

    def perform_create(self, serializer):
        if not self._admin():
            raise PermissionDenied("للمدير فقط")
        serializer.save(updated_by=self.request.user)

    def perform_update(self, serializer):
        if not self._admin():
            raise PermissionDenied("للمدير فقط")
        serializer.save(updated_by=self.request.user)

    def perform_destroy(self, instance):
        if not self._admin():
            raise PermissionDenied("للمدير فقط")
        instance.is_active = False
        instance.save(update_fields=["is_active", "updated_at"])
