from decimal import Decimal
import uuid

from django.db import transaction
from django.utils import timezone
from rest_framework import serializers, viewsets
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .models import Wallet, WalletTransaction
from .models_extra import ServiceCategory, Service, ServiceField, ServiceSubmission

class ServiceCategorySerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()
    children_count = serializers.IntegerField(read_only=True)
    class Meta:
        model = ServiceCategory
        fields = ["id", "name", "parent", "image", "image_url", "description", "sort_order", "is_active", "children_count"]
        read_only_fields = ["id", "image_url", "children_count"]
    def get_image_url(self, obj):
        if not obj.image: return None
        request = self.context.get("request")
        return request.build_absolute_uri(obj.image.url) if request else obj.image.url

class ServiceFieldSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceField
        fields = ["id", "key", "label", "field_type", "placeholder", "help_text", "is_required", "options", "sort_order"]
        read_only_fields = ["id"]

class ServiceSerializer(serializers.ModelSerializer):
    fields = ServiceFieldSerializer(many=True, required=False)
    image_url = serializers.SerializerMethodField()
    banner_url = serializers.SerializerMethodField()
    category_name = serializers.CharField(source="category.name", read_only=True)
    class Meta:
        model = Service
        fields = ["id", "name", "slug", "category", "category_name", "image", "image_url", "banner", "banner_url", "description", "price", "currency", "is_active", "is_featured", "sort_order", "config", "fields"]
        read_only_fields = ["id", "slug", "image_url", "banner_url"]
    def _url(self, value):
        if not value: return None
        request = self.context.get("request")
        return request.build_absolute_uri(value.url) if request else value.url
    def get_image_url(self, obj): return self._url(obj.image)
    def get_banner_url(self, obj): return self._url(obj.banner)
    def create(self, validated_data):
        rows = validated_data.pop("fields", [])
        service = Service.objects.create(**validated_data)
        for row in rows: ServiceField.objects.create(service=service, **row)
        return service
    def update(self, instance, validated_data):
        rows = validated_data.pop("fields", None)
        instance = super().update(instance, validated_data)
        if rows is not None:
            keep = set()
            for row in rows:
                row = dict(row); field_id = row.pop("id", None)
                if field_id:
                    field = instance.fields.filter(id=field_id).first()
                    if not field: raise serializers.ValidationError({"fields": "الحقل لا ينتمي إلى هذه الخدمة."})
                    for key, value in row.items(): setattr(field, key, value)
                    field.save(); keep.add(field_id)
                else:
                    field = ServiceField.objects.create(service=instance, **row); keep.add(field.id)
            instance.fields.exclude(id__in=keep).delete()
        return instance

class ServiceSubmissionSerializer(serializers.ModelSerializer):
    service_name = serializers.CharField(source="service.name", read_only=True)
    class Meta:
        model = ServiceSubmission
        fields = ["id", "reference", "service", "service_name", "customer", "amount", "currency", "data", "status", "notes", "created_at", "updated_at"]
        read_only_fields = ["id", "reference", "customer", "amount", "currency", "status", "created_at", "updated_at"]

class ServiceCategoryViewSet(viewsets.ModelViewSet):
    serializer_class = ServiceCategorySerializer
    def get_queryset(self):
        from django.db.models import Count
        return ServiceCategory.objects.filter(is_active=True).annotate(children_count=Count("children"))
    def get_permissions(self):
        return [AllowAny()] if self.action in {"list", "retrieve"} else [IsAuthenticated()]
    def perform_create(self, serializer):
        if not (self.request.user.is_staff or self.request.user.role == "admin"): raise PermissionDenied("إدارة فئات الخدمات للمدير فقط")
        serializer.save()
    def perform_update(self, serializer):
        if not (self.request.user.is_staff or self.request.user.role == "admin"): raise PermissionDenied("إدارة فئات الخدمات للمدير فقط")
        serializer.save()
    def perform_destroy(self, instance):
        if not (self.request.user.is_staff or self.request.user.role == "admin"): raise PermissionDenied("إدارة فئات الخدمات للمدير فقط")
        instance.is_active = False; instance.save(update_fields=["is_active", "updated_at"])

class ServiceViewSet(viewsets.ModelViewSet):
    serializer_class = ServiceSerializer
    def get_queryset(self):
        qs = Service.objects.select_related("category").prefetch_related("fields")
        if self.action in {"list", "retrieve"}: qs = qs.filter(is_active=True)
        category = self.request.query_params.get("category")
        if category: qs = qs.filter(category_id=category)
        if self.request.query_params.get("featured") == "1": qs = qs.filter(is_featured=True)
        return qs
    def get_permissions(self): return [AllowAny()] if self.action in {"list", "retrieve"} else [IsAuthenticated()]
    def perform_create(self, serializer):
        if not (self.request.user.is_staff or self.request.user.role == "admin"): raise PermissionDenied("إدارة الخدمات للمدير فقط")
        serializer.save()
    def perform_update(self, serializer):
        if not (self.request.user.is_staff or self.request.user.role == "admin"): raise PermissionDenied("إدارة الخدمات للمدير فقط")
        serializer.save()
    def perform_destroy(self, instance):
        if not (self.request.user.is_staff or self.request.user.role == "admin"): raise PermissionDenied("إدارة الخدمات للمدير فقط")
        instance.is_active = False; instance.save(update_fields=["is_active", "updated_at"])

class ServiceSubmissionViewSet(viewsets.ModelViewSet):
    serializer_class = ServiceSubmissionSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "post", "patch", "head", "options"]
    def get_queryset(self):
        user = self.request.user
        qs = ServiceSubmission.objects.select_related("service", "customer")
        return qs if (user.is_staff or user.role == "admin") else qs.filter(customer=user)
    @transaction.atomic
    def create(self, request, *args, **kwargs):
        service = Service.objects.filter(pk=request.data.get("service"), is_active=True).prefetch_related("fields").first()
        if not service: raise ValidationError({"service": "الخدمة غير موجودة أو غير متاحة."})
        data = request.data.get("data") or {}
        if not isinstance(data, dict): raise ValidationError({"data": "بيانات الخدمة يجب أن تكون كائنًا."})
        for field in service.fields.all():
            value = data.get(field.key)
            if field.is_required and value in (None, "", []): raise ValidationError({"data": f"الحقل «{field.label}» مطلوب."})
            if field.field_type in {"select", "multiselect"} and field.options:
                allowed = {str(x.get("value", x)) if isinstance(x, dict) else str(x) for x in field.options}
                values = value if isinstance(value, list) else [value]
                if any(str(x) not in allowed for x in values): raise ValidationError({"data": f"قيمة غير صالحة للحقل «{field.label}»."})
        if service.price > 0:
            wallet = Wallet.objects.select_for_update().filter(user=request.user).first() or Wallet.objects.create(user=request.user)
            if wallet.currency != service.currency or wallet.is_locked or wallet.balance < service.price: raise ValidationError({"wallet": "الرصيد غير كافٍ أو العملة غير مطابقة."})
            wallet.balance -= service.price; wallet.save(update_fields=["balance", "updated_at"])
            WalletTransaction.objects.create(wallet=wallet, transaction_type=WalletTransaction.Types.PAYMENT, amount=-service.price, balance_after=wallet.balance, reference=f"SERVICE-{uuid.uuid4().hex[:10].upper()}", note=service.name, metadata={"service_id": service.id})
        submission = ServiceSubmission.objects.create(service=service, customer=request.user, amount=service.price, currency=service.currency, data=data, reference=f"SRV-{timezone.now():%Y%m%d}-{uuid.uuid4().hex[:6].upper()}")
        return Response(ServiceSubmissionSerializer(submission, context={"request": request}).data, status=201)