from rest_framework.exceptions import APIException, ValidationError
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle

from .api import ServiceRequestAPIView, ServiceTransactionDetailAPIView
from .models import Service, ServiceTransaction


class IdempotencyConflict(APIException):
    status_code = 409
    default_detail = "Idempotency-Key تعارض مع عملية مختلفة."
    default_code = "idempotency_conflict"


class ServiceRequestThrottle(ScopedRateThrottle):
    scope = "service_request"


_SECRET_KEYS = {
    "token", "password", "passwd", "pass", "backpass", "userid", "username",
    "authorization", "api_key", "apikey", "secret", "webhook_secret",
}


def _redact(value):
    if isinstance(value, dict):
        result = {}
        for key, child in value.items():
            normalized = str(key).strip().lower().replace("-", "_")
            if normalized in _SECRET_KEYS or "password" in normalized or normalized.endswith("token"):
                result[key] = "[REDACTED]"
            else:
                result[key] = _redact(child)
        return result
    if isinstance(value, list):
        return [_redact(item) for item in value]
    return value


def _safe_result(data):
    return _redact(data) if isinstance(data, (dict, list)) else data


class SecureServiceRequestAPIView(ServiceRequestAPIView):
    throttle_classes = [ServiceRequestThrottle]

    def post(self, request, *args, **kwargs):
        service_id = request.data.get("service_id")
        service = Service.objects.filter(pk=service_id, is_active=True).only("id", "requires_balance", "service_kind").first()
        key = str(request.headers.get("Idempotency-Key") or request.data.get("idempotency_key") or "").strip()

        if service and service.requires_balance and service.service_kind == Service.ServiceKinds.PURCHASE and not key:
            raise ValidationError({"idempotency_key": "Idempotency-Key مطلوب لكل عملية مدفوعة لمنع الخصم المكرر."})

        if key:
            existing = ServiceTransaction.objects.filter(idempotency_key=key).select_related("service").first()
            if existing:
                if existing.customer_id != request.user.id:
                    raise IdempotencyConflict()
                if service and existing.service_id != service.id:
                    raise IdempotencyConflict()
                if str(existing.item_id or "") != str(request.data.get("item_id") or ""):
                    raise IdempotencyConflict()
                if existing.item_type != str(request.data.get("item_type", "") or ""):
                    raise IdempotencyConflict()
                incoming_payload = request.data.get("payload", {})
                if not isinstance(incoming_payload, dict):
                    raise ValidationError({"payload": "بيانات الخدمة يجب أن تكون بصيغة JSON object."})
                for key_name, value in incoming_payload.items():
                    stored = (existing.payload or {}).get(key_name)
                    if str(stored) != str(value):
                        raise IdempotencyConflict()

        from django.db import IntegrityError
        try:
            response = super().post(request, *args, **kwargs)
        except IntegrityError as exc:
            raise IdempotencyConflict() from exc
        if isinstance(response, Response) and isinstance(response.data, dict) and "result" in response.data:
            response.data["result"] = _safe_result(response.data["result"])
        return response


class SecureServiceTransactionDetailAPIView(ServiceTransactionDetailAPIView):
    throttle_classes = [ServiceRequestThrottle]

    def get(self, request, pk):
        response = super().get(request, pk)
        if isinstance(response, Response) and isinstance(response.data, dict) and "result" in response.data:
            response.data["result"] = _safe_result(response.data["result"])
        return response
