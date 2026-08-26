from decimal import Decimal
import uuid

from django.db import transaction
from django.utils import timezone
from rest_framework import serializers, viewsets
from rest_framework.decorators import action
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
        if not obj.image:
            return None
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
        if not value:
            return None
        request = self.context.get("request")
        return request.build_absolute_uri(value.url) if request else value.url

    def get_image_url(self, obj):
        return self._url(obj.image)

    def get_banner_url(self, obj):
        return self._url(obj.banner)

    def create(self, validated_data):
        field_rows = validated_data.pop("fields", [])
        service = Service.objects.create(**validated_data)
        for row in field_rows:
            ServiceField.objects.create(service=service, **row)
        return service

    def update(self, instance, validated_data):
        field_rows = validated_data.pop("fields", None)
        instance = super().update(instance, validated_data)
        if field_rows is not None:
            keep_ids = set()
            for row in field_rows:
                row = dict(row)
                field_id = row.pop("id", None)
                if field_id:
                    field = instance.fields.filter(id=field_id).first()
                    if not field:
                        raise serializers.ValidationError({"fields": "الحقل لا ينتمي إلى هذه الخدمة."})
                    for key, value in row.items():
                        setattr(field, key, value)
                    field.save()
                    keep_ids.add(field_id)
                else:
                    field = ServiceField.objects.create(service=instance, **row)
                    keep_ids.add(field.id)
            instance.fields.exclude(id__in=keep_ids).delete()
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
        qs = ServiceCategory.objects.filter(is_active=True).annotate(children_count_count=__import__("django.db.models", fromlist=["Count"]).Count("children"))
        if self.action not in {"list", "retrieve"}:
            if not (self.request.user.is_authenticated and (self.request.user.is_staff or self.request.user.role == "admin")):
                raise PermissionDenied("إدارة فئات الخدمات للمدير فقط")
        return qs

    def get_permissions(self):
        if self.action in {"list", "retrieve"}:
            return [AllowAny()]
        return [IsAuthenticated()]


class ServiceViewSet(viewsets.ModelViewSet):
    serializer_class = ServiceSerializer

    def get_queryset(self):
        qs = Service.objects.select_related("category").prefetch_related("fields")
        user = self.request.user
        if self.action in {"list", "retrieve"}:
            qs = qs.filter(is_active=True)
        elif not (user.is_authenticated and (user.is_staff or user.role == "admin")):
            raise PermissionDenied("إدارة الخدمات للمدير فقط")
        category = self.request.query_params.get("category")
        if category:
            qs = qs.filter(category_id=category)
        if self.request.query_params.get("featured") == "1":
            qs = qs.filter(is_featured=True)
        return qs

    def get_permissions(self):
        if self.action in {"list", "retrieve"}:
            return [AllowAny()]
        return [IsAuthenticated()]


class ServiceSubmissionViewSet(viewsets.ModelViewSet):
    serializer_class = ServiceSubmissionSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_queryset(self):
        user = self.request.user
        qs = ServiceSubmission.objects.select_related("service", "customer")
        if user.is_staff or user.role == "admin":
            return qs
        return qs.filter(customer=user)

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        service = Service.objects.filter(pk=request.data.get("service"), is_active=True).prefetch_related("fields").first()
        if not service:
            raise ValidationError({"service": "الخدمة غير موجودة أو غير متاحة."})
        data = request.data.get("data") or {}
        if not isinstance(data, dict):
            raise ValidationError({"data": "بيانات الخدمة يجب أن تكون كائنًا."})
        for field in service.fields.all():
            value = data.get(field.key)
            if field.is_required and (value is None or value == "" or value == []):
                raise ValidationError({"data": f"الحقل «{field.label}» مطلوب."})
            if field.field_type in {"select", "multiselect"} and field.options:
                allowed = {str(option.get("value", option)) if isinstance(option, dict) else str(option) for option in field.options}
                values = value if isinstance(value, list) else [value]
                invalid = [str(item) for item in values if str(item) not in allowed]
                if invalid:
                    raise ValidationError({"data": f"قيمة غير صالحة للحقل «{field.label}»."})
        if service.price > 0:
            wallet = Wallet.objects.select_for_update().filter(user=request.user).first()
            if not wallet:
                wallet = Wallet.objects.create(user=request.user)
            if wallet.currency != service.currency:
                raise ValidationError({"wallet": "عملة رصيد العميل لا تطابق عملة الخدمة."})
            if wallet.is_locked or wallet.balance < service.price:
                raise ValidationError({"wallet": "الرصيد غير كافٍ لإتمام الخدمة."})
            wallet.balance -= service.price
            wallet.save(update_fields=["balance", "updated_at"])
            WalletTransaction.objects.create(wallet=wallet, transaction_type=WalletTransaction.Types.PAYMENT, amount=-service.price, balance_after=wallet.balance, reference=f"SERVICE-{uuid.uuid4().hex[:10].upper()}", note=service.name, metadata={"service_id": service.id})
        submission = ServiceSubmission.objects.create(service=service, customer=request.user, amount=service.price, currency=service.currency, data=data, reference=f"SRV-{timezone.now():%Y%m%d}-{uuid.uuid4().hex[:6].upper()}")
        return Response(ServiceSubmissionSerializer(submission, context={"request": request}).data, status=201)
