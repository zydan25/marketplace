import json
from decimal import Decimal, InvalidOperation
from urllib.parse import urlparse

from django.db import transaction
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.status import HTTP_201_CREATED, HTTP_400_BAD_REQUEST, HTTP_403_FORBIDDEN, HTTP_404_NOT_FOUND
from rest_framework.views import APIView

from .catalog_sync import sync_provider_link
from .models import DigitalProduct, GameProduct, MainServiceCategory, ProviderConnection, ProviderLink, Service, ServiceCategory, ServiceDistribution, ServiceField, ServiceOption, TelecomDenomination, TelecomPlan


RESOURCE_MODELS = {
    "option": ServiceOption,
    "denom": TelecomDenomination,
    "plan": TelecomPlan,
    "game": GameProduct,
    "digital": DigitalProduct,
}


def _staff(user):
    return bool(user and user.is_authenticated and (user.is_staff or getattr(user, "role", None) == "admin"))


def _json(value, default):
    if value in (None, "", {}):
        return default
    if isinstance(value, (dict, list)):
        return value
    try:
        return json.loads(value)
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        raise ValueError("JSON غير صالح.") from exc


def _dec(value, *, required=False):
    if value in (None, ""):
        if required:
            raise ValueError("القيمة المالية مطلوبة.")
        return None
    try:
        amount = Decimal(str(value)).quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise ValueError("القيمة المالية غير صالحة.") from exc
    if amount < 0:
        raise ValueError("القيمة المالية لا يمكن أن تكون سالبة.")
    return amount


def _url_ok(value, *, required=True):
    value = str(value or "").strip()
    if not value and not required:
        return ""
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("base_url يجب أن يكون رابط HTTP/HTTPS صالحًا.")
    return value


def _public_item(item):
    return {
        "id": item.id,
        "type": item.__class__.__name__,
        "name": item.name,
        "price": str(getattr(item, "sale_price", getattr(item, "price", 0))),
        "currency": getattr(item, "currency", "YER"),
        "is_active": item.is_active,
        "provider_num": str((getattr(item, "metadata", {}) or {}).get("provider_num", getattr(item, "provider_num", "") or "")),
        "provider_link_number": str((getattr(item, "metadata", {}) or {}).get("provider_link_number", "")),
        "provider_quantity": (getattr(item, "metadata", {}) or {}).get("provider_quantity"),
        "purchaseable": (getattr(item, "metadata", {}) or {}).get("purchaseable", True),
    }


class CatalogAdminAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def _guard(self, request):
        if not _staff(request.user):
            return Response({"detail": "هذه الواجهة للمدير فقط."}, status=HTTP_403_FORBIDDEN)
        return None

    def get(self, request):
        denied = self._guard(request)
        if denied:
            return denied
        return Response({
            "main_categories": list(MainServiceCategory.objects.values("id", "name", "slug", "icon", "sort_order", "is_active")),
            "categories": list(ServiceCategory.objects.select_related("main_category", "parent").values("id", "main_category_id", "parent_id", "name", "slug", "icon", "sort_order", "is_active")),
            "services": list(Service.objects.select_related("category").values("id", "category_id", "name", "slug", "code", "service_kind", "requires_balance", "pricing_mode", "price", "currency", "min_amount", "max_amount", "sort_order", "is_active")),
            "providers": list(ProviderConnection.objects.values("id", "name", "code", "connection_type", "base_url", "userid", "domain_name", "username", "timeout_seconds", "max_retries", "is_active")),
            "links": list(ProviderLink.objects.select_related("provider").values("id", "provider_id", "name", "code", "operation", "path_template", "http_method", "request_encoding", "priority", "is_active")),
            "distributions": list(ServiceDistribution.objects.select_related("service", "provider_link").values("id", "service_id", "provider_link_id", "priority", "is_active")),
        })


class CatalogAdminEntityAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request, entity):
        if not _staff(request.user):
            return Response({"detail": "هذه الواجهة للمدير فقط."}, status=HTTP_403_FORBIDDEN)
        try:
            data = request.data
            if entity == "main":
                obj_id = data.get("id")
                obj = MainServiceCategory.objects.select_for_update().filter(pk=obj_id).first() if obj_id else None
                if obj is None:
                    obj = MainServiceCategory()
                obj.name = str(data.get("name") or "").strip()
                obj.slug = str(data.get("slug") or obj.name).strip()
                if not obj.name or not obj.slug:
                    raise ValueError("اسم ومعرف الفئة الرئيسية مطلوبان.")
                obj.description = str(data.get("description") or "").strip()
                obj.icon = str(data.get("icon") or "").strip()
                obj.sort_order = int(data.get("sort_order") or 0)
                obj.is_active = bool(data.get("is_active", True))
                obj.save()
                return Response({"id": obj.id, "name": obj.name, "slug": obj.slug}, status=HTTP_201_CREATED)

            if entity == "category":
                main = MainServiceCategory.objects.filter(pk=data.get("main_category_id"), is_active=True).first()
                if not main:
                    raise ValueError("الفئة الرئيسية غير موجودة أو متوقفة.")
                parent = ServiceCategory.objects.filter(pk=data.get("parent_id"), main_category=main).first() if data.get("parent_id") else None
                obj = ServiceCategory.objects.select_for_update().filter(pk=data.get("id") or 0).first() or ServiceCategory()
                obj.main_category = main
                obj.parent = parent
                obj.name = str(data.get("name") or "").strip()
                obj.slug = str(data.get("slug") or obj.name).strip()
                if not obj.name or not obj.slug:
                    raise ValueError("اسم ومعرف الفئة مطلوبان.")
                obj.description = str(data.get("description") or "").strip()
                obj.icon = str(data.get("icon") or "").strip()
                obj.sort_order = int(data.get("sort_order") or 0)
                obj.is_active = bool(data.get("is_active", True))
                obj.save()
                return Response({"id": obj.id, "main_category_id": main.id, "parent_id": obj.parent_id, "name": obj.name, "slug": obj.slug}, status=HTTP_201_CREATED)

            if entity == "service":
                category = ServiceCategory.objects.filter(pk=data.get("category_id"), is_active=True).first()
                if not category:
                    raise ValueError("فئة الخدمة غير موجودة أو متوقفة.")
                obj = Service.objects.select_for_update().filter(pk=data.get("id") or 0).first() or Service()
                obj.category = category
                obj.name = str(data.get("name") or "").strip()
                obj.code = str(data.get("code") or "").strip()
                obj.slug = str(data.get("slug") or obj.code or obj.name).strip()
                if not obj.name or not obj.code or not obj.slug:
                    raise ValueError("الاسم والكود والمعرف مطلوبة.")
                obj.description = str(data.get("description") or "").strip()
                obj.service_kind = str(data.get("service_kind") or Service.ServiceKinds.PURCHASE)
                obj.requires_balance = bool(data.get("requires_balance", True))
                obj.pricing_mode = str(data.get("pricing_mode") or Service.PricingModes.FIXED)
                obj.price = _dec(data.get("price"), required=False) or Decimal("0.00")
                obj.min_amount = _dec(data.get("min_amount"))
                obj.max_amount = _dec(data.get("max_amount"))
                if obj.min_amount is not None and obj.max_amount is not None and obj.min_amount > obj.max_amount:
                    raise ValueError("الحد الأدنى لا يمكن أن يتجاوز الحد الأعلى.")
                obj.currency = str(data.get("currency") or "YER").upper()[:6]
                obj.icon = str(data.get("icon") or "").strip()
                obj.sort_order = int(data.get("sort_order") or 0)
                obj.metadata = _json(data.get("metadata"), {})
                obj.request_schema = _json(data.get("request_schema"), {})
                obj.response_schema = _json(data.get("response_schema"), {})
                obj.is_active = bool(data.get("is_active", True))
                obj.save()
                return Response({"id": obj.id, "code": obj.code, "name": obj.name}, status=HTTP_201_CREATED)

            if entity == "field":
                service = Service.objects.filter(pk=data.get("service_id"), is_active=True).first()
                if not service:
                    raise ValueError("الخدمة غير موجودة أو متوقفة.")
                obj = ServiceField.objects.select_for_update().filter(pk=data.get("id") or 0).first() or ServiceField(service=service)
                obj.service = service
                obj.key = str(data.get("key") or "").strip()
                obj.label = str(data.get("label") or obj.key).strip()
                obj.field_type = str(data.get("field_type") or ServiceField.FieldTypes.TEXT)
                obj.required = bool(data.get("required", True))
                obj.secret = bool(data.get("secret", False))
                obj.choices = _json(data.get("choices"), [])
                obj.validation = _json(data.get("validation"), {})
                obj.default_value = _json(data.get("default_value"), None)
                obj.sort_order = int(data.get("sort_order") or 0)
                obj.is_active = bool(data.get("is_active", True))
                if not obj.key:
                    raise ValueError("مفتاح الحقل مطلوب.")
                obj.save()
                return Response({"id": obj.id, "service_id": service.id, "key": obj.key}, status=HTTP_201_CREATED)

            if entity == "provider":
                obj = ProviderConnection.objects.select_for_update().filter(pk=data.get("id") or 0).first() or ProviderConnection()
                obj.name = str(data.get("name") or "").strip()
                obj.code = str(data.get("code") or "").strip()
                if not obj.name or not obj.code:
                    raise ValueError("اسم وكود المزود مطلوبان.")
                obj.connection_type = str(data.get("connection_type") or ProviderConnection.Types.SANAACASH)
                obj.base_url = _url_ok(data.get("base_url"), required=obj.connection_type != ProviderConnection.Types.MANUAL)
                obj.userid = str(data.get("userid") or "").strip()
                obj.domain_name = str(data.get("domain_name") or "").strip()
                obj.username = str(data.get("username") or "").strip()
                obj.headers = _json(data.get("headers"), {})
                obj.timeout_seconds = max(1, min(120, int(data.get("timeout_seconds") or 20)))
                obj.max_retries = max(0, min(10, int(data.get("max_retries") or 0)))
                obj.metadata = _json(data.get("metadata"), {})
                obj.is_active = bool(data.get("is_active", True))
                password = str(data.get("password") or "")
                if password:
                    obj.set_password(password)
                elif not obj.pk and obj.connection_type != ProviderConnection.Types.MANUAL:
                    raise ValueError("كلمة مرور المزود مطلوبة عند إنشاء الربط.")
                obj.save()
                return Response({"id": obj.id, "name": obj.name, "code": obj.code, "is_active": obj.is_active}, status=HTTP_201_CREATED)

            if entity == "link":
                provider = ProviderConnection.objects.filter(pk=data.get("provider_id"), is_active=True).first()
                if not provider:
                    raise ValueError("المزود غير موجود أو متوقف.")
                obj = ProviderLink.objects.select_for_update().filter(pk=data.get("id") or 0).first() or ProviderLink()
                obj.provider = provider
                obj.name = str(data.get("name") or "").strip()
                obj.code = str(data.get("code") or "").strip()
                obj.operation = str(data.get("operation") or "").strip()
                obj.path_template = str(data.get("path_template") or "").strip()
                obj.http_method = str(data.get("http_method") or "GET").upper()
                obj.request_encoding = str(data.get("request_encoding") or "query").lower()
                obj.fixed_params = _json(data.get("fixed_params"), {})
                obj.field_map = _json(data.get("field_map"), {})
                obj.headers = _json(data.get("headers"), {})
                obj.success_codes = _json(data.get("success_codes"), ["0"])
                obj.pending_codes = _json(data.get("pending_codes"), ["-2"])
                obj.status_path_template = str(data.get("status_path_template") or "").strip()
                obj.status_params = _json(data.get("status_params"), {})
                obj.metadata = _json(data.get("metadata"), {})
                obj.priority = max(1, int(data.get("priority") or 100))
                obj.is_active = bool(data.get("is_active", True))
                if not obj.name or not obj.code or not obj.path_template:
                    raise ValueError("اسم وكود ومسار الربطية مطلوبة.")
                if obj.operation == "" and obj.metadata.get("catalog", {}).get("enabled"):
                    raise ValueError("ربط الكتالوج يحتاج operation واضحًا.")
                obj.save()
                return Response({"id": obj.id, "provider_id": provider.id, "code": obj.code}, status=HTTP_201_CREATED)

            if entity == "distribution":
                service = Service.objects.filter(pk=data.get("service_id"), is_active=True).first()
                link = ProviderLink.objects.select_related("provider").filter(pk=data.get("provider_link_id"), is_active=True, provider__is_active=True).first()
                if not service or not link:
                    raise ValueError("الخدمة أو الربطية غير موجودة/غير فعالة.")
                obj = ServiceDistribution.objects.select_for_update().filter(pk=data.get("id") or 0).first()
                if obj is None:
                    obj, _ = ServiceDistribution.objects.get_or_create(service=service, provider_link=link)
                else:
                    obj.service = service
                    obj.provider_link = link
                obj.priority = max(1, int(data.get("priority") or 100))
                obj.conditions = _json(data.get("conditions"), {})
                obj.is_active = bool(data.get("is_active", True))
                obj.save()
                return Response({"id": obj.id, "service_id": service.id, "provider_link_id": link.id}, status=HTTP_201_CREATED)

            if entity == "resource":
                kind = str(data.get("kind") or "").strip()
                model = RESOURCE_MODELS.get(kind)
                if model is None:
                    raise ValueError("نوع المورد غير صالح.")
                service = Service.objects.filter(pk=data.get("service_id"), is_active=True).first()
                if not service:
                    raise ValueError("الخدمة غير موجودة أو متوقفة.")
                obj = model.objects.select_for_update().filter(pk=data.get("id") or 0).first() or model(service=service)
                obj.service = service
                obj.name = str(data.get("name") or "").strip()
                obj.external_code = str(data.get("external_code") or "").strip()
                obj.sort_order = int(data.get("sort_order") or 0)
                obj.is_active = bool(data.get("is_active", True))
                if not obj.name or not obj.external_code:
                    raise ValueError("اسم المورد والكود الخارجي مطلوبان.")
                meta = _json(data.get("metadata"), {})
                provider_num = str(data.get("provider_num") or "").strip()
                provider_quantity = data.get("provider_quantity")
                if provider_num:
                    meta["provider_num"] = provider_num
                if provider_quantity not in (None, ""):
                    meta["provider_quantity"] = str(provider_quantity)
                meta["provider_link_number"] = str(data.get("provider_link_number") or meta.get("provider_link_number") or "")
                meta["provider_packageid"] = str(data.get("provider_packageid") or meta.get("provider_packageid") or "")
                meta["provider_uniqcode"] = str(data.get("provider_uniqcode") or meta.get("provider_uniqcode") or "")
                if data.get("purchaseable") is not None:
                    meta["purchaseable"] = bool(data.get("purchaseable"))
                if kind == "denom":
                    obj.face_value = _dec(data.get("face_value"), required=True)
                    obj.sale_price = _dec(data.get("sale_price"), required=True)
                    obj.payment_type = str(data.get("payment_type") or "")
                    obj.line_type = str(data.get("line_type") or "")
                else:
                    obj.price = _dec(data.get("price"), required=True)
                    obj.currency = str(data.get("currency") or "YER").upper()[:6]
                    if kind == "plan":
                        obj.quota = _dec(data.get("quota"))
                        obj.quota_unit = str(data.get("quota_unit") or "")
                        obj.validity_days = int(data["validity_days"]) if str(data.get("validity_days") or "").isdigit() else None
                        obj.payment_type = str(data.get("payment_type") or "")
                        obj.line_type = str(data.get("line_type") or "")
                    elif kind == "digital":
                        obj.validity_days = int(data["validity_days"]) if str(data.get("validity_days") or "").isdigit() else None
                obj.metadata = meta
                obj.save()
                return Response(_public_item(obj), status=HTTP_201_CREATED)

            if entity == "sync":
                link = ProviderLink.objects.select_related("provider").filter(pk=data.get("provider_link_id"), is_active=True, provider__is_active=True).first()
                if not link:
                    raise ValueError("الربطية غير موجودة أو غير فعالة.")
                result = sync_provider_link(link, dry_run=bool(data.get("dry_run", True)), prune=bool(data.get("prune", False)))
                return Response(result)

            return Response({"detail": "الكيان غير مدعوم."}, status=HTTP_404_NOT_FOUND)
        except (ValueError, InvalidOperation) as exc:
            return Response({"detail": str(exc)}, status=HTTP_400_BAD_REQUEST)
        except Exception as exc:
            return Response({"detail": f"تعذر حفظ العنصر: {exc}"}, status=HTTP_400_BAD_REQUEST)
