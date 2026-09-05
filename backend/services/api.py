from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .accounting_bridge import reserve_service_funds
from .models import MainServiceCategory, Service, ServiceTransaction


def _clean_payload(service, payload):
    payload = payload if isinstance(payload, dict) else {}
    clean = dict(payload)
    for field in service.fields.filter(is_active=True).order_by("sort_order", "id"):
        value = clean.get(field.key, field.default_value)
        if field.required and (value is None or value == ""):
            raise ValueError(f"الحقل {field.label} مطلوب.")
        if value is not None and field.field_type in {field.FieldTypes.NUMBER, field.FieldTypes.DECIMAL}:
            try:
                value = Decimal(str(value)) if field.field_type == field.FieldTypes.DECIMAL else int(value)
            except (InvalidOperation, ValueError, TypeError):
                raise ValueError(f"قيمة {field.label} غير صالحة.")
        if isinstance(field.validation, dict):
            min_len = field.validation.get("min_length")
            max_len = field.validation.get("max_length")
            if min_len and len(str(value)) < int(min_len):
                raise ValueError(f"الحقل {field.label} أقصر من الحد المسموح.")
            if max_len and len(str(value)) > int(max_len):
                raise ValueError(f"الحقل {field.label} أطول من الحد المسموح.")
        clean[field.key] = value
    return clean


def _resolve_price(service, payload, item_id=None):
    if service.pricing_mode == Service.PricingModes.FIXED:
        return Decimal(service.price)
    if service.pricing_mode == Service.PricingModes.AMOUNT:
        amount = Decimal(str(payload.get("amount", "0")))
        if service.min_amount is not None and amount < service.min_amount:
            raise ValueError("المبلغ أقل من الحد الأدنى المسموح.")
        if service.max_amount is not None and amount > service.max_amount:
            raise ValueError("المبلغ أكبر من الحد الأعلى المسموح.")
        return amount
    if item_id is None:
        raise ValueError("يجب اختيار عنصر من جدول الخدمة.")
    item_models = [service.telecom_denominations.model, service.telecom_plans.model, service.game_products.model, service.digital_products.model]
    for model in item_models:
        item = model.objects.filter(pk=item_id, service=service, is_active=True).first()
        if item:
            return Decimal(item.sale_price if hasattr(item, "sale_price") else item.price)
    raise ValueError("عنصر الخدمة غير موجود أو غير فعال.")


class ServiceCatalogAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        roots = []
        for main in MainServiceCategory.objects.filter(is_active=True).prefetch_related("categories__children__services", "categories__services").order_by("sort_order", "id"):
            roots.append({
                "id": main.id,
                "name": main.name,
                "slug": main.slug,
                "icon": main.icon,
                "categories": [
                    {
                        "id": category.id,
                        "name": category.name,
                        "slug": category.slug,
                        "parent_id": category.parent_id,
                        "services": [
                            {
                                "id": service.id,
                                "code": service.code,
                                "name": service.name,
                                "description": service.description,
                                "pricing_mode": service.pricing_mode,
                                "price": str(service.price),
                                "currency": service.currency,
                                "fields": [
                                    {
                                        "key": f.key,
                                        "label": f.label,
                                        "type": f.field_type,
                                        "required": f.required,
                                        "choices": f.choices,
                                    }
                                    for f in service.fields.filter(is_active=True).order_by("sort_order", "id")
                                ],
                            }
                            for service in category.services.filter(is_active=True).order_by("sort_order", "id")
                        ],
                    }
                    for category in main.categories.filter(is_active=True, parent__isnull=True).order_by("sort_order", "id")
                ],
            })
        return Response({"categories": roots})


class ServiceDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        service = get_object_or_404(Service.objects.select_related("category__main_category"), pk=pk, is_active=True)
        return Response({
            "id": service.id,
            "code": service.code,
            "name": service.name,
            "description": service.description,
            "category": {"id": service.category_id, "name": service.category.name, "main_category": service.category.main_category.name},
            "pricing_mode": service.pricing_mode,
            "price": str(service.price),
            "min_amount": str(service.min_amount) if service.min_amount is not None else None,
            "max_amount": str(service.max_amount) if service.max_amount is not None else None,
            "currency": service.currency,
            "fields": [{"key": f.key, "label": f.label, "type": f.field_type, "required": f.required, "choices": f.choices} for f in service.fields.filter(is_active=True).order_by("sort_order", "id")],
        })


class ServiceRequestAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        service_id = request.data.get("service_id")
        payload = request.data.get("payload", {})
        item_id = request.data.get("item_id")
        idempotency_key = request.headers.get("Idempotency-Key") or request.data.get("idempotency_key")
        service = get_object_or_404(Service, pk=service_id, is_active=True)
        if idempotency_key:
            existing = ServiceTransaction.objects.filter(idempotency_key=idempotency_key, customer=request.user).first()
            if existing:
                return Response(_transaction_data(existing), status=200)
        try:
            payload = _clean_payload(service, payload)
            amount = _resolve_price(service, payload, item_id=item_id)
            mobile = str(payload.get("mobile", "")).strip()
            tx = ServiceTransaction.objects.create(
                customer=request.user,
                service=service,
                item_id=int(item_id) if item_id else None,
                currency=service.currency,
                customer_amount=amount,
                payload=payload,
                mobile=mobile,
                status=ServiceTransaction.Status.ACCEPTED,
                idempotency_key=idempotency_key,
            )
            journal = reserve_service_funds(tx)
            tx.reserved_journal_id = journal.pk
            tx.status = ServiceTransaction.Status.QUEUED
            tx.save(update_fields=["reserved_journal_id", "status", "updated_at"])
            from .models import ServiceTask
            ServiceTask.objects.create(transaction=tx, kind=ServiceTask.Kinds.SUBMIT)
        except ValueError as exc:
            transaction.set_rollback(True)
            return Response({"detail": str(exc)}, status=400)
        return Response(_transaction_data(tx), status=202)


def _transaction_data(tx):
    return {
        "id": str(tx.id),
        "service": tx.service.code,
        "status": tx.status,
        "amount": str(tx.customer_amount),
        "currency": tx.currency,
        "provider_transaction_id": tx.provider_transaction_id or None,
        "error_code": tx.error_code or None,
        "error_message": tx.error_message or None,
        "created_at": tx.created_at.isoformat(),
        "completed_at": tx.completed_at.isoformat() if tx.completed_at else None,
    }


class ServiceTransactionDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        tx = get_object_or_404(ServiceTransaction.objects.select_related("service"), pk=pk, customer=request.user)
        return Response(_transaction_data(tx))
