from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .secure_catalog import SecureServiceDetailAPIView
from .settings_models import ServiceSetting


class ServiceSettingsAPIView(APIView):
    """Read-only API for the customer app to discover configured service IDs."""

    permission_classes = [IsAuthenticated]

    @staticmethod
    def _data(setting):
        service = setting.service
        service_data = None
        if service is not None:
            service_data = {
                "id": service.id,
                "code": service.code,
                "name": service.name,
                "slug": service.slug,
                "icon": service.icon,
                "category_id": service.category_id,
                "category": service.category.name,
                "main_category_id": service.category.main_category_id,
                "main_category": service.category.main_category.name,
                "detail_path": f"/api/services/services/{service.id}/",
            }
        return {
            "id": setting.id,
            "key": setting.key,
            "name": setting.name,
            "group": setting.group,
            "description": setting.description,
            "setting_type": setting.setting_type,
            "service_id": setting.service_id,
            "service": service_data,
            "value": setting.value,
            "is_configured": bool(service is not None) if setting.setting_type == ServiceSetting.Types.SERVICE else setting.value is not None,
            "updated_at": setting.updated_at,
        }

    def get(self, request):
        qs = ServiceSetting.objects.select_related("service__category__main_category").filter(is_active=True)
        key = (request.query_params.get("key") or "").strip()
        group = (request.query_params.get("group") or "").strip()
        service_id = (request.query_params.get("service_id") or "").strip()
        configured_only = request.query_params.get("configured") == "1"
        if key:
            qs = qs.filter(key=key)
        if group:
            qs = qs.filter(group=group)
        if service_id.isdigit():
            qs = qs.filter(service_id=int(service_id))
        if configured_only:
            qs = qs.exclude(setting_type=ServiceSetting.Types.SERVICE, service__isnull=True).exclude(setting_type__in=[ServiceSetting.Types.TEXT, ServiceSetting.Types.JSON, ServiceSetting.Types.BOOLEAN], value__isnull=True)

        rows = [self._data(setting) for setting in qs]
        return Response({"version": "1", "count": len(rows), "settings": rows})


class ServiceSettingDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, key):
        setting = get_object_or_404(
            ServiceSetting.objects.select_related("service__category__main_category"),
            key=key,
            is_active=True,
        )
        return Response(ServiceSettingsAPIView._data(setting))


class ServiceSettingServiceAPIView(APIView):
    """Resolve a configured setting directly to the full service contract."""

    permission_classes = [IsAuthenticated]

    def get(self, request, key):
        setting = get_object_or_404(
            ServiceSetting.objects.select_related("service__category__main_category"),
            key=key,
            is_active=True,
            setting_type=ServiceSetting.Types.SERVICE,
        )
        if setting.service_id is None or not setting.service.is_active:
            return Response({"detail": "هذا الإعداد غير مربوط بخدمة فعالة."}, status=409)
        response = SecureServiceDetailAPIView().get(request, setting.service_id)
        return Response({
            "setting": ServiceSettingsAPIView._data(setting),
            "service": response.data,
        }, status=response.status_code)
