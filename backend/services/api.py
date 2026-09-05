import hashlib
import secrets

from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .accounting_bridge import reserve_service_funds
from .models import MainServiceCategory, Service, ServiceTask, ServiceTransaction
from .security import encrypt_secret


def _clean_payload(service, payload):
    if not isinstance(payload, dict):
        raise ValueError("بيانات الخدمة يجب أن تكون بصيغة JSON object.")
    allowed = {f.key: f for f in service.fields.filter(is_active=True)}
    cleaned = {}
    for key, field in allowed.items():
        value = payload.get(key, field.default_value)
        if field.required and (value is None or str(value).strip() == ""):
            raise ValueError(f"الحقل {field.label} مطلوب.")
        if value is not None:
            cleaned[key] = value
    unknown = set(payload) - set(allowed)
    if unknown:
        raise ValueError(f"حقول غير مسموحة: {', '.join(sorted(unknown))}")
    for key, field in allowed.items():
        if key not in cleaned:
            continue
        rule = field.validation or {}
        value = str(cleaned[key])
        if rule.get("min_length") is not None and len(value) < int(rule["min_length"]):
            raise ValueError(f"قيمة {field.label} أقصر من الحد المسموح.")
        if rule.get("max_length") is not None and len(value) > int(rule["max_length"]):
            raise ValueError(f"قيمة {field.label} أطول من الحد المسموح.")
        if field.choices and cleaned[key] not in field.choices:
            raise ValueError(f"قيمة {field.label} غير صالحة.")
    return cleaned


def _resolve_price(service, payload, *, item_id=None, item_type=""):
    from decimal import Decimal
    if service.pricing_mode == Service.PricingModes.FIXED:
        amount = Decimal(service.price)
    elif service.pricing_mode == Service.PricingModes.AMOUNT:
        try:
            amount = Decimal(str(payload.get("amount")))
        except Exception as exc:
            raise ValueError("المبلغ غير صالح.") from exc
        if service.min_amount is not None and amount < service.min_amount:
            raise ValueError("المبلغ أقل من الحد الأدنى.")
        if service.max_amount is not None and amount > service.max_amount:
            raise ValueError("المبلغ أكبر من الحد الأعلى.")
    else:
        if not item_id or not item_type:
            raise ValueError("يجب تحديد المنتج/الباقة للخدمة.")
        model_map = {"telecom_denominations": "telecom_denominations", "telecom_plans": "telecom_plans", "game_products": "game_products", "digital_products": "digital_products"}
        rel = model_map.get(item_type)
        if not rel:
            raise ValueError("نوع المنتج غير صالح.")
        item = getattr(service, rel).filter(pk=item_id, is_active=True).first()
        if not item:
            raise ValueError("العنصر المطلوب غير موجود أو متوقف.")
        amount = Decimal(getattr(item, "sale_price", getattr(item, "price", 0)))
    if amount <= 0:
        raise ValueError("قيمة الخدمة يجب أن تكون أكبر من صفر.")
    return amount.quantize(Decimal("0.01"))


def _service_items(service):
    result = []
    for rel_name, item_type in (("telecom_denominations", "telecom_denominations"), ("telecom_plans", "telecom_plans"), ("game_products", "game_products"), ("digital_products", "digital_products")):
        for item in getattr(service, rel_name).filter(is_active=True).order_by("sort_order", "id"):
            price = getattr(item, "sale_price", getattr(item, "price", 0))
            result.append({"id": item.id, "type": item_type, "name": item.name, "code": item.external_code, "price": str(price), "currency": getattr(item, "currency", service.currency), "metadata": item.metadata})
    return result


class ServiceCatalogAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        roots = []
        for main in MainServiceCategory.objects.filter(is_active=True).order_by("sort_order", "id"):
            roots.append({"id": main.id, "name": main.name, "slug": main.slug, "icon": main.icon, "categories": self._categories(main)})
        return Response({"categories": roots})

    def _categories(self, main):
        categories = list(main.categories.filter(is_active=True).prefetch_related("services", "children__services").order_by("sort_order", "id"))
        by_parent = {}
        for category in categories:
            by_parent.setdefault(category.parent_id, []).append(category)
        def build(category):
            return {"id": category.id, "name": category.name, "slug": category.slug, "parent_id": category.parent_id, "services": [self._service_data(service) for service in category.services.filter(is_active=True).order_by("sort_order", "id")], "children": [build(child) for child in by_parent.get(category.id, [])]}
        return [build(category) for category in by_parent.get(None, [])]

    @staticmethod
    def _service_data(service):
        return {
            "id": service.id, "code": service.code, "name": service.name, "description": service.description,
            "pricing_mode": service.pricing_mode, "price": str(service.price), "currency": service.currency,
            "min_amount": str(service.min_amount) if service.min_amount is not None else None,
            "max_amount": str(service.max_amount) if service.max_amount is not None else None,
            "fields": [{"key": f.key, "label": f.label, "type": f.field_type, "required": f.required, "choices": f.choices} for f in service.fields.filter(is_active=True).order_by("sort_order", "id")],
            "items": _service_items(service),
        }


class ServiceDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        service = get_object_or_404(Service.objects.select_related("category__main_category"), pk=pk, is_active=True)
        data = ServiceCatalogAPIView._service_data(service)
        data.update({"category": {"id": service.category_id, "name": service.category.name, "main_category": service.category.main_category.name}})
        return Response(data)


class ServiceRequestAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        service = get_object_or_404(Service, pk=request.data.get("service_id"), is_active=True)
        payload = request.data.get("payload", {})
        item_id = request.data.get("item_id")
        item_type = request.data.get("item_type", "")
        idempotency_key = request.headers.get("Idempotency-Key") or request.data.get("idempotency_key")
        if idempotency_key:
            existing = ServiceTransaction.objects.filter(idempotency_key=idempotency_key, customer=request.user).first()
            if existing:
                return Response(_transaction_data(existing), status=200)
        try:
            payload = _clean_payload(service, payload)
            amount = _resolve_price(service, payload, item_id=item_id, item_type=item_type)
            mobile = str(payload.get("mobile", "")).strip()
            tx = ServiceTransaction.objects.create(customer=request.user, service=service, item_type=item_type, item_id=int(item_id) if item_id else None, currency=service.currency, customer_amount=amount, payload=payload, mobile=mobile, status=ServiceTransaction.Status.ACCEPTED, idempotency_key=idempotency_key, webhook_secret_encrypted=encrypt_secret(secrets.token_urlsafe(24)))
            journal = reserve_service_funds(tx)
            tx.reserved_journal_id = journal.pk
            tx.status = ServiceTransaction.Status.QUEUED
            tx.save(update_fields=["reserved_journal_id", "status", "updated_at"])
            ServiceTask.objects.create(transaction=tx, kind=ServiceTask.Kinds.SUBMIT)
        except ValueError as exc:
            transaction.set_rollback(True)
            return Response({"detail": str(exc)}, status=400)
        return Response(_transaction_data(tx), status=202)


def _transaction_data(tx):
    return {"id": str(tx.id), "service": tx.service.code, "status": tx.status, "amount": str(tx.customer_amount), "currency": tx.currency, "provider_transaction_id": tx.provider_transaction_id or None, "error_code": tx.error_code or None, "error_message": tx.error_message or None, "created_at": tx.created_at.isoformat(), "completed_at": tx.completed_at.isoformat() if tx.completed_at else None}


class ServiceTransactionDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        tx = get_object_or_404(ServiceTransaction.objects.select_related("service"), pk=pk, customer=request.user)
        return Response(_transaction_data(tx))
