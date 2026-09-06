"""Import legacy service catalogs without guessing unsafe provider mappings."""

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
    network = str(network or "").strip()
    name = str(name or "").strip()
    if network in GAMES_AND_CARDS:
        return network
    if name in GAME_CODE_ALIASES:
        return GAME_CODE_ALIASES[name]
    for source, canonical in GAME_CODE_ALIASES.items():
        if source.lower() in network.lower() or source.lower() in name.lower():
            return canonical
    network_norm = _norm(network)
    name_norm = _norm(name)
    for code in GAMES_AND_CARDS:
        normalized = _norm(code)
        if normalized and (normalized == network_norm or normalized in network_norm or normalized in name_norm):
            return code
    return None


def _ensure_game_service(code, name, group_ids=None, purchaseable=True):
    main, _ = MainServiceCategory.objects.get_or_create(
        slug="games", defaults={"name": "الألعاب", "icon": "gamepad", "is_active": True}
    )
    category, _ = ServiceCategory.objects.get_or_create(
        main_category=main, parent=None, slug="games",
        defaults={"name": "الألعاب", "is_active": True},
    )
    service = Service.objects.filter(code=code).first()
    if service is None:
        service = Service.objects.create(
            code=code,
            category=category,
            name=name,
            slug=slugify(code, allow_unicode=True)[:180] or code[:180],
            service_kind=Service.ServiceKinds.PURCHASE,
            requires_balance=True,
            pricing_mode=Service.PricingModes.ITEM,
            price=Decimal("0.00"),
            currency="YER",
            is_active=True,
        )
    meta = dict(service.metadata or {})
    ids = set(meta.get("legacy_group_ids", []))
    ids.update(group_ids or [])
    meta.update({
        "provider_type": code,
        "legacy_group_ids": sorted(ids),
        "purchaseable": bool(purchaseable),
        "catalog_source": "legacy SQL + Sanaacash PDF",
    })
    service.metadata = meta
    if not service.category_id:
        service.category = category
    service.save(update_fields=["metadata", "category", "updated_at"] if hasattr(service, "updated_at") else ["metadata", "category"])
    fields = [
        ("mobile", "رقم الهاتف/المستفيد", "text", True, {"min_length": 9, "max_length": 9}, 10),
        ("uniqcode", "كود الفئة الموحد", "text", True, {}, 20),
        ("playerid", "رقم اللاعب", "text", True, {}, 30),
        ("playername", "اسم اللاعب", "text", False, {}, 40),
        ("zoneid", "Zone ID", "text", False, {}, 50),
        ("email", "البريد الإلكتروني", "email", False, {}, 60),
    ]
    for key, label, typ, required, validation, order in fields:
        ServiceField.objects.update_or_create(
            service=service, key=key,
            defaults={"label": label, "field_type": typ, "required": required, "validation": validation, "sort_order": order, "is_active": True},
        )
    if purchaseable:
        route = ProviderLink.objects.filter(
            operation="games_cards", is_active=True, provider__is_active=True
        ).order_by("priority", "id").first()
        if route:
            ServiceDistribution.objects.update_or_create(
                service=service, provider_link=route,
                defaults={"priority": route.priority, "is_active": True, "conditions": {}},
            )
    return service


def _upsert_game_unit(service, row, usd_rate):
    unit_id, group_id, legacy_service_id, name, detail, price, price_usd, price_sar, qty, unit_fields, link_id, link_amount, uniq_code = row[:13]
    direct_yer = _decimal(price)
    usd = _decimal(price_usd)
    converted = (usd * usd_rate).quantize(Decimal("0.01")) if direct_yer <= 0 and usd > 0 else direct_yer
    info = dict(service.metadata or {})
    canonical = bool(info.get("provider_type")) and not str(info.get("provider_type")).startswith("legacy-game-")
    purchaseable = bool(canonical and converted > 0 and uniq_code)
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
        "purchaseable": purchaseable,
    }
    if not purchaseable:
        metadata["purchase_disabled_reason"] = "كود الخدمة غير موثق في عقد Sanaacash الحالي أو بيانات السعر/uniqcode غير صالحة."
    return GameProduct.objects.update_or_create(
        service=service,
        external_code=f"legacy-{unit_id}",
        defaults={
            "name": str(name or uniq_code or unit_id),
            "price": converted,
            "currency": "YER",
            "metadata": metadata,
            "is_active": True,
        },
    )


@transaction.atomic
def import_catalog(sql):
    usd_rate = Decimal("560")
    for row in _rows(sql, "currenciestbl"):
        if len(row) >= 7 and str(row[3] or "").upper() == "USD":
            usd_rate = _decimal(row[6], usd_rate)
            break

    group_rows = _rows(sql, "operationsgroups")
    unit_rows = _rows(sql, "gameunits")
    card_rows = _rows(sql, "servicescardstbl")
    mtn_offer_rows = _rows(sql, "mtnoffers")
    saba_offer_rows = _rows(sql, "sabaoffers")
    sbay_rows = _rows(sql, "sbaytbl")
    sbay_offer_rows = _rows(sql, "sbayoffers")
    why_rows = _rows(sql, "whytbl")
    why_offer_rows = _rows(sql, "whyoffers")
    adenet_rows = _rows(sql, "adenettbl")
    yem4g_rows = _rows(sql, "yemfgtbl")

    existing_services = {code: Service.objects.filter(code=code, is_active=True).first() for code, *_ in SERVICES}
    existing_services = {k: v for k, v in existing_services.items() if v}

    game_groups = {}
    for row in group_rows:
        if len(row) < 13 or str(row[9] or "").strip().lower() != "game":
            continue
        group_id, name, *_rest = row
        network = str(row[12] or "").strip()
        if not network:
            continue
        canonical = _known_game_code(network, name)
        game_groups[int(group_id)] = {"service_code": canonical or f"legacy-game-{group_id}", "canonical": canonical, "name": str(name or network)}

    game_services = {}
    for group_id, info in game_groups.items():
        if info["service_code"] not in game_services:
            game_services[info["service_code"]] = _ensure_game_service(info["service_code"], info["name"], [group_id], bool(info["canonical"]))
        else:
            service = game_services[info["service_code"]]
            meta = dict(service.metadata or {})
            ids = set(meta.get("legacy_group_ids", [])); ids.add(group_id)
            service.metadata = {**meta, "legacy_group_ids": sorted(ids)}
            service.save(update_fields=["metadata", "updated_at"])

    imported_games = 0
    for row in unit_rows:
        if len(row) < 13:
            continue
        info = game_groups.get(int(row[1])) if str(row[1]).isdigit() else None
        if not info:
            continue
        _upsert_game_unit(game_services[info["service_code"]], row, usd_rate)
        imported_games += 1

    # Legacy digital-card registry. It is deliberately catalog-only until its
    # provider type and price are present in the documented API contract.
    digital_main, _ = MainServiceCategory.objects.get_or_create(
        slug="digital", defaults={"name": "البرامج والبطاقات", "icon": "apps", "is_active": True}
    )
    digital_category, _ = ServiceCategory.objects.get_or_create(
        main_category=digital_main, parent=None, slug="digital-cards",
        defaults={"name": "البطاقات الرقمية", "is_active": True},
    )
    imported_cards = 0
    for row in card_rows:
        if len(row) < 7:
            continue
        card_id, name, legacy_service_id, issms, sms, service_link, unit_fields = row
        known_code = None
        low_name = str(name or "").lower()
        aliases = {
            "razer": "razergold", "itunes": "appstore", "playstation network بلاي استيشن امريكي": "plastationusa",
            "playstation network ksa": "plastationsar", "crossfire": "crossfire", "مستر كارد": "mastercard",
        }
        for needle, code in aliases.items():
            if needle in low_name:
                known_code = code
                break
        target_service = Service.objects.filter(code=known_code).first() if known_code else None
        if target_service is None:
            target_service, _ = Service.objects.update_or_create(
                code=f"legacy-card-{legacy_service_id}",
                defaults={
                    "category": digital_category,
                    "name": str(name or f"بطاقة {legacy_service_id}"),
                    "slug": slugify(f"legacy-card-{legacy_service_id}", allow_unicode=True),
                    "service_kind": Service.ServiceKinds.PURCHASE,
                    "requires_balance": True,
                    "pricing_mode": Service.PricingModes.ITEM,
                    "price": Decimal("0.00"),
                    "currency": "YER",
                    "metadata": {"legacy_service_id": legacy_service_id, "purchaseable": False, "purchase_disabled_reason": "العقد الحالي لا يوفر سعرًا وكود مزود موثوقًا لهذه البطاقة."},
                    "is_active": True,
                },
            )
        DigitalProduct.objects.update_or_create(
            service=target_service,
            external_code=f"legacy-card-{card_id}",
            defaults={
                "name": str(name or legacy_service_id),
                "price": Decimal("0.00"),
                "currency": "YER",
                "metadata": {"legacy_card_id": card_id, "legacy_service_id": legacy_service_id, "service_link": service_link, "unit_fields": unit_fields, "issms": issms, "sms": sms, "purchaseable": False, "purchase_disabled_reason": "لا يوجد سعر/ربط تنفيذ موثق في عقد API الحالي."},
                "is_active": True,
            },
        )
        imported_cards += 1

    # Missing operator catalogs: these values are present in the legacy backup
    # but are not embedded in catalog_operators.py. Only documented parameter
    # mappings are made executable.
    sbay_denom_service = Service.objects.filter(code="sbay-denomination", is_active=True).first()
    if sbay_denom_service:
        for row in sbay_rows:
            if len(row) < 3:
                continue
            legacy_id, unit, price = row[:3]
            ServiceOption.objects.update_or_create(
                service=sbay_denom_service,
                external_code=str(legacy_id),
                provider_num=str(unit or ""),
                name=f"سبأفون الجنوب {unit}",
                defaults={"price": _decimal(price), "currency": "YER", "metadata": {"legacy_id": legacy_id, "purchaseable": bool(unit and _decimal(price) > 0)}, "is_active": True},
            )

    sbay_offer_service = Service.objects.filter(code="sbay-offer", is_active=True).first()
    if sbay_offer_service:
        for row in sbay_offer_rows:
            if len(row) < 4:
                continue
            legacy_id, name, price, offer_code = row[:4]
            # The PDF explicitly says the provider num comes from a separate
            # table. Do not guess it from offer_code.
            TelecomPlan.objects.update_or_create(
                service=sbay_offer_service,
                external_code=str(offer_code or legacy_id),
                defaults={"name": str(name or offer_code), "price": _decimal(price), "metadata": {"legacy_id": legacy_id, "provider_num": "", "purchaseable": False, "purchase_disabled_reason": "رقم المزود لهذه الباقة غير موجود في عقد API الموثق."}, "is_active": True},
            )

    why_bill_service = Service.objects.filter(code="why-bill", is_active=True).first()
    if why_bill_service:
        for row in why_rows:
            if len(row) < 3:
                continue
            legacy_id, amount, price = row[:3]
            ServiceOption.objects.update_or_create(
                service=why_bill_service,
                external_code=str(legacy_id),
                provider_num=str(legacy_id),
                name=f"واي {amount}",
                defaults={"price": _decimal(price), "currency": "YER", "metadata": {"legacy_id": legacy_id, "provider_num": str(legacy_id), "purchaseable": _decimal(price) > 0}, "is_active": True},
            )

    why_package_service = Service.objects.filter(code="why-package", is_active=True).first()
    if why_package_service:
        for row in why_offer_rows:
            if len(row) < 17:
                continue
            legacy_id, name, offer_price, _isrobot, offer_code = row[:5]
            qty = str(row[9] or "")
            uniq_num = str(row[11] or "")
            purchaseable = bool(qty and uniq_num and _decimal(offer_price) > 0)
            TelecomPlan.objects.update_or_create(
                service=why_package_service,
                external_code=str(offer_code or legacy_id),
                defaults={"name": str(name or legacy_id), "price": _decimal(offer_price), "metadata": {"provider_num": qty, "packageid": uniq_num, "legacy_id": legacy_id, "purchaseable": purchaseable}, "is_active": True},
            )

    adenet_service = Service.objects.filter(code="adenet-bill", is_active=True).first()
    if adenet_service:
        for row in adenet_rows:
            if len(row) < 6:
                continue
            legacy_id, unit, price, item_price, qty, link_num = row[:6]
            provider_num = str(link_num or unit or legacy_id)
            ServiceOption.objects.update_or_create(
                service=adenet_service,
                external_code=str(legacy_id),
                provider_num=provider_num,
                name=str(unit or f"عدن نت {legacy_id}"),
                defaults={"price": _decimal(price), "currency": "YER", "metadata": {"legacy_id": legacy_id, "item_price": item_price, "qty": qty, "purchaseable": bool(provider_num and _decimal(price) > 0)}, "is_active": True},
            )

    yem4g_service = Service.objects.filter(code="yem4g-package", is_active=True).first()
    if yem4g_service:
        for row in yem4g_rows:
            if len(row) < 3:
                continue
            legacy_id, name, price = row[:3]
            TelecomPlan.objects.update_or_create(
                service=yem4g_service,
                external_code=str(legacy_id),
                defaults={"name": str(name), "price": _decimal(price), "metadata": {"legacy_id": legacy_id, "provider_type": "yem4g", "purchaseable": _decimal(price) > 0}, "is_active": True},
            )

    # Enrich You offers but keep the PDF contract price for known rows. Extra
    # legacy rows get the explicit legacy offer_num only when present.
    you_service = Service.objects.filter(code="you-offer", is_active=True).first()
    known_you = {str(row[3] or row[0]): (str(row[0]), _decimal(row[2])) for row in YOU_OFFERS}
    if you_service:
        for row in mtn_offer_rows:
            if len(row) < 12:
                continue
            offer_id, name, price, uniq_num = row[:4]
            offer_num = str(row[9] or "")
            code = str(uniq_num or offer_id)
            if code in known_you:
                continue
            purchaseable = bool(offer_num and _decimal(price) > 0)
            TelecomPlan.objects.update_or_create(
                service=you_service, external_code=code,
                defaults={"name": str(name or code), "price": _decimal(price), "metadata": {"provider_num": offer_num, "legacy_offer_id": offer_id, "legacy_offer_num": offer_num, "purchaseable": purchaseable, "source": "legacy_sql"}, "is_active": True},
            )

    saba_service = Service.objects.filter(code="saba-offer", is_active=True).first()
    known_saba = {str(row[3]): str(row[0]) for row in SABA_OFFERS}
    if saba_service:
        for row in saba_offer_rows:
            if len(row) < 12:
                continue
            legacy_id, name, price = row[:3]
            offer_code = str(row[4] or "")
            if offer_code in known_saba:
                continue
            TelecomPlan.objects.update_or_create(
                service=saba_service, external_code=offer_code or str(legacy_id),
                defaults={"name": str(name or offer_code), "price": _decimal(price), "metadata": {"provider_num": "", "legacy_offer_id": legacy_id, "uniq_num": str(row[11] or ""), "purchaseable": False, "purchase_disabled_reason": "رقم مزود الباقة غير موثق في عقد API الحالي.", "source": "legacy_sql"}, "is_active": True},
            )

    return {"game_groups": len(game_groups), "game_units": imported_games, "digital_cards": imported_cards, "usd_rate": str(usd_rate)}


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
            f"تم الاستيراد بأمان: {result['game_groups']} مجموعة ألعاب، {result['game_units']} وحدة ألعاب، "
            f"{result['digital_cards']} بطاقة/خدمة رقمية، معدل USD القديم={result['usd_rate']}."
        ))
