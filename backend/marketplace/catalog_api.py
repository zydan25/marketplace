from rest_framework import serializers, viewsets
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import AllowAny, IsAuthenticated

from .models_extra import CurrencyRate

# Backward-compatible exports. Canonical catalog endpoints now live in the catalog app.
from catalog.api import CatalogOptionViewSet, CatalogTreeView, CategoryViewSet, PriceGroupViewSet, ProductImageViewSet, ProductViewSet, VariantViewSet


class CurrencyRateSerializer(serializers.ModelSerializer):
    class Meta:
        model = CurrencyRate
        fields = ["id", "base_currency", "target_currency", "rate", "is_active", "updated_at"]
        read_only_fields = ["id", "updated_at"]


class CurrencyRateViewSet(viewsets.ModelViewSet):
    serializer_class = CurrencyRateSerializer

    def get_queryset(self):
        qs = CurrencyRate.objects.all().order_by("base_currency", "target_currency")
        user = self.request.user
        if not (user.is_authenticated and (user.is_staff or getattr(user, "role", None) == "admin")):
            qs = qs.filter(is_active=True)
        return qs

    def get_permissions(self):
        return [AllowAny()] if self.action in {"list", "retrieve"} else [IsAuthenticated()]

    def _admin(self):
        user = self.request.user
        return bool(user.is_authenticated and (user.is_staff or getattr(user, "role", None) == "admin"))

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