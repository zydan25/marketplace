from rest_framework import serializers, viewsets
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.exceptions import PermissionDenied
from .models import City, VendorProfile
from .models_extra import VendorCityShipping, MarketplaceOffice

class VendorCityShippingSerializer(serializers.ModelSerializer):
    city_name = serializers.CharField(source="city.name", read_only=True)
    class Meta:
        model=VendorCityShipping
        fields=["id","vendor","city","city_name","fee","is_active","created_at","updated_at"]
        read_only_fields=["id","vendor","created_at","updated_at"]
class VendorCityShippingViewSet(viewsets.ModelViewSet):
    serializer_class=VendorCityShippingSerializer
    permission_classes=[IsAuthenticated]
    def get_queryset(self):
        if self.request.user.is_staff or self.request.user.role=="admin": return VendorCityShipping.objects.select_related("vendor","city")
        return VendorCityShipping.objects.filter(vendor__owner=self.request.user).select_related("city","vendor")
    def perform_create(self,serializer):
        if self.request.user.role!="vendor": raise PermissionDenied("للتاجر فقط")
        vendor=VendorProfile.objects.filter(owner=self.request.user,status="active").first()
        if not vendor: raise PermissionDenied("لا يوجد متجر نشط")
        serializer.save(vendor=vendor)
    def perform_update(self,serializer):
        if self.request.user.role=="vendor" and serializer.instance.vendor.owner_id!=self.request.user.id: raise PermissionDenied("لا تملك هذه الرسوم")
        serializer.save()

class MarketplaceOfficeSerializer(serializers.ModelSerializer):
    city_name=serializers.CharField(source="city.name",read_only=True)
    class Meta:
        model=MarketplaceOffice
        fields="__all__"
        read_only_fields=["id","created_at","updated_at"]
class MarketplaceOfficeViewSet(viewsets.ModelViewSet):
    serializer_class=MarketplaceOfficeSerializer
    def get_queryset(self): return MarketplaceOffice.objects.filter(is_active=True).select_related("city")
    def get_permissions(self): return [AllowAny()] if self.action in {"list","retrieve"} else [IsAuthenticated()]
    def perform_create(self,serializer):
        if not (self.request.user.is_staff or self.request.user.role=="admin"): raise PermissionDenied("للمدير فقط")
        serializer.save()
    def perform_update(self,serializer):
        if not (self.request.user.is_staff or self.request.user.role=="admin"): raise PermissionDenied("للمدير فقط")
        serializer.save()
    def perform_destroy(self,instance):
        if not (self.request.user.is_staff or self.request.user.role=="admin"): raise PermissionDenied("للمدير فقط")
        instance.is_active=False; instance.save(update_fields=["is_active","updated_at"])
