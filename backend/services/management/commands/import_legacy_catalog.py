"""Import legacy service/game catalog data into the normalized service platform.

Usage:
    python manage.py import_legacy_catalog --sql /path/to/legacy.sql

The importer intentionally keeps provider identifiers in metadata so the new
API can expose a stable internal item id while still sending the exact legacy
provider values (num, uniqcode, link_id, unit_fields, etc.).
"""

import re
from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.text import slugify

from services.models import GameProduct, DigitalProduct, MainServiceCategory, Service, ServiceCategory


GAME_CATEGORY = "games"
DIGITAL_CATEGORY = "digital-cards"


def _insert_text(sql, table):
    match = re.search(r"INSERT INTO `" + re.escape(table) + r"` VALUES (.*?);", sql, re.S | re.I)
    if not match:
        return ""
    return match.group(1)


def _tuples(text):
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
        except Exception:
            return value


def _safe_code(value, fallback):
    code = str(value or "").strip()
    return code[:80] or fallback


@transaction.atomic
def import_catalog(sql):
    groups = _tuples(_insert_text(sql, "operationsgroups"))
    units = _tuples(_insert_text(sql, "gameunits"))
    cards = _tuples(_insert_text(sql, "servicescardstbl"))

    main, _ = MainServiceCategory.objects.get_or_create(
        slug="services",
        defaults={"name": "الخدمات", "icon": "apps", "is_active": True},
    )
    game_category, _ = ServiceCategory.objects.get_or_create(
        main_category=main,
        parent=None,
        slug=GAME_CATEGORY,
        defaults={"name": "الألعاب", "is_active": True},
    )
    digital_category, _ = ServiceCategory.objects.get_or_create(
        main_category=main,
        parent=None,
        slug=DIGITAL_CATEGORY,
        defaults={"name": "البطاقات الرقمية", "is_active": True},
    )

    game_services = {}
    group_by_id = {}
    for row in groups:
        if len(row) < 13 or str(row[9] or "") != "game":
            continue
        group_id, name, _, orderin, *_ = row
        game_network = str(row[12] or "").strip()
        if not game_network:
            continue
        code = _safe_code(game_network, f"legacy-game-{group_id}")
        service, _ = Service.objects.update_or_create(
            code=code,
            defaults={
                "category": game_category,
                "name": str(name or game_network),
                "slug": slugify(code, allow_unicode=True)[:180] or f"game-{group_id}",
                "service_kind": Service.ServiceKinds.PURCHASE,
                "requires_balance": True,
                "pricing_mode": Service.PricingModes.ITEM,
                "price": Decimal("0.00"),
                "currency": "YER",
                "request_schema": {"type": "object", "async": True},
                "metadata": {"legacy_group_id": group_id, "legacy_group_network": row[9], "provider_type": game_network},
                "is_active": True,
            },
        )
        game_services[int(group_id)] = service
        group_by_id[int(group_id)] = row

    imported_games = 0
    for row in units:
        if len(row) < 13:
            continue
        unit_id, group_id, service_id, name, detail, price, price_usd, price_sar, qty, fields, link_id, link_amount, uniq_code = row
        service = game_services.get(int(group_id)) if str(group_id).isdigit() else None
        if not service:
            continue
        external_code = str(uniq_code or link_id or unit_id)
        try:
            amount = Decimal(str(price or "0"))
            if amount <= 0 and price_usd:
                amount = Decimal(str(price_usd))
        except Exception:
            amount = Decimal("0")
        GameProduct.objects.update_or_create(
            service=service,
            external_code=external_code,
            defaults={
                "name": str(name or external_code),
                "price": amount,
                "currency": "YER",
                "metadata": {
                    "legacy_unit_id": unit_id,
                    "legacy_group_id": group_id,
                    "legacy_service_id": service_id,
                    "provider_num": str(link_id or ""),
                    "link_id": str(link_id or ""),
                    "link_amount": str(link_amount or ""),
                    "uniqcode": str(uniq_code or ""),
                    "unit_qty": str(qty or ""),
                    "unit_fields": str(fields or ""),
                    "detail": str(detail or ""),
                    "price_usd": str(price_usd or ""),
                    "price_sar": str(price_sar or ""),
                },
                "is_active": True,
            },
        )
        imported_games += 1

    imported_cards = 0
    # The legacy digital-card table contains the service ids; actual provider
    # pricing/units can be imported separately when their source table exists.
    for row in cards:
        if len(row) < 7:
            continue
        _, name, legacy_service_id, issms, sms, service_link, unit_fields = row
        code = _safe_code(f"legacy-card-{legacy_service_id}", f"legacy-card-{legacy_service_id}")
        service, _ = Service.objects.update_or_create(
            code=code,
            defaults={
                "category": digital_category,
                "name": str(name or code),
                "slug": slugify(code, allow_unicode=True)[:180],
                "service_kind": Service.ServiceKinds.PURCHASE,
                "requires_balance": True,
                "pricing_mode": Service.PricingModes.ITEM,
                "currency": "YER",
                "metadata": {"legacy_service_id": legacy_service_id, "issms": issms, "sms": sms, "service_link": service_link, "unit_fields": unit_fields},
                "is_active": True,
            },
        )
        DigitalProduct.objects.update_or_create(
            service=service,
            external_code=str(legacy_service_id),
            defaults={
                "name": str(name or code),
                "price": Decimal("0.00"),
                "currency": "YER",
                "metadata": {"legacy_service_id": legacy_service_id, "service_link": service_link, "unit_fields": unit_fields},
                "is_active": True,
            },
        )
        imported_cards += 1

    return len(game_services), imported_games, imported_cards


class Command(BaseCommand):
    help = "استيراد الألعاب والبطاقات من نسخة قاعدة النظام القديم إلى منصة الخدمات الجديدة."

    def add_arguments(self, parser):
        parser.add_argument("--sql", required=True, help="مسار نسخة SQL القديمة")

    def handle(self, *args, **options):
        try:
            with open(options["sql"], "r", encoding="utf-8", errors="ignore") as handle:
                sql = handle.read()
        except OSError as exc:
            raise CommandError(str(exc)) from exc
        games, units, cards = import_catalog(sql)
        self.stdout.write(self.style.SUCCESS(f"تم الاستيراد: {games} خدمة لعبة، {units} وحدة لعبة، {cards} بطاقة/خدمة رقمية."))
