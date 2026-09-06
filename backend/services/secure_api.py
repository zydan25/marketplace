from rest_framework.exceptions import APIException
from rest_framework.throttling import ScopedRateThrottle

from .api import ServiceRequestAPIView, ServiceTransactionDetailAPIView


class ServiceRequestThrottle(ScopedRateThrottle):
    scope = "service_request"


class SecureServiceRequestAPIView(ServiceRequestAPIView):
    throttle_classes = [ServiceRequestThrottle]

    def post(self, request, *args, **kwargs):
        try:
            return super().post(request, *args, **kwargs)
        except Exception as exc:
            # Let DRF's normal exceptions propagate; convert only an idempotency
            # collision from the DB layer into an explicit conflict when it
            # escapes the base endpoint.
            from django.db import IntegrityError
            if isinstance(exc, IntegrityError):
                raise APIException("تعذر تثبيت العملية بسبب تعارض فريد؛ أعد استخدام نفس Idempotency-Key لنفس الطلب فقط.")
            raise


class SecureServiceTransactionDetailAPIView(ServiceTransactionDetailAPIView):
    throttle_classes = [ServiceRequestThrottle]
