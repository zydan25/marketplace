import re
import secrets
from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .accounting_bridge import reserve_service_funds
from .models import DigitalProduct, GameProduct, MainServiceCategory, Service, ServiceOption, ServiceTask, ServiceTransaction, TelecomDenomination, TelecomPlan
from .security import encrypt_secret


def _normalize_digits(value):
    if value is None:
        return ""
    return str(value).translate(str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "01234567890123456789"))


def _clean_payload(service, payload):
    if not isinstance(payload, dict):
        raise ValueError("بيانات الخدمة يجب أن تكون بصيغة JSON object.")
    allowed = {f.key: f for f in service.fields.filter(is_active=True)}
    cleaned = {}
    for key, field in allowed.items():
        value = payload.get(key, field.default_value)
        if value is None:
            if field.required:
                raise ValueError(f"الحقل {field.label} مطلوب.")
            continue
        if isinstance(value, str):
            value = value.strip()
        if key == "mobile":
            value = _normalize_digits(value)
        if field.required and str(value).strip() == "":
            raise ValueError(f"الحقل {field.label} مطلوب.")
        if field.field_type in {"number", "decimal"}:
            try:
                Decimal(str(value))
            except (InvalidOperation, TypeError, ValueError) as exc:
                raise ValueError(f"قيمة {field.label} يجب أن تكون رقمًا.") from exc
        if field.field_type == "email" and value:
            if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", str(value)):
                raise ValueError(f"البريد الإلكتروني في {field.label} غير صالح.")
        rule = field.validation or {}
        text_value = str(value)
        if rule.get("min_length") is not None and len(text_value) < int(rule["min_length"]):
            raise ValueError(f"قيمة {field.label} أقصر من الحد المسموح.")
        if rule.get("max_length") is not None and len(text_value) > int(rule["max_length"]):
            raise ValueError(f"قيمة {field.label} أطول من الحد المسموح.")
        if rule.get("pattern") and not re.fullmatch(str(rule["pattern"]), text_value):
            raise ValueError(f"قيمة {field.label} لا تطابق الصيغة المطلوبة.")
        if field.choices and str(value) not in {str(choice) for choice in field.choices}:
            raise ValueError(f"قيمة {field.label} غير صالحة.")
        if rule.get("min") is not None and field.field_type in {"number", "decimal"} and Decimal(str(value)) < Decimal(str(rule["min"])):
            raise ValueError(f"قيمة {field.label} أقل من الحد الأدنى.")
        if rule.get("max") is not None and field.field_type in {"number", "decimal"} and Decimal(str(value)) > Decimal(str(rule["max"])):
            raise ValueError(f"قيمة {field.label} أكبر من الحد الأعلى.")
        cleaned[key] = value
    unknown = set(payload) - set(allowed)
    if unknown:
        raise ValueError(f"حقول غير مسموحة: {', '.join(sorted(unknown))}")
    return cleaned


def _resolve_item(service, item_id, item_type):
    if not item_id or not item_type:
        raise ValueError("يجب تحديد المنتج/الباقة للخدمة.")
    rel_map = {
        "telecom_denominations": "telecom_denominations",
        "telecom_plans": "telecom_plans",
        "game_products": "game_products",
        "digital_products": "digital_products",
        "service_options": "options",
    }
    rel = rel_map.get(item_type)
    if not rel:
        raise ValueError("نوع المنتج غير صالح.")
    item = getattr(service, rel).filter(pk=item_id, is_active=True).first()
    if not item:
        raise ValueError("العنصر المطلوب غير موجود أو متوقف.")
    return item


def _hydrate_item_payload(service, payload, *, item_id=None, item_type=""):
    if not item_id or not item_type:
        return dict(payload), None
    item = _resolve_item(service, item_id, item_type)
    hydrated = dict(payload)
    external_code = str(getattr(item, "external_code", "") or "")
    metadata = dict(getattr(item, "metadata", {}) or {})
    provider_num = str(metadata.get("provider_num", "") or getattr(item, "provider_num", "") or "")
    if external_code:
        hydrated["external_code"] = external_code
    if provider_num:
        hydrated["num"] = provider_num
    if item_type == "service_options":
        for key in ("packageid", "uniqcode"):
            if metadata.get(key):
                hydrated[key] = metadata[key]
    if item_type == "telecom_denominations" and metadata.get("provider_num"):
        hydrated["num"] = str(metadata["provider_num"])
    if item_type == "telecom_plans" and metadata.get("provider_num"):
        hydrated["num"] = str(metadata["provider_num"])
    if item_type == "telecom_denominations" and service.code == "yem-denomination":
        hydrated["amount"] = str(item.face_value)
    if item_type == "telecom_plans" and service.code in {"yem4g-package", "yem4g-change"}:
        hydrated["amount"] = str(item.price)
    if item_type in {"game_products", "digital_products"}:
        uniqcode = metadata.get("uniqcode") or metadata.get("uniq_code")
        if uniqcode:
            hydrated["uniqcode"] = str(uniqcode)
    return hydrated, item


def _item_amount(item):
    if item is None:
        return Decimal("0.00")
    if isinstance(item, TelecomDenomination):
        return Decimal(str(item.sale_price))
    if isinstance(item, (TelecomPlan, GameProduct, DigitalProduct, ServiceOption)):
        return Decimal(str(item.price))
    return Decimal("0.00")


def _resolve_price(service, payload, *, item=None):
    if not service.requires_balance or service.service_kind in {Service.ServiceKinds.QUERY, Service.ServiceKinds.CATALOG}:
        return Decimal("0.00")
    if item is not None and bool((getattr(item, "metadata", {}) or {}).get("requires_balance", True)) is False:
        return Decimal("0.00")
    if service.pricing_mode == Service.PricingModes.FIXED:
        amount = Decimal(service.price)
    elif service.pricing_mode == Service.PricingModes.AMOUNT:
        try:
            amount = Decimal(str(payload.get("amount")))
        except (InvalidOperation, TypeError, ValueError) as exc:
            raise ValueError("المبلغ غير صالح.") from exc
        if service.min_amount is not None and amount < service.min_amount:
            raise ValueError("المبلغ أقل من الحد الأدنى.")
        if service.max_amount is not None and amount > service.max_amount:
            raise ValueError("المبلغ أكبر من الحد الأعلى.")
    elif service.pricing_mode == Service.PricingModes.ITEM:
        amount = _item_amount(item)
    else:
        raise ValueError("طريقة تسعير الخدمة غير مدعومة.")
    if amount < 0:
        raise ValueError("قيمة الخدمة لا يمكن أن تكون سالبة.")
    if amount == 0:
        raise ValueError("الخدمة المدفوعة تحتاج إلى سعر أكبر من صفر، أو اضبطها كخدمة مجانية/استعلام.")
    return amount.quantize(Decimal("0.01"))


def _service_items(service):
    result = []
    models = [
        ("service_options", service.options.filter(is_active=True)),
        ("telecom_denominations", service.telecom_denominations.filter(is_active=True)),
        ("telecom_plans", service.telecom_plans.filter(is_active=True)),
        ("game_products", service.game_products.filter(is_active=True)),
        ("digital_products", service.digital_products.filter(is_active=True)),
    ]
    for item_type, qs in models:
        for item in qs.order_by("sort_order", "id"):
            result.append({
                "id": item.id,
                "type": item_type,
                "name": item.name,
                "code": getattr(item, "external_code", ""),
                "provider_num": str(getattr(item, "provider_num", "") or (getattr(item, "metadata", {}) or {}).get("provider_num", "")),
                "price": str(_item_amount(item)),
                "currency": getattr(item, "currency", service.currency),
                "metadata": getattr(item, "metadata", {}) or {},
            })
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
            return {
                "id": category.id,
                "name": category.name,
                "slug": category.slug,
                "parent_id": category.parent_id,
                "services": [self._service_data(service) for service in category.services.filter(is_active=True).order_by("sort_order", "id")],
                "children": [build(child) for child in by_parent.get(category.id, [])],
            }

        return [build(category) for category in by_parent.get(None, [])]

    @staticmethod
    def _service_data(service):
        return {
            "id": service.id,
            "code": service.code,
            "name": service.name,
            "description": service.description,
            "service_kind": service.service_kind,
            "requires_balance": service.requires_balance,
            "pricing_mode": service.pricing_mode,
            "price": str(service.price),
            "currency": service.currency,
            "min_amount": str(service.min_amount) if service.min_amount is not None else None,
            "max_amount": str(service.max_amount) if service.max_amount is not None else None,
            "request_schema": service.request_schema,
            "response_schema": service.response_schema,
            "fields": [{
                "key": f.key,
                "label": f.label,
                "type": f.field_type,
                "required": f.required,
                "secret": f.secret,
                "choices": f.choices,
                "default": f.default_value,
                "validation": f.validation,
            } for f in service.fields.filter(is_active=True).order_by("sort_order", "id")],
            "items": _service_items(service),
        }


class ServiceDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        service = get_object_or_404(Service.objects.select_related("category__main_category"), pk=pk, is_active=True)
        data = ServiceCatalogAPIView._service_data(service)
        data["category"] = {"id": service.category_id, "name": service.category.name, "main_category": service.category.main_category.name}
        return Response(data)


class ServiceRequestAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        service = get_object_or_404(Service, pk=request.data.get("service_id"), is_active=True)
        original_payload = request.data.get("payload", {})
        item_id = request.data.get("item_id")
        item_type = str(request.data.get("item_type", "") or "")
        idempotency_key = request.headers.get("Idempotency-Key") or request.data.get("idempotency_key")
        if idempotency_key:
            existing = ServiceTransaction.objects.filter(idempotency_key=idempotency_key, customer=request.user).first()
            if existing:
                return Response(_transaction_data(existing), status=200)
        try:
            hydrated, item = _hydrate_item_payload(service, original_payload, item_id=item_id, item_type=item_type)
            payload = _clean_payload(service, hydrated)
            if service.pricing_mode == Service.PricingModes.ITEM and item is None and service.requires_balance:
                raise ValueError("هذه الخدمة تعتمد على كتالوج؛ اختر الباقة/الفئة أولًا.")
            amount = _resolve_price(service, payload, item=item)
            mobile = str(payload.get("mobile", "")).strip()
            tx = ServiceTransaction.objects.create(
                customer=request.user,
                service=service,
                item_type=item_type,
                item_id=int(item_id) if item_id else None,
                currency=service.currency,
                customer_amount=amount,
                payload=payload,
                mobile=mobile,
                status=ServiceTransaction.Status.ACCEPTED,
                idempotency_key=idempotency_key,
                webhook_secret_encrypted=encrypt_secret(secrets.token_urlsafe(24)),
            )
            if service.requires_balance and amount > 0:
                journal = reserve_service_funds(tx)
                tx.reserved_journal_id = journal.pk if journal else None
            tx.status = ServiceTransaction.Status.QUEUED
            tx.save(update_fields=["reserved_journal_id", "status", "updated_at"])
            ServiceTask.objects.create(transaction=tx, kind=ServiceTask.Kinds.SUBMIT)
        except (ValueError, InvalidOperation) as exc:
            transaction.set_rollback(True)
            return Response({"detail": str(exc)}, status=400)
        return Response(_transaction_data(tx), status=202)


def _transaction_data(tx):
    return {
        "id": str(tx.id),
        "service": tx.service.code,
        "service_kind": tx.service.service_kind,
        "status": tx.status,
        "amount": str(tx.customer_amount),
        "currency": tx.currency,
        "provider_transid": tx.provider_transid,
        "provider_transaction_id": tx.provider_transaction_id or None,
        "error_code": tx.error_code or None,
        "error_message": tx.error_message or None,
        "result": tx.provider_response if tx.service.service_kind in {Service.ServiceKinds.QUERY, Service.ServiceKinds.CATALOG} else None,
        "created_at": tx.created_at.isoformat(),
        "completed_at": tx.completed_at.isoformat() if tx.completed_at else None,
    }


class ServiceTransactionDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        tx = get_object_or_404(ServiceTransaction.objects.select_related("service"), pk=pk, customer=request.user)
        return Response(_transaction_data(tx))
