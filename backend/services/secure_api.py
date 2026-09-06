from rest_framework.exceptions import APIException
from rest_framework.throttling import ScopedRateThrottle

from .api import ServiceRequestAPIView, ServiceTransactionDetailAPIView


class IdempotencyConflict(APIException):
    status_code = 409
    default_detail = "Idempotency-Key تعارض مع عملية مختلفة."
    default_code = "idempotency_conflict"


class ServiceRequestThrottle(ScopedRateThrottle):
    scope = "service_request"


class SecureServiceRequestAPIView(ServiceRequestAPIView):
    throttle_classes = [ServiceRequestThrottle]

    def post(self, request, *args, **kwargs):
        from django.db import IntegrityError
        try:
            return super().post(request, *args, **kwargs)
        except IntegrityError as exc:
            raise IdempotencyConflict() from exc


class SecureServiceTransactionDetailAPIView(ServiceTransactionDetailAPIView):
    throttle_classes = [ServiceRequestThrottle]
