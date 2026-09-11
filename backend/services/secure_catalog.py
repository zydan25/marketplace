from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import MainServiceCategory, Service, TelecomPlanType


_PUBLIC_METADATA_KEYS = {
    "quota", "quota_unit", "validity_days", "payment_type", "line_type", "catalog_only",
    "description", "country", "region", "currency_name", "unit_detail", "detail",
}
_GENERATED_KEYS = {"external_code", "num", "packageid", "uniqcode"}


def _public_metadata(item):
    metadata = getattr(item, "metadata", {}) or {}
    return {key: str(metadata[key]) for key in _PUBLIC_METADATA_KEYS if key in metadata and metadata[key] is not None}


def _field_is_generated(service, field):
    if field.key in _GENERATED_KEYS:
        return True
    if field.key == "amount" and service.pricing_mode == Service.PricingModes.ITEM:
        return True
    if field.key == "mobile" and service.code in {"electric-query", "electric-bill", "water-query", "water-bill"}:
        return True
    return bool((field.validation or {}).get("server_generated"))


def _availability(item, service):
    metadata = getattr(item, "metadata", {}) or {}
    if metadata.get("purchaseable", True) is False:
        return {"available": "false", "reason": "غير متاح حاليًا"}
    quantity = metadata.get("provider_quantity")
    if quantity not in (None, ""):
        try:
            value = float(quantity)
            return {"available": "true" if value > 0 else "false", "quantity": str(quantity)}
        except (ValueError, TypeError):
            pass
    price = getattr(item, "sale_price", getattr(item, "price", 0))
    if service.service_kind == Service.ServiceKinds.PURCHASE and service.requires_balance:
        try:
            if float(price) <= 0:
                return {"available": "false", "reason": "السعر غير مهيأ"}
        except (TypeError, ValueError):
            return {"available": "false", "reason": "السعر غير صالح"}
    return {"available": "true" if getattr(item, "is_active", True) else "false"}


def _service_data(service):
    items = []
    relations = (
        ("service_options", service.options),
        ("telecom_denominations", service.telecom_denominations),
        ("telecom_plans", service.telecom_plans),
        ("game_products", service.game_products),
        ("digital_products", service.digital_products),
    )
    for item_type, relation in relations:
        for item in relation.filter(is_active=True).order_by("sort_order", "id"):
            item_data = {
                "id": item.id,
                "type": item_type,
                "name": item.name,
                "currency": getattr(item, "currency", service.currency),
                "metadata": _public_metadata(item),
                "availability": _availability(item, service),
            }
            if item_type == "telecom_denominations":
                item_data["price"] = str(item.sale_price)
            elif hasattr(item, "price"):
                item_data["price"] = str(item.price)
            if item_type == "telecom_plans":
                item_data["payment_type"] = item.payment_type
                item_data["line_type"] = item.line_type
                item_data["plan_type_ids"] = [plan_type.id for plan_type in item.plan_types.filter(is_active=True)]
            items.append(item_data)

    plan_types = []
    for plan_type in TelecomPlanType.objects.filter(service=service, is_active=True).select_related("parent").prefetch_related("plans").order_by("sort_order", "id"):
        plan_types.append({
            "id": plan_type.id,
            "code": plan_type.code,
            "name": plan_type.name,
            "description": plan_type.description,
            "parent_id": plan_type.parent_id,
            "plan_ids": [plan.id for plan in plan_type.plans.filter(is_active=True)],
        })

    return {
        "id": service.id,
        "code": service.code,
        "name": service.name,
        "icon": service.icon,
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
        "fields": [
            {"key": field.key, "label": field.label, "type": field.field_type, "required": field.required, "secret": field.secret, "choices": field.choices, "default": field.default_value, "validation": field.validation}
            for field in service.fields.filter(is_active=True).order_by("sort_order", "id")
            if not _field_is_generated(service, field)
        ],
        "items": items,
        "plan_types": plan_types,
    }


def _category_data(category):
    return {
        "id": category.id,
        "name": category.name,
        "slug": category.slug,
        "icon": category.icon,
        "parent_id": category.parent_id,
        "services": [_service_data(service) for service in category.services.filter(is_active=True)],
        "children": [_category_data(child) for child in category.children.filter(is_active=True).order_by("sort_order", "id")],
    }


def _games_as_children(category):
    result = []
    for service in category.services.filter(is_active=True).order_by("sort_order", "id"):
        result.append({"id": -service.id, "name": service.name, "slug": service.code, "icon": service.icon or "gamepad", "parent_id": category.id, "services": [_service_data(service)], "children": []})
    for child in category.children.filter(is_active=True).order_by("sort_order", "id"):
        result.append(_category_data(child))
    return result


class SecureServiceCatalogAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        roots = []
        for main in MainServiceCategory.objects.filter(is_active=True).order_by("sort_order", "id"):
            categories = []
            for category in main.categories.filter(is_active=True, parent=None).order_by("sort_order", "id"):
                if main.slug == "games" and category.slug == "games":
                    categories.append({"id": category.id, "name": category.name, "slug": category.slug, "icon": category.icon, "parent_id": None, "services": [], "children": _games_as_children(category)})
                else:
                    categories.append(_category_data(category))
            roots.append({"id": main.id, "name": main.name, "slug": main.slug, "icon": main.icon, "categories": categories})
        return Response({"version": "6", "categories": roots})


class SecureServiceDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        service = get_object_or_404(Service.objects.select_related("category__main_category"), pk=pk, is_active=True)
        data = _service_data(service)
        data["category"] = {"id": service.category_id, "name": service.category.name, "main_category": service.category.main_category.name}
        return Response(data)
