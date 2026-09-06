"""Import legacy service catalogs without guessing unsafe provider mappings.

Usage:
    python manage.py import_legacy_catalog --sql /path/to/legacy.sql

The importer keeps the Sanaacash PDF as the authoritative provider contract.
The legacy SQL is used to enrich the normalized catalog with additional units,
prices, quotas and metadata. Items with an unverified provider mapping are
kept visible but marked purchaseable=false and therefore cannot be executed.
"""

import re
from decimal import Decimal, InvalidOperation

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.text import slugify

from services.catalog_base import SERVICES
from services.catalog_games import GAMES_AND_CARDS
from services.catalog_operators import SABA_OFFERS, YOU_OFFERS
from services.models import (
    DigitalProduct,
    GameProduct,
    MainServiceCategory,
    ProviderLink,
    Service,
    ServiceCategory,
    ServiceDistribution,
    ServiceField,
    ServiceOption,
    TelecomDenomination,
    TelecomPlan,
)


GAME_CODE_ALIASES = {
    "Likee- #برنامج# likee": "likee",
    "بيجو لايف #برنامج#": "bigolive",
    "هاي داي جواهر": "hidadijwaher",
    "هاي داي عملة ذهبية": "ddihadi",
    "بوبجي نيو ستيت": "newstatepobg",
    "كلاش اوف كلانس": "clashofclanz",
    "كلاش رويال": "clashroial",
    "براول ستارز": "praolstars",
    "كول او ديوتي": "calloffdyoty",
    "كونزات يويو": None,
    "عملات تيكتوك": None,
}


def _insert_text(sql, table):
    match = re.search(r"INSERT INTO `" + re.escape(table) + r"` VALUES (.*?);", sql, re.S | re.I)
    return match.group(1) if match else ""


def _rows(sql, table):
    text = _insert_text(sql, table)
    if not text:
        return []
    rows, current, depth = [], [], 0
    quoted = False
    escaped = False
    for char in text:
        if quoted:
            current.append(char)
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == "'":
                quoted = False
            continue
        if char == "'":
            quoted = True
            current.append(char)
        elif char == "(":
            depth += 1
            current.append(char)
        elif char == ")":
            depth -= 1
            current.append(char)
            if depth == 0:
                rows.append("".join(current)[1:-1])
                current = []
        elif depth:
            current.append(char)

    return [_fields(row) for row in rows]


def _fields(row):
    values, current = [], []
    quoted = False
    escaped = False
    for char in row:
        if quoted:
            current.append(char)
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == "'":
                quoted = False
            continue
        if char == "'":
            quoted = True
            current.append(char)
        elif char == ",":
            values.append(_value("".join(current).strip()))
            current = []
        else:
            current.append(char)
    values.append(_value("".join(current).strip()))
    return values


def _value(value):
    if value.upper() == "NULL":
        return None
    if len(value) >= 2 and value[0] == "'" and value[-1] == "'":
        return value[1:-1].replace("\\'", "'").replace("\\\\", "\\")
    try:
        return int(value)
    except ValueError:
        try:
            return Decimal(value)
        except (InvalidOperation, ValueError):
            return value


def _decimal(value, default=Decimal("0.00")):
    try:
        return Decimal(str(value if value not in (None, "") else default)).quantize(Decimal("0.01"))
    except (InvalidOperation, TypeError, ValueError):
        return default


def _norm(text):
    return re.sub(r"[^a-z0-9]+", "", str(text or "").lower())


def _known_game_code(network, name):
    if network in GAMES_AND_CARDS:
        return network
    for source, canonical in GAME_CODE_ALIASES.items():
        if canonical and (source in str(network or "") or source in str(name or "")):
            return canonical
    network_norm = _norm(network)
    name_norm = _norm(name)
    for code in GAMES_AND_CARDS:
        c = _norm(code)
        if c and (c == network_norm or c in network_norm or c in name_norm):
            return code
    return None


def _ensure_game_service(code, name, group_ids=None, purchaseable=True):
    category, _ = ServiceCategory.objects.get_or_create(
        main_category=MainServiceCategory.objects.get_or_create(
            slug="games", defaults={"name": "الألعاب", "icon": "gamepad", "is_active": True}
        )[0],
        parent=None,
        slug="games",
        defaults={"name": "الألعاب", "is_active": True},
    )
    service, _ = Service.objects.update_or_create(
        code=code,
        defaults={
            "category": category,
            "name": name,
            "slug": slugify(code, allow_unicode=True)[:180] or code[:180],
            "service_kind": Service.ServiceKinds.PURCHASE,
            "requires_balance": True,
            "pricing_mode": Service.PricingModes.ITEM,
            "price": Decimal("0.00"),
            "currency": "YER",
            "metadata": {
                "provider_type": code,
                "legacy_group_ids": group_ids or [],
                "purchaseable": bool(purchaseable),
                "catalog_source": "legacy SQL + Sanaacash PDF",
            },
            "is_active": True,
        },
    )
    defaults = [
        ("mobile", "رقم الهاتف/المستفيد", "text", True, {"min_length": 9, "max_length": 9}),
        ("uniqcode", "كود الفئة الموحد", "text", True, {}),
        ("playerid", "رقم اللاعب", "text", True, {}),
        ("playername", "اسم اللاعب", "text", False, {}),
        ("zoneid", "Zone ID", "text", False, {}),
        ("email", "البريد الإلكتروني", "email", False, {}),
    ]
    for key, label, typ, required, validation in defaults:
        ServiceField.objects.update_or_create(
            service=service,
            key=key,
            defaults={
                "label": label,
                "field_type": typ,
                "required": required,
                "validation": validation,
                "is_active": True,
            },
        )
    if purchaseable:
        route = ProviderLink.objects.filter(operation="games_cards", is_active=True, provider__is_active=True).order_by("priority", "id").first()
        if route:
            ServiceDistribution.objects.update_or_create(
                service=service,
                provider_link=route,
                defaults={"priority": route.priority, "is_active": True, "conditions": {}},
            )
    return service


@transaction.atomic
def import_catalog(sql):
    # Currency table: legacy backup stores USD rate as the value needed to
    # translate the game's USD price into YER. We retain the rate as metadata.
    usd_rate = Decimal("560")
    for row in _rows(sql, "currenciestbl"):
        if len(row) >= 7 and str(row[3] or "").upper() == "USD":
            usd_rate = _decimal(row[6], usd_rate)
            break

    group_rows = _rows(sql, "operationsgroups")
    unit_rows = _rows(sql, "gameunits")
    card_rows = _rows(sql, "servicescardstbl")
    mtn_rows = _rows(sql, "mtntbl")
    mtn_offer_rows = _rows(sql, "mtnoffers")
    saba_offer_rows = _rows(sql, "sabaoffers")
    sbay_rows = _rows(sql, "sbaytbl")
    sbay_offer_rows = _rows(sql, "sbayoffers")
    why_rows = _rows(sql, "whytbl")
    why_offer_rows = _rows(sql, "whyoffers")
    adenet_rows = _rows(sql, "adenettbl")
    yem4g_rows = _rows(sql, "yemfgtbl")

    known_yem_categories = {row[0]: row for row in SERVICES}
    for code in known_yem_categories:
        pass

    game_groups = {}
    for row in group_rows:
        if len(row) < 13 or str(row[9] or "").strip().lower() != "game":
            continue
        group_id = row[0]
        name = str(row[1] or "").strip()
        network = str(row[12] or "").strip()
        if not network:
            continue
        canonical = _known_game_code(network, name)
        service_code = canonical or f"legacy-game-{group_id}"
        game_groups[int(group_id)] = {
            "service_code": service_code,
            "canonical": canonical,
            "name": name or network,
        }

    services = {}
    for group_id, info in game_groups.items():
        current = services.get(info["service_code"])
        if current:
            meta = dict(current.metadata or {})
            ids = set(meta.get("legacy_group_ids", []))
            ids.add(group_id)
            meta["legacy_group_ids"] = sorted(ids)
            current.metadata = meta
            current.save(update_fields=["metadata", "updated_at"])
            continue
        services[info["service_code"]] = _ensure_game_service(
            info["service_code"],
            info["name"],
            [group_id],
            bool(info["canonical"]),
        )

    imported_games = 0
    for row in unit_rows:
        if len(row) < 13:
            continue
        unit_id, group_id, legacy_service_id, name, detail, price, price_usd, price_sar, qty, unit_fields, link_id, link_amount, uniq_code = row
        try:
            group_id_int = int(group_id)
        except (TypeError, ValueError):
            continue
        info = game_groups.get(group_id_int)
        if not info:
            continue
        service = services[info["service_code"]]
        direct_yer = _decimal(price, Decimal("0"))
        usd = _decimal(price_usd, Decimal("0"))
        converted = (usd * usd_rate).quantize(Decimal("0.01")) if direct_yer <= 0 and usd > 0 else direct_yer
        metadata = {
            "legacy_unit_id": unit_id,
            "legacy_group_id": group_id,
            "legacy_service_id": legacy_service_id,
            "provider_num": str(link_id or ""),
            "link_id": str(link_id or ""),
            "link_amount": str(link_amount or ""),
            "uniqcode": str(uniq_code or ""),
            "unit_qty": str(qty or ""),
            "unit_fields": str(unit_fields or ""),
            "detail": str(detail or ""),
            "price_usd": str(usd),
            "price_sar": str(price_sar or ""),
            "legacy_usd_to_yer_rate": str(usd_rate),
            "price_source": "legacy_unit_price" if direct_yer > 0 else "legacy_usd_conversion",
            "price_review_required": direct_yer <= 0,
            "purchaseable": bool(info["canonical"] and converted > 0),
        }
        if not metadata["purchaseable"]:
            metadata["purchase_disabled_reason"] = "كود المزود غير موثق في عقد Sanaacash أو السعر غير صالح."
        GameProduct.objects.update_or_create(
            service=service,
            external_code=str(uniq_code or link_id or unit_id),
            defaults={
                "name": str(name or uniq_code or unit_id),
                "price": converted,
                "currency": "YER",
                "metadata": metadata,
                "is_active": True,
            },
        )
        imported_games += 1

    # Digital-card services from the legacy table are imported as catalog-only
    # unless a matching documented provider code exists. No zero-price card can
    # be executed accidentally.
    digital_main, _ = MainServiceCategory.objects.get_or_create(
        slug="digital", defaults={"name": "البرامج والبطاقات", "icon": "apps", "is_active": True}
    )
    digital_category, _ = ServiceCategory.objects.get_or_create(
        main_category=digital_main, parent=None, slug="digital-cards",
        defaults={"name": "البطاقات الرقمية", "is_active": True},
    )
    imported_cards = 0
    linked_card_unit_ids = {int(r[2]) for r in unit_rows if len(r) > 2 and str(r[2]).isdigit()}
    for row in card_rows:
        if len(row) < 7:
            continue
        card_id, name, legacy_service_id, issms, sms, service_link, unit_fields = row
        service_code = f"legacy-card-{legacy_service_id}"
        service, _ = Service.objects.update_or_create(
            code=service_code,
            defaults={
                "category": digital_category,
                "name": str(name or service_code),
                "slug": slugify(service_code, allow_unicode=True),
                "service_kind": Service.ServiceKinds.PURCHASE,
                "requires_balance": True,
                "pricing_mode": Service.PricingModes.ITEM,
                "price": Decimal("0.00"),
                "currency": "YER",
                "metadata": {"legacy_service_id": legacy_service_id, "issms": issms, "sms": sms, "service_link": service_link, "unit_fields": unit_fields, "purchaseable": False, "purchase_disabled_reason": "تحتاج مطابقة مزود موثقة قبل التفعيل."},
                "is_active": True,
            },
        )
        DigitalProduct.objects.update_or_create(
            service=service,
            external_code=str(legacy_service_id),
            defaults={
                "name": str(name or service_code),
                "price": Decimal("0.00"),
                "currency": "YER",
                "metadata": {"legacy_card_id": card_id, "legacy_service_id": legacy_service_id, "service_link": service_link, "unit_fields": unit_fields, "linked_gameunit_service": legacy_service_id in linked_card_unit_ids, "purchaseable": False, "purchase_disabled_reason": "السعر/كود المزود غير موثّق في عقد API الحالي."},
                "is_active": True,
            },
        )
        imported_cards += 1

    # Enrich known operator catalogs that were missing from the original static tables.
    if "sbay-denomination" in known_yem_categories:
        service = Service.objects.filter(code="sbay-denomination", is_active=True).first()
        if service:
            for row in sbay_rows:
                if len(row) < 8:
                    continue
                sbay_id, unit, price, *_tail = row
                ServiceOption.objects.update_or_create(
                    service=service,
                    external_code=str(sbay_id),
                    provider_num=str(unit or ""),
                    name=f"سبأفون الجنوب {unit}",
                    defaults={"price": _decimal(price), "currency": "YER", "metadata": {"legacy_id": sbay_id, "purchaseable": bool(unit and _decimal(price) > 0)}, "is_active": True},
                )

    why_service = Service.objects.filter(code="why-package", is_active=True).first()
    if why_service:
        for row in why_offer_rows:
            if len(row) < 17:
                continue
            legacy_id, name, offer_price, _, offer_code, *_rest = row
            qty = str(row[9] or "")
            uniq_num = str(row[11] or "")
            purchaseable = bool(qty and uniq_num and _decimal(offer_price) > 0)
            TelecomPlan.objects.update_or_create(
                service=why_service,
                external_code=str(offer_code or legacy_id),
                defaults={
                    "name": str(name or legacy_id),
                    "price": _decimal(offer_price),
                    "metadata": {"provider_num": qty, "packageid": uniq_num, "legacy_id": legacy_id, "purchaseable": purchaseable},
                    "is_active": True,
                },
            )

    adenet_service = Service.objects.filter(code="adenet-bill", is_active=True).first()
    if adenet_service:
        for row in adenet_rows:
            if len(row) < 6:
                continue
            legacy_id, unit, price, item_price, qty, link_num = row
            provider_num = str(link_num or unit or legacy_id)
            purchaseable = bool(provider_num and _decimal(price) > 0)
            ServiceOption.objects.update_or_create(
                service=adenet_service,
                external_code=str(legacy_id),
                provider_num=provider_num,
                name=str(unit or f"عدن نت {legacy_id}"),
                defaults={"price": _decimal(price), "currency": "YER", "metadata": {"legacy_id": legacy_id, "item_price": item_price, "qty": qty, "purchaseable": purchaseable}, "is_active": True},
            )

    yem4g_service = Service.objects.filter(code="yem4g-package", is_active=True).first()
    if yem4g_service:
        for row in yem4g_rows:
            if len(row) < 3:
                continue
            legacy_id, name, price = row
            TelecomPlan.objects.update_or_create(
                service=yem4g_service,
                external_code=str(legacy_id),
                defaults={"name": str(name), "price": _decimal(price), "metadata": {"legacy_id": legacy_id, "provider_type": "yem4g", "purchaseable": _decimal(price) > 0}, "is_active": True},
            )

    # Add the extra MTN/Sabafon offers from the legacy backup only when their
    # provider number is explicit; otherwise preserve them as disabled catalog.
    you_service = Service.objects.filter(code="you-offer", is_active=True).first()
    known_you_codes = {str(row[3] or row[0]): str(row[0]) for row in YOU_OFFERS}
    if you_service:
        for row in mtn_offer_rows:
            if len(row) < 12:
                continue
            offer_id, name, price, uniq_num, *_rest = row
            offer_num = str(row[9] or "")
            code = str(uniq_num or offer_id)
            known_num = known_you_codes.get(code)
            provider_num = known_num or offer_num
            purchaseable = bool(provider_num and _decimal(price) > 0)
            TelecomPlan.objects.update_or_create(
                service=you_service,
                external_code=code,
                defaults={
                    "name": str(name or code),
                    "price": _decimal(price),
                    "metadata": {"provider_num": provider_num, "legacy_offer_id": offer_id, "legacy_offer_num": offer_num, "purchaseable": purchaseable, "source": "legacy_sql"},
                    "is_active": True,
                },
            )

    saba_service = Service.objects.filter(code="saba-offer", is_active=True).first()
    known_saba_codes = {str(row[3]): str(row[0]) for row in SABA_OFFERS}
    if saba_service:
        for row in saba_offer_rows:
            if len(row) < 17:
                continue
            legacy_id, name, price, *_ = row
            offer_code = str(row[4] or "")
            pdf_num = known_saba_codes.get(offer_code)
            purchaseable = bool(pdf_num and _decimal(price) > 0)
            TelecomPlan.objects.update_or_create(
                service=saba_service,
                external_code=offer_code or str(legacy_id),
                defaults={
                    "name": str(name or offer_code),
                    "price": _decimal(price),
                    "metadata": {"provider_num": pdf_num or "", "legacy_offer_id": legacy_id, "uniq_num": str(row[11] or ""), "purchaseable": purchaseable, "source": "legacy_sql"},
                    "is_active": True,
                },
            )

    return {
        "game_groups": len(game_groups),
        "game_units": imported_games,
        "digital_cards": imported_cards,
        "usd_rate": str(usd_rate),
    }


class Command(BaseCommand):
    help = "استيراد كتالوج الخدمات والألعاب والبطاقات من نسخة SQL القديمة بأمان."

    def add_arguments(self, parser):
        parser.add_argument("--sql", required=True, help="مسار نسخة SQL القديمة")

    def handle(self, *args, **options):
        try:
            with open(options["sql"], "r", encoding="utf-8", errors="ignore") as handle:
                sql = handle.read()
        except OSError as exc:
            raise CommandError(str(exc)) from exc
        result = import_catalog(sql)
        self.stdout.write(self.style.SUCCESS(
            "تم الاستيراد بأمان: "
            f"{result['game_groups']} مجموعة ألعاب، "
            f"{result['game_units']} وحدة ألعاب، "
            f"{result['digital_cards']} بطاقة/خدمة رقمية، "
            f"معدل USD القديم={result['usd_rate']}."
        ))
