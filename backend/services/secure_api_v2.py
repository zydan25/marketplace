from decimal import InvalidOperation

from django.db import IntegrityError, transaction
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .accounting_bridge import reserve_service_funds
from .api import (
    _clean_payload,
    _generated_keys,
    _hydrate_item_payload,
    _resolve_price,
    _transaction_data,
)
from .models import Service, ServiceTask, ServiceTransaction
from .secure_api import (
    IdempotencyConflict,
    ServiceRequestThrottle,
    _assert_item_ready_for_purchase,
    _matches_existing,
)
from .security import encrypt_secret


class CanonicalServiceRequestAPIView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [ServiceRequestThrottle]

    def _post(self, request):
        service_id = request.data.get("service_id")
        service = Service.objects.filter(pk=service_id, is_active=True).first()
        if not service:
            raise ValidationError({"service_id": "الخدمة غير موجودة أو متوقفة."})

        original_payload = request.data.get("payload", {})
        if not isinstance(original_payload, dict):
            raise ValidationError({"payload": "بيانات الخدمة يجب أن تكون بصيغة JSON object."})

        item_id = request.data.get("item_id")
        item_type = str(request.data.get("item_type", "") or "")
        key = str(request.headers.get("Idempotency-Key") or request.data.get("idempotency_key") or "").strip()
        if len(key) > 180:
            raise ValidationError({"idempotency_key": "Idempotency-Key طويل جدًا."})
        if service.requires_balance and service.service_kind == Service.ServiceKinds.PURCHASE and not key:
            raise ValidationError({"idempotency_key": "Idempotency-Key مطلوب لكل عملية مدفوعة."})

        if service.requires_balance and service.service_kind == Service.ServiceKinds.PURCHASE:
            _assert_item_ready_for_purchase(service, item_type, item_id)

        if key:
            existing = ServiceTransaction.objects.filter(idempotency_key=key).select_related("service").first()
            if existing:
                if not _matches_existing(existing, service, request):
                    raise IdempotencyConflict()
                return Response(_transaction_data(existing), status=200)

        hydrated, item = _hydrate_item_payload(service, original_payload, item_id=item_id, item_type=item_type)
        generated_keys = _generated_keys(original_payload, hydrated)
        payload = _clean_payload(service, hydrated, generated_keys=generated_keys)

        action = str(payload.get("method") or "").strip()
        free_actions = {str(value) for value in (service.metadata or {}).get("free_actions", [])}
        amount = 0 if action in free_actions else _resolve_price(service, payload, item=item)

        with transaction.atomic():
            tx = ServiceTransaction.objects.create(
                customer=request.user,
                service=service,
                item_type=item_type,
                item_id=int(item_id) if item_id else None,
                currency=service.currency,
                customer_amount=amount,
                payload=payload,
                mobile=str(payload.get("mobile", "")).strip(),
                status=ServiceTransaction.Status.ACCEPTED,
                idempotency_key=key or None,
                webhook_secret_encrypted=encrypt_secret(__import__("secrets").token_urlsafe(24)),
            )
            if service.requires_balance and amount > 0:
                journal = reserve_service_funds(tx)
                tx.reserved_journal_id = journal.pk if journal else None
            tx.status = ServiceTransaction.Status.QUEUED
            tx.save(update_fields=["reserved_journal_id", "status", "updated_at"])
            ServiceTask.objects.create(transaction=tx, kind=ServiceTask.Kinds.SUBMIT)
            return Response(_transaction_data(tx), status=202)

    def post(self, request, *args, **kwargs):
        try:
            return self._post(request)
        except (ValidationError, IdempotencyConflict):
            raise
        except IntegrityError as exc:
            key = str(request.headers.get("Idempotency-Key") or request.data.get("idempotency_key") or "").strip()
            if key:
                existing = ServiceTransaction.objects.filter(idempotency_key=key).select_related("service").first()
                if existing:
                    if _matches_existing(existing, existing.service, request):
                        return Response(_transaction_data(existing), status=200)
                    raise IdempotencyConflict() from exc
            raise
        except (ValueError, InvalidOperation) as exc:
            raise ValidationError({"detail": str(exc)}) from exc
