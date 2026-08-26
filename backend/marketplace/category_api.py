from django.db import IntegrityError
from django.utils.text import slugify
from rest_framework import serializers, viewsets
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.exceptions import PermissionDenied, ValidationError

from .models import Category

class CategoryWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name", "parent", "is_active", "sort_order", "slug"]
        read_only_fields = ["id", "slug"]
    def _slug(self, name, instance=None):
        base = slugify(name, allow_unicode=True) or "category"
        candidate = base; n = 2
        while Category.objects.filter(slug=candidate).exclude(pk=getattr(instance, "pk", None)).exists():
            candidate = f"{base}-{n}"; n += 1
        return candidate
    def create(self, validated_data):
        try: return Category.objects.create(slug=self._slug(validated_data["name"]), **validated_data)
        except IntegrityError: raise ValidationError({"name": "يوجد صنف بهذا الاسم أو بمعرّف مماثل."})
    def update(self, instance, validated_data):
        name = validated_data.get("name")
        if name and name != instance.name: validated_data["slug"] = self._slug(name, instance)
        return super().update(instance, validated_data)

class CategoryViewSet(viewsets.ModelViewSet):
    serializer_class = CategoryWriteSerializer
    def get_queryset(self):
        qs = Category.objects.select_related("parent").prefetch_related("children")
        return qs.filter(is_active=True) if self.action in {"list", "retrieve"} else qs
    def get_permissions(self):
        return [AllowAny()] if self.action in {"list", "retrieve"} else [IsAuthenticated()]
    def perform_create(self, serializer):
        if not (self.request.user.is_staff or self.request.user.role == "admin"): raise PermissionDenied("إضافة الأصناف متاحة للإدارة فقط")
        serializer.save()
    def perform_update(self, serializer):
        if not (self.request.user.is_staff or self.request.user.role == "admin"): raise PermissionDenied("تعديل الأصناف متاح للإدارة فقط")
        serializer.save()
    def perform_destroy(self, instance):
        if not (self.request.user.is_staff or self.request.user.role == "admin"): raise PermissionDenied("حذف الأصناف متاح للإدارة فقط")
        instance.is_active = False; instance.save(update_fields=["is_active", "updated_at"])
