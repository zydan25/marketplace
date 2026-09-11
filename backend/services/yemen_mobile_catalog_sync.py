"""Authoritative Yemen Mobile catalog sync derived from the supplied Sanaacash API PDF."""

from __future__ import annotations

import re
from decimal import Decimal

from django.db import transaction

from .catalog_yemen import YEMEN_MOBILE_OFFERS
from .models import TelecomPlan, TelecomPlanType


_ARABIC_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "01234567890123456789")


def _normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "").translate(_ARABIC_DIGITS)).strip()


def _first_number(patterns: list[str], text: str) -> Decimal | None:
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            try:
                return Decimal(match.group(1))
            except Exception:
                pass
    return None


def parse_package_details(name: str) -> dict:
    """Parse only benefits explicitly present in the API package name."""
    text = _normalize_text(name)
    internet = _first_number([
        r"(\d+(?:\.\d+)?)\s*(?:ميجابايت|ميغا(?:بايت)?)",
        r"(\d+(?:\.\d+)?)\s*MB\b",
        r"(\d+(?:\.\d+)?)\s*(?:جيجا(?:بايت)?|جيجا)\b",
        r"(\d+(?:\.\d+)?)\s*GB\b",
    ], text)
    internet_unit = None
    if internet is not None:
        if re.search(r"(?:ميجابايت|ميغا(?:بايت)?)|\bMB\b", text, flags=re.IGNORECASE):
            internet_unit = "MB"
        elif re.search(r"(?:جيجا(?:بايت)?|جيجا)|\bGB\b", text, flags=re.IGNORECASE):
            internet_unit = "GB"

    voice = _first_number([
        r"(\d+(?:\.\d+)?)\s*(?:دقيقة|دقائق|دقيقه)",
        r"(\d+(?:\.\d+)?)\s*(?:minutes?|mins?)\b",
    ], text)
    sms = _first_number([
        r"(\d+(?:\.\d+)?)\s*(?:رسالة|رسائل|رساله)",
        r"(\d+(?:\.\d+)?)\s*(?:SMS|messages?)\b",
    ], text)

    validity_days = None
    if re.search(r"10\s*(?:يوم|أيام|ايام)", text):
        validity_days = 10
    elif re.search(r"30\s*(?:يوم|أيام|ايام)", text):
        validity_days = 30
    elif re.search(r"(?:يومي|اليومي|اليومية|يومية)\b", text):
        validity_days = 1
    elif re.search(r"(?:أسبوع|اسبوع|الأسبوع|الاسبوع|أسبوعية|اسبوعية)\b", text):
        validity_days = 7
    elif re.search(r"(?:شهر|شهرية|الشهرية|الشهريه|شهريه)\b", text):
        validity_days = 30

    technology = None
    if re.search(r"\b4G\b|فورجي|LTE", text, flags=re.IGNORECASE):
        technology = "4G"
    elif re.search(r"\b3G\b|3\(G\)", text, flags=re.IGNORECASE):
        technology = "3G"
    elif re.search(r"VOLTE", text, flags=re.IGNORECASE):
        technology = "VoLTE"

    return {
        "internet_amount": str(internet) if internet is not None else None,
        "internet_unit": internet_unit,
        "voice_minutes": str(voice) if voice is not None else None,
        "sms_count": str(sms) if sms is not None else None,
        "validity_days": validity_days,
        "technology": technology,
    }


def _normalize_payment_type(value: str) -> str:
    text = _normalize_text(value).lower()
    if text in {"paid", "postpaid", "فوترة"}:
        return "postpaid"
    if text in {"prepaid", "دفع مسبق"}:
        return "prepaid"
    return text


def _plan_metadata(code: str, name: str, payment_type: str, line_type: str, details: dict) -> dict:
    return {
        "catalog_source": "api 1 (59).pdf",
        "catalog_authority": "Sanaacash API PDF",
        "exact_api_code": code,
        "provider_offer_code": code,
        "purchaseable": True,
        "provider_operation": "offeryem",
        "api_payment_type": payment_type,
        "api_line_type": line_type,
        "benefits": details,
    }


@transaction.atomic
def sync_yemen_mobile_catalog(service):
    """Deactivate legacy rows, then upsert only exact API source rows."""
    # Do not delete existing TelecomPlan records: historical transactions can
    # still carry their item_id. We only make the authoritative source rows active.
    TelecomPlan.objects.filter(service=service).update(is_active=False)
    TelecomPlanType.objects.filter(service=service).update(is_active=False)

    created_or_updated = 0
    source_codes = set()
    for index, (raw_code, raw_price, raw_name, raw_payment, raw_line) in enumerate(YEMEN_MOBILE_OFFERS):
        code = str(raw_code).strip()
        source_codes.add(code)
        price = Decimal(str(raw_price))
        if price <= 0:
            raise ValueError(f"مصدر API يحتوي سعرًا غير صالح للباقة {code}: {price}")
        name = str(raw_name).strip()
        payment_type = _normalize_payment_type(raw_payment)
        line_type = str(raw_line or "").strip()
        details = parse_package_details(name)
        quota = Decimal(details["internet_amount"]) if details["internet_amount"] is not None else None
        defaults = {
            "name": name,
            "price": price,
            "quota": quota,
            "quota_unit": details["internet_unit"] or "",
            "validity_days": details["validity_days"],
            "payment_type": payment_type,
            "line_type": line_type,
            "metadata": _plan_metadata(code, name, payment_type, line_type, details),
            "sort_order": index,
            "is_active": True,
        }
        TelecomPlan.objects.update_or_create(service=service, external_code=code, defaults=defaults)
        created_or_updated += 1

    # Create the minimal source-backed root taxonomy. Existing custom categories
    # remain in DB but are inactive until an administrator re-enables them.
    roots = {}
    for code, name in (("3g", "باقات 3G"), ("4g", "باقات 4G"), ("other", "باقات أخرى")):
        roots[code], _ = TelecomPlanType.objects.update_or_create(
            service=service,
            code=code,
            defaults={
                "name": name,
                "description": "تصنيف أولي مبني على نوع التقنية الظاهر في اسم الباقة من عقد API.",
                "parent": None,
                "is_active": True,
            },
        )
        roots[code].plans.clear()

    for plan in TelecomPlan.objects.filter(service=service, is_active=True):
        technology = (plan.metadata or {}).get("benefits", {}).get("technology")
        target = roots["4g" if technology == "4G" else "3g" if technology == "3G" else "other"]
        target.plans.add(plan)

    return {
        "created_plans": created_or_updated,
        "expected_source_rows": len(YEMEN_MOBILE_OFFERS),
        "source_codes": sorted(source_codes),
        "zero_price": 0,
    }
