from rest_framework import serializers, viewsets
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated

from .models import City, VendorProfile
from .models_extra import VendorCityShipping


class VendorCityShippingSerializer(serializers.ModelSerializer):
    city_name = serializers.CharField(source="city.name", read_only=True)
    class Meta:
        model = VendorCityShipping
        fields = ["id", "vendor", "city", "city_name", "fee", "is_active", "created_at", "updated_at"]
        read_only_fields = ["id", "vendor", "city_name", "created_at", "updated_at"]


class VendorCityShippingViewSet(viewsets.ModelViewSet):
    serializer_class = VendorCityShippingSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        qs = VendorCityShipping.objects.select_related("vendor", "city").order_by("city__name")
        if user.is_staff or user.role == "admin":
            vendor_id = self.request.query_params.get("vendor")
            return qs.filter(vendor_id=vendor_id) if vendor_id else qs
        return qs.filter(vendor__owner=user)

    def _vendor(self):
        vendor = VendorProfile.objects.filter(owner=self.request.user).first()
        if not vendor:
            raise ValidationError({"vendor": "لا يوجد متجر مرتبط بالحساب."})
        if vendor.status != "active":
            raise PermissionDenied("يجب اعتماد المتجر قبل إعداد رسوم التوصيل.")
        return vendor

    def perform_create(self, serializer):
        if self.request.user.role != "vendor":
            raise PermissionDenied("إعداد رسوم التوصيل للتاجر فقط")
        vendor = self._vendor()
        city_id = self.request.data.get("city")
        if not City.objects.filter(pk=city_id, is_active=True).exists():
            raise ValidationError({"city": "المحافظة غير صالحة."})
        serializer.save(vendor=vendor)

    def perform_update(self, serializer):
        instance = serializer.instance
        if self.request.user.role == "vendor" and instance.vendor.owner_id != self.request.user.id:
            raise PermissionDenied("لا تملك هذه الرسوم")
        if not (self.request.user.is_staff or self.request.user.role == "admin") and instance.vendor.owner_id != self.request.user.id:
            raise PermissionDenied("لا تملك هذه الرسوم")
        serializer.save()
