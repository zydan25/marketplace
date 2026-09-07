"""Import service/catalog data from the legacy MySQL dump without importing credentials.

Usage:
    python manage.py import_legacy_services /path/to/backup.sql
    python manage.py import_legacy_services /path/to/backup.sql.zip --dry-run

The importer is deliberately catalog-focused. Financial/accounting/customer
history stays in the platform's existing Django models instead of being copied
into unrelated service tables. Every imported legacy row keeps its original
identity and source fields in ``metadata`` so no provider mapping is guessed.
"""

from __future__ import annotations

import csv
import io
import re
import zipfile
from decimal import Decimal, InvalidOperation
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.text import slugify

from services.models import (
    GameProduct,
    MainServiceCategory,
    Service,
    ServiceCategory,
    ServiceOption,
    TelecomDenomination,
    TelecomPlan,
)
from services.catalog_base import SERVICES
from services.catalog_yemen_contract import canonical_yemen_mobile_offer_code
from services.management.commands.provision_sanaacash import provision


GAME_CODES = {row[0] for row in SERVICES if row[5] == "games_cards"}
SUPPORTED_GAME_GROUPS = {
    "pubg", "freefire", "legends", "loardstelmble", "clashroial", "genshmbacket",
    "clashofclanz", "newstatepobg", "praolstars", "hidadijwaher", "ddihadi",
    "calloffdyoty", "pompitch", "googleplayusa", "googleplaykorea", "appstore",
    "beinconnect", "razergold", "crossfire", "plastationusa", "plastationsar",
    "visacard", "mastercard", "likee", "bigolive",
}


def _open_dump(path: Path):
    if path.suffix.lower() == ".zip":
        zf = zipfile.ZipFile(path)
        sql_names = [name for name in zf.namelist() if name.lower().endswith((".sql", ".dump")) or name == "-"]
        if not sql_names:
            raise CommandError("الملف المضغوط لا يحتوي ملف SQL.")
        return io.TextIOWrapper(zf.open(sql_names[0], "r"), encoding="utf-8", errors="replace"), zf
    return path.open("r", encoding="utf-8", errors="replace"), None


def _sql_statements(text: str, prefix: str):
    start = 0
    while True:
        pos = text.find(prefix, start)
        if pos < 0:
            return
        quote = None
        escaped = False
        i = pos
        while i < len(text):
            ch = text[i]
            if quote:
                if escaped:
                    escaped = False
                elif ch == "\\":
                    escaped = True
                elif ch == quote:
                    quote = None
            elif ch in ("'", '"'):
                quote = ch
            elif ch == ";":
                yield text[pos : i + 1]
                start = i + 1
                break
            i += 1
        else:
            return


def _split_rows(values_sql: str):
    rows, current = [], []
    quote = None
    escaped = False
    depth = 0
    token = []
    for ch in values_sql:
        if quote:
            token.append(ch)
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == quote:
                quote = None
            continue
        if ch in ("'", '"'):
            quote = ch
            token.append(ch)
        elif ch == "(":
            depth += 1
            if depth > 1:
                token.append(ch)
        elif ch == ")":
            depth -= 1
            if depth == 0:
                current.append("".join(token).strip())
                token = []
                rows.append(current)
                current = []
            else:
                token.append(ch)
        elif ch == "," and depth == 1:
            current.append("".join(token).strip())
            token = []
        elif depth:
            token.append(ch)
    return rows


def _sql_value(raw):
    value = raw.strip()
    if value.upper() == "NULL":
        return None
    if len(value) >= 2 and value[0] == "'" and value[-1] == "'":
        body = value[1:-1]
        return bytes(body, "utf-8").decode("unicode_escape") if "\\" in body else body
    return value


def _tables(text: str):
    result = {}
    for match in re.finditer(r"CREATE TABLE `([^`]+)`\s*\((.*?)\) ENGINE=", text, re.S):
        cols = re.findall(r"^\s*`([^`]+)`\s+", match.group(2), re.M)
        result[match.group(1)] = cols
    return result


def _read_table(text: str, table: str, columns: list[str]):
    prefix = f"INSERT INTO `{table}`"
    for statement in _sql_statements(text, prefix):
        m = re.search(r"\bVALUES\s+(.*);\s*$", statement, re.S)
        if not m:
            continue
        for row in _split_rows(m.group(1)):
            if len(row) != len(columns):
                continue
            yield {columns[i]: _sql_value(row[i]) for i in range(len(columns))}


def _decimal(value, default=Decimal("0")):
    try:
        if value in (None, "", "NULL"):
            return default
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return default


def _first(row, *names, default=None):
    for name in names:
        value = row.get(name)
        if value not in (None, ""):
            return value
    return default


def _ensure_legacy_category(main: MainServiceCategory, slug: str, name: str):
    return ServiceCategory.objects.update_or_create(
        main_category=main,
        parent=None,
        slug=slugify(slug, allow_unicode=True),
        defaults={"name": name[:200], "is_active": True},
    )[0]


def _ensure_legacy_service(category, *, code, name, kind="catalog", pricing="item", metadata=None):
    return Service.objects.update_or_create(
        code=code[:100],
        defaults={
            "category": category,
            "name": name[:200],
            "slug": slugify(code, allow_unicode=True),
            "description": "مستورد من النسخة الاحتياطية القديمة؛ يحتاج ربط API مستقل قبل التنفيذ."[:2000],
            "service_kind": kind,
            "requires_balance": False,
            "pricing_mode": pricing,
            "price": Decimal("0"),
            "currency": "YER",
            "metadata": {**(metadata or {}), "legacy_only": True, "provider_supported": False},
            "is_active": True,
        },
    )[0]


class Command(BaseCommand):
    help = "استيراد كتالوجات الخدمات والمنتجات من نسخة MySQL الاحتياطية مع الحفاظ على هوية البيانات."

    def add_arguments(self, parser):
        parser.add_argument("dump", help="مسار ملف .sql أو .zip")
        parser.add_argument("--dry-run", action="store_true")

    @transaction.atomic
    def handle(self, *args, **options):
        path = Path(options["dump"]).expanduser()
        if not path.exists():
            raise CommandError(f"ملف النسخة الاحتياطية غير موجود: {path}")

        stream, archive = _open_dump(path)
        try:
            text = stream.read()
        finally:
            stream.close()
            if archive:
                archive.close()

        schema = _tables(text)
        required = {"gameunits", "operationsgroups", "mtnoffers", "sabaoffers", "sbayoffers", "whytbl", "adenettbl", "yemfgtbl"}
        missing = sorted(required - set(schema))
        if missing:
            raise CommandError("جداول مطلوبة غير موجودة في النسخة: " + ", ".join(missing))

        _, categories, services = provision()
        main_games = MainServiceCategory.objects.get(slug="games")
        main_payments = MainServiceCategory.objects.get(slug__in=["payments", "التسديدات"]).pk
        main_payments = MainServiceCategory.objects.get(pk=main_payments)
        summary = {}

        def save_count(name, count):
            summary[name] = count

        # Games/cards: preserve every gameunit row, including USD/SAR prices,
        # quantity, required fields, upstream link and uniq_code.
        group_rows = {str(r.get("id")): r for r in _read_table(text, "operationsgroups", schema["operationsgroups"])}
        game_count = 0
        for row in _read_table(text, "gameunits", schema["gameunits"]):
            group = group_rows.get(str(row.get("group_id"))) or {}
            code = str(_first(group, "game_network", default="")).strip().lower()
            if not code:
                code = f"legacy-game-group-{row.get('group_id')}"
            if code in services:
                service = services[code]
            else:
                service = _ensure_legacy_service(
                    _ensure_legacy_category(main_games, f"legacy-{row.get('group_id')}", str(_first(group, "group_name", default="ألعاب قديمة"))),
                    code=f"legacy-{code}",
                    name=str(_first(group, "group_name", default=row.get("unit_name") or code)),
                    metadata={"legacy_group_id": row.get("group_id"), "legacy_game_code": code},
                )
            external_code = str(_first(row, "uniq_code", default="") or row.get("id") or "").strip()
            metadata = {
                "legacy_id": row.get("id"),
                "legacy_group_id": row.get("group_id"),
                "legacy_service_id": row.get("service_id"),
                "unit_detail": row.get("unit_detail") or "",
                "unit_price_usd": row.get("unit_price_usd") or "",
                "unit_price_sar": row.get("unit_price_sar") or "",
                "unit_qty": row.get("unit_qty") or "",
                "unit_fields": row.get("unit_fields") or "",
                "provider_link_id": row.get("link_id") or "",
                "provider_link_amount": row.get("link_amount") or "",
                "uniqcode": row.get("uniq_code") or "",
                "catalog_source": "legacy database backup",
            }
            GameProduct.objects.update_or_create(
                service=service,
                external_code=external_code,
                defaults={
                    "name": str(row.get("unit_name") or external_code)[:200],
                    "price": _decimal(row.get("unit_price")),
                    "currency": "YER",
                    "metadata": metadata,
                    "is_active": True,
                },
            )
            game_count += 1
        save_count("gameunits", game_count)

        def import_option_table(table, service_code, code_names, name_names, price_names, extra=None):
            service = services.get(service_code)
            if not service:
                return 0
            count = 0
            for row in _read_table(text, table, schema[table]):
                code = str(_first(row, *code_names, default=row.get("id") or "")).strip()
                name = str(_first(row, *name_names, default=code)).strip()
                price = _decimal(_first(row, *price_names, default="0"))
                meta = {"legacy_id": row.get("id"), "catalog_source": "legacy database backup"}
                if extra:
                    meta.update({k: row.get(v) for k, v in extra.items()})
                ServiceOption.objects.update_or_create(
                    service=service,
                    external_code=code,
                    provider_num=str(_first(row, "offer_num", "uniq_num", "offer_code", "unit", "num", default="")),
                    name=name[:200],
                    defaults={"price": price, "currency": "YER", "metadata": meta, "is_active": True},
                )
                count += 1
            return count

        save_count("mtnoffers", import_option_table("mtnoffers", "you-offer", ("code", "uniq_num", "offer_num", "id"), ("offer_name", "name", "id"), ("offer_price", "item_price", "price", "id")))
        save_count("sabaoffers", import_option_table("sabaoffers", "saba-offer", ("offer_code", "code", "id"), ("offer_name", "name", "id"), ("offer_price", "item_price", "id"), {"qty": "qty"}))
        save_count("sbayoffers", import_option_table("sbayoffers", "sbay-offer", ("offer_code", "code", "id"), ("offer_name", "name", "id"), ("offer_price", "item_price", "id"), {"qty": "qty"}))
        save_count("adenettbl", import_option_table("adenettbl", "adenet-bill", ("unit", "id"), ("unit", "id"), ("price", "item_price", "id"), {"qty": "qty", "link_num": "link_num"}))
        save_count("whytbl", import_option_table("whytbl", "why-bill", ("package_id", "caon_num", "why_unit", "why_id"), ("why_unit", "package_id", "why_id"), ("why_price", "why_price1", "item_price", "why_id"), {"qty": "qty", "caonlink": "caonlink"}))

        # Explicit telecom denomination tables from the backup.
        def import_denom(table, service_code, unit_field, sale_fields, face_fields, code_field=None):
            service = services.get(service_code)
            if not service:
                return 0
            count = 0
            for row in _read_table(text, table, schema[table]):
                code = str(row.get(code_field or unit_field) or row.get("id") or "").strip()
                face = _decimal(_first(row, *face_fields, default=0))
                sale = _decimal(_first(row, *sale_fields, default=face))
                TelecomDenomination.objects.update_or_create(
                    service=service,
                    external_code=canonical_yemen_mobile_offer_code(code) if service_code.startswith("yem-") else code,
                    defaults={
                        "name": f"{row.get(unit_field) or code}",
                        "face_value": face,
                        "sale_price": sale,
                        "metadata": {"legacy_id": row.get("id"), "catalog_source": "legacy database backup", "legacy_row": row},
                        "is_active": True,
                    },
                )
                count += 1
            return count

        save_count("mobiletbl", import_denom("mobiletbl", "yem-denomination", "mobile_unit", ("mobile_price", "mobile_price1", "item_price"), ("mobile_unit", "qty"), "mobile_unit"))
        save_count("mtntbl", import_denom("mtntbl", "you-denomination", "mtn_unit", ("mtn_price", "mtn_price1", "item_price"), ("mtn_unit", "qty"), "mtn_unit"))
        save_count("sabatbl", import_denom("sabatbl", "saba-denomination", "saba_unit", ("saba_price", "saba_price1", "item_price"), ("saba_unit", "qty"), "saba_unit"))

        # Yemen 4G legacy units become plans; keep the human unit name and
        # original price instead of inventing a provider code.
        yem4g = services.get("yem4g-package")
        fg_count = 0
        if yem4g:
            for row in _read_table(text, "yemfgtbl", schema["yemfgtbl"]):
                external_code = f"legacy-yem4g-{row.get('id')}"
                TelecomPlan.objects.update_or_create(
                    service=yem4g,
                    external_code=external_code,
                    defaults={
                        "name": str(row.get("unit_name") or external_code),
                        "price": _decimal(row.get("unit_price")),
                        "metadata": {"legacy_id": row.get("id"), "legacy_unit_name": row.get("unit_name"), "catalog_source": "legacy database backup"},
                        "is_active": True,
                    },
                )
                fg_count += 1
        save_count("yemfgtbl", fg_count)

        # Generic operations are preserved as legacy-only services. They are not
        # assigned to a provider link because the supplied API contract is the
        # authoritative executable contract and these rows may represent local-only operations.
        op_count = 0
        if "operations" in schema:
            for row in _read_table(text, "operations", schema["operations"]):
                legacy_code = f"legacy-operation-{row.get('id')}"
                category = _ensure_legacy_category(main_payments, "legacy-operations", "خدمات النسخة القديمة")
                _ensure_legacy_service(
                    category,
                    code=legacy_code,
                    name=str(row.get("operation_name") or legacy_code),
                    kind="catalog" if str(row.get("servtype") or "").lower() in {"catalog", "offer"} else "query",
                    metadata={
                        "legacy_operation_id": row.get("id"),
                        "legacy_servtype": row.get("servtype"),
                        "legacy_fields": row.get("operation_fields") or "",
                        "legacy_linkid": row.get("operation_linkid") or "",
                        "legacy_amountlink": row.get("operation_amountlink") or "",
                        "legacy_uniqcode": row.get("operation_uniqcode") or "",
                    },
                )
                op_count += 1
        save_count("operations", op_count)

        if options["dry_run"]:
            transaction.set_rollback(True)
            self.stdout.write(self.style.WARNING("وضع المعاينة: لم تُحفظ أي تغييرات."))
        for key, value in summary.items():
            self.stdout.write(f"{key}: {value}")
        self.stdout.write(self.style.SUCCESS("اكتمل فحص/استيراد كتالوج النسخة الاحتياطية."))
