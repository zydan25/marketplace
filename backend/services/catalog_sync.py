from decimal import Decimal, InvalidOperation

from django.db import transaction

from .models import DigitalProduct, GameProduct, ProviderLink, ServiceOption, TelecomDenomination, TelecomPlan
from .provider import ProviderClient


ITEM_MODELS = {
    "service_options": ServiceOption,
    "telecom_denominations": TelecomDenomination,
    "telecom_plans": TelecomPlan,
    "game_products": GameProduct,
    "digital_products": DigitalProduct,
}


def _deep_get(value, path):
    if path in (None, "", []):
        return value
    current = value
    for key in str(path).split("."):
        if isinstance(current, dict):
            current = current.get(key)
        elif isinstance(current, list) and key.isdigit():
            index = int(key)
            current = current[index] if index < len(current) else None
        else:
            return None
    return current


def _first(row, aliases):
    for alias in aliases or []:
        if isinstance(alias, str):
            value = _deep_get(row, alias)
            if value not in (None, ""):
                return value
    return None


def _decimal(value, default=Decimal("0.00")):
    if value in (None, ""):
        return default
    try:
        return Decimal(str(value)).quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError, TypeError):
        return default


def _items_from_response(data, response_path):
    raw = _deep_get(data, response_path) if response_path else data
    if raw is None:
        return []
    if isinstance(raw, list):
        return raw
    if isinstance(raw, dict):
        for key in ("items", "data", "results", "offers", "products", "rows"):
            candidate = raw.get(key)
            if isinstance(candidate, list):
                return candidate
    return []


def _mapping(link):
    catalog = dict((link.metadata or {}).get("catalog") or {})
    fields = dict(catalog.get("fields") or {})
    defaults = {
        "name": ["name", "title", "label", "description", "num", "code"],
        "external_code": ["external_code", "code", "uniqcode", "uniq_code", "offerid", "packageid", "id"],
        "provider_num": ["provider_num", "num", "number", "offerid", "packageid"],
        "price": ["sale_price", "price", "amount", "value", "cost", "face_value"],
        "face_value": ["face_value", "value", "amount"],
        "currency": ["currency", "curr"],
        "quantity": ["quantity", "qty", "stock", "available", "units", "count"],
        "quota": ["quota", "data", "volume"],
        "quota_unit": ["quota_unit", "unit"],
        "validity_days": ["validity_days", "days", "duration"],
        "payment_type": ["payment_type", "pay_type", "payment"],
        "line_type": ["line_type", "sim_type", "type"],
        "uniqcode": ["uniqcode", "uniq_code"],
        "packageid": ["packageid", "package_id", "offerid"],
        "link_number": ["link_number", "provider_link_number", "linkid", "link_id"],
    }
    defaults.update(fields)
    return catalog, defaults


def sync_provider_link(link, *, dry_run=False, prune=False):
    if not link.is_active or not link.provider.is_active:
        raise ValueError("الربطية أو المزود غير فعال.")
    catalog, fields = _mapping(link)
    if not catalog.get("enabled", False):
        raise ValueError("هذه الربطية غير مهيأة لمزامنة كتالوج المزود.")
    service_code = str(catalog.get("service_code") or "").strip()
    item_type = str(catalog.get("item_type") or "").strip()
    response_path = catalog.get("response_path", "")
    model = ITEM_MODELS.get(item_type)
    if not service_code or not model:
        raise ValueError("إعداد الكتالوج يجب أن يحتوي service_code وitem_type صالحًا.")

    from .models import Service
    service = Service.objects.filter(code=service_code, is_active=True).first()
    if not service:
        raise ValueError(f"الخدمة {service_code} غير موجودة أو متوقفة.")

    from django.utils import timezone
    # Use a non-persisted transaction object: catalog endpoints still require a
    # valid provider transid for Sanaacash token generation, but must never create
    # a customer financial transaction.
    fake_tx = __import__("services.models", fromlist=["ServiceTransaction"]).ServiceTransaction(
        service=service, payload={}, mobile="0"
    )
    fake_tx.provider_transid = ProviderClient.new_numeric_transid(link.provider, request_kind="catalog")
    fake_tx.provider_transaction_id = str(fake_tx.provider_transid)
    fake_tx.webhook_secret_encrypted = ""
    result = ProviderClient(link.provider).call(link, fake_tx, status_check=False)
    if not result.success:
        raise RuntimeError(f"فشل جلب كتالوج المزود: {result.code} {result.description}")

    rows = _items_from_response(result.response, response_path)
    if not rows:
        raise ValueError("رد المزود لا يحتوي عناصر كتالوج قابلة للقراءة.")

    saved = 0
    disabled_unpriced = 0
    seen = set()
    with transaction.atomic():
        for row in rows:
            name = str(_first(row, fields["name"]) or "").strip()
            external_code = str(_first(row, fields["external_code"]) or "").strip()
            provider_num = str(_first(row, fields["provider_num"]) or "").strip()
            if not name or not external_code:
                continue
            price = _decimal(_first(row, fields["price"]))
            currency = str(_first(row, fields["currency"]) or service.currency).upper()[:6]
            quantity = _first(row, fields["quantity"])
            link_number = str(_first(row, fields["link_number"]) or catalog.get("provider_link_number") or "").strip()
            uniqcode = str(_first(row, fields["uniqcode"]) or "").strip()
            packageid = str(_first(row, fields["packageid"]) or "").strip()
            identity = (external_code, provider_num, name)
            seen.add(identity)
            metadata = dict(catalog.get("item_metadata") or {})
            metadata.update({
                "provider_link_id": link.pk,
                "provider_link_number": link_number,
                "provider_num": provider_num,
                "provider_uniqcode": uniqcode,
                "provider_packageid": packageid,
                "provider_quantity": None if quantity in (None, "") else str(quantity),
                "catalog_synced_at": timezone.now().isoformat(),
                "catalog_source": "provider",
            })
            if price <= 0 and service.service_kind == Service.ServiceKinds.PURCHASE and service.requires_balance:
                metadata["purchaseable"] = False
                metadata["purchase_disabled_reason"] = "المزود لم يرسل سعرًا صالحًا؛ يجب إدخال سعر بيع معتمد قبل التفعيل."
                disabled_unpriced += 1
            else:
                metadata.setdefault("purchaseable", True)

            if dry_run:
                saved += 1
                continue

            common = {"name": name, "sort_order": saved, "is_active": True, "metadata": metadata}
            if model is TelecomDenomination:
                obj, _ = model.objects.update_or_create(
                    service=service, external_code=external_code,
                    defaults={
                        **common,
                        "face_value": _decimal(_first(row, fields["face_value"]), price),
                        "sale_price": price,
                        "payment_type": str(_first(row, fields["payment_type"]) or ""),
                        "line_type": str(_first(row, fields["line_type"]) or ""),
                    },
                )
            elif model is TelecomPlan:
                obj, _ = model.objects.update_or_create(
                    service=service, external_code=external_code,
                    defaults={
                        **common,
                        "price": price,
                        "quota": _decimal(_first(row, fields["quota"]), Decimal("0")) if _first(row, fields["quota"]) not in (None, "") else None,
                        "quota_unit": str(_first(row, fields["quota_unit"]) or ""),
                        "validity_days": int(_first(row, fields["validity_days"])) if str(_first(row, fields["validity_days"]) or "").isdigit() else None,
                        "payment_type": str(_first(row, fields["payment_type"]) or ""),
                        "line_type": str(_first(row, fields["line_type"]) or ""),
                    },
                )
            elif model is ServiceOption:
                obj, _ = model.objects.update_or_create(
                    service=service, external_code=external_code, provider_num=provider_num, name=name,
                    defaults={**common, "provider_num": provider_num, "price": price, "currency": currency},
                )
            elif model is GameProduct:
                obj, _ = model.objects.update_or_create(
                    service=service, external_code=external_code,
                    defaults={**common, "price": price, "currency": currency},
                )
            else:
                obj, _ = model.objects.update_or_create(
                    service=service, external_code=external_code,
                    defaults={**common, "price": price, "currency": currency, "validity_days": int(_first(row, fields["validity_days"])) if str(_first(row, fields["validity_days"]) or "").isdigit() else None},
                )
            saved += 1

        if prune and not dry_run:
            qs = model.objects.filter(service=service, metadata__provider_link_id=link.pk)
            for obj in qs.iterator():
                meta = obj.metadata or {}
                identity = (str(getattr(obj, "external_code", "") or ""), str(meta.get("provider_num", "") or ""), str(getattr(obj, "name", "") or ""))
                if identity not in seen:
                    obj.is_active = False
                    obj.save(update_fields=["is_active"])

    return {"service": service.code, "item_type": item_type, "seen": len(rows), "saved": saved, "disabled_unpriced": disabled_unpriced, "dry_run": dry_run}
