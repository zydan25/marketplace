from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .api import ServiceCatalogAPIView
from .models import MainServiceCategory, Service


_PUBLIC_METADATA_KEYS = {
    "quota",
    "quota_unit",
    "validity_days",
    "payment_type",
    "line_type",
    "catalog_only",
    "description",
}


def _public_item(item, item_type, service):
    metadata = getattr(item, "metadata", {}) or {}
    public_metadata = {key: metadata[key] for key in _PUBLIC_METADATA_KEYS if key in metadata}
    return {
        "id": item.id,
        "type": item_type,
        "name": item.name,
        "price": str(ServiceCatalogAPIView._service_data.__func__(service)["price"] if False else getattr(item, "price", 0)),
        "currency": getattr(item, "currency", service.currency),
        "metadata": public_metadata,
    }


class SecureServiceCatalogAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        roots = []
        for main in MainServiceCategory.objects.filter(is_active=True).order_by("sort_order", "id"):
            categories = []
            for category in main.categories.filter(is_active=True).prefetch_related("services", "children__services").order_by("sort_order", "id"):
                categories.append(self._category(category))
            roots.append({"id": main.id, "name": main.name, "slug": main.slug, "icon": main.icon, "categories": categories})
        return Response({"categories": roots})

    def _category(self, category):
        children = [self._category(child) for child in category.children.filter(is_active=True).order_by("sort_order", "id")]
        services = [self._service(service) for service in category.services.filter(is_active=True).order_by("sort_order", "id")]
        return {
            "id": category.id,
            "name": category.name,
            "slug": category.slug,
            "parent_id": category.parent_id,
            "services": services,
            "children": children,
        }

    @staticmethod
    def _service(service):
        items = []
        for item_type, relation in (
            ("service_options", service.options),
            ("telecom_denominations", service.telecom_denominations),
            ("telecom_plans", service.telecom_plans),
            ("game_products", service.game_products),
            ("digital_products", service.digital_products),
        ):
            for item in relation.filter(is_active=True).order_by("sort_order", "id"):
                item_data = {
                    "id": item.id,
                    "type": item_type,
                    "name": item.name,
                    "currency": getattr(item, "currency", service.currency),
                    "metadata": {},
                }
                if hasattr(item, "price"):
                    item_data["price"] = str(item.price)
                elif item_type == "telecom_denominations":
                    item_data["price"] = str(item.sale_price)
                metadata = getattr(item, "metadata", {}) or {}
                item_data["metadata"] = {key: metadata[key] for key in _PUBLIC_METADATA_KEYS if key in metadata}
                items.append(item_data)
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
            "fields": [
                {
                    "key": field.key,
                    "label": field.label,
                    "type": field.field_type,
                    "required": field.required,
                    "secret": field.secret,
                    "choices": field.choices,
                    "default": field.default_value,
                    "validation": field.validation,
                }
                for field in service.fields.filter(is_active=True).order_by("sort_order", "id")
            ],
            "items": items,
        }


class SecureServiceDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        service = get_object_or_404(Service.objects.select_related("category__main_category"), pk=pk, is_active=True)
        data = SecureServiceCatalogAPIView._service(service)
        data["category"] = {
            "id": service.category_id,
            "name": service.category.name,
            "main_category": service.category.main_category.name,
        }
        return Response(data)
