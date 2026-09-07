"""Import service/catalog data from the supplied legacy MySQL backup.

The import is deliberately split into two layers:
1. rows that are part of the current Sanaacash contract become live catalog
   records and can be exposed to the customer app;
2. legacy-only rows are preserved as inactive/unlinked catalog records with
   their original values in metadata, so they are not accidentally sent to a
   provider that the current API contract does not define.

Customer/accounting/payment history is not duplicated into service catalog
models. Those records belong to their existing Django domains.
"""

from __future__ import annotations

import io
import re
import zipfile
from decimal import Decimal, InvalidOperation
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.text import slugify

from services.catalog_base import SERVICES
from services.catalog_yemen_contract import canonical_yemen_mobile_offer_code
from services.management.commands.provision_sanaacash import provision
from services.models import (
    GameProduct,
    MainServiceCategory,
    Service,
    ServiceCategory,
    ServiceOption,
    TelecomDenomination,
    TelecomPlan,
)


def _open_dump(path: Path):
    if path.suffix.lower() != ".zip":
        return path.open("r", encoding="utf-8", errors="replace"), None
    archive = zipfile.ZipFile(path)
    names = [n for n in archive.namelist() if n.lower().endswith((".sql", ".dump"))]
    if not names:
        archive.close()
        raise CommandError("الملف المضغوط لا يحتوي ملف SQL.")
    return io.TextIOWrapper(archive.open(names[0], "r"), encoding="utf-8", errors="replace"), archive


def _statements(text: str, table: str):
    prefix = f"INSERT INTO `{table}`"
    start = 0
    while True:
        pos = text.find(prefix, start)
        if pos < 0:
            return
        quote = None
        escaped = False
        for i in range(pos, len(text)):
            ch = text[i]
            if quote:
                if escaped:
                    escaped = False
                elif ch == "\\":
                    escaped = True
                elif ch == quote:
                    quote = None
                continue
            if ch in ("'", '"'):
                quote = ch
            elif ch == ";":
                yield text[pos : i + 1]
                start = i + 1
                break
        else:
            return


def _table_columns(text: str, table: str):
    match = re.search(r"CREATE TABLE `" + re.escape(table) + r"`\s*\((.*?)\) ENGINE=", text, re.S)
    if not match:
        return []
    return re.findall(r"^\s*`([^`]+)`\s+", match.group(1), re.M)


def _rows(text: str, table: str, columns: list[str]):
    if not columns:
        return
    for statement in _statements(text, table):
        value_match = re.search(r"\bVALUES\s+(.*);\s*$", statement, re.S)
        if not value_match:
            continue
        values = value_match.group(1)
        row, rows, token = [], [], []
        depth = 0
        quote = None
        escaped = False
        for ch in values:
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
                    row.append("".join(token).strip())
                    token = []
                    if len(row) == len(columns):
                        rows.append(row)
                    row = []
                else:
                    token.append(ch)
            elif ch == "," and depth == 1:
                row.append("".join(token).strip())
                token = []
            elif depth:
                token.append(ch)
        for raw_row in rows:
            yield {columns[i]: _value(raw_row[i]) for i in range(len(columns))}


def _value(raw: str):
    value = raw.strip()
    if value.upper() == "NULL":
        return None
    if len(value) >= 2 and value[0] == "'" and value[-1] == "'":
        body = value[1:-1]
        # MySQL dumps may use backslash escapes. Do the common ones explicitly
        # so Arabic text is never decoded through unicode_escape.
        return (
            body.replace("\\\\", "\\")
            .replace("\\'", "'")
            .replace('\\"', '"')
            .replace("\\n", "\n")
            .replace("\\r", "\r")
            .replace("\\t", "\t")
        )
    return value


def _first(row, *names, default=None):
    for name in names:
        value = row.get(name)
        if value not in (None, ""):
            return value
    return default


def _decimal(value, default=Decimal("0")):
    try:
        return default if value in (None, "") else Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return default


def _category(main, slug, name, parent=None):
    return ServiceCategory.objects.update_or_create(
        main_category=main,
        parent=parent,
        slug=slugify(slug, allow_unicode=True)[:160],
        defaults={"name": str(name)[:160], "is_active": True},
    )[0]


def _legacy_service(category, code, name, metadata=None):
    return Service.objects.update_or_create(
        code=code[:80],
        defaults={
            "category": category,
            "name": str(name)[:180],
            "slug": slugify(code, allow_unicode=True)[:180],
            "description": "بيانات قديمة محفوظة للمراجعة؛ لا تُنفذ لدى المزود حتى تطابق عقد API الحالي.",
            "service_kind": Service.ServiceKinds.CATALOG,
            "requires_balance": False,
            "pricing_mode": Service.PricingModes.ITEM,
            "price": Decimal("0"),
            "currency": "YER",
            "metadata": {"legacy_only": True, "provider_supported": False, **(metadata or {})},
            "is_active": True,
        },
    )[0]


def _import_plan_rows(text, schema, table, service, code_names, name_names, price_names, extra=None):
    count = 0
    for row in _rows(text, table, schema[table]):
        code = str(_first(row, *code_names, default=row.get("id") or row.get("offer_num") or count + 1)).strip()
        name = str(_first(row, *name_names, default=code)).strip()
        price = _decimal(_first(row, *price_names, default="0"))
        metadata = {"legacy_id": row.get("id"), "catalog_source": "legacy database backup"}
        if extra:
            metadata.update({key: row.get(source) for key, source in extra.items()})
        TelecomPlan.objects.update_or_create(
            service=service,
            external_code=code,
            defaults={
                "name": name[:180],
                "price": price,
                "metadata": metadata,
                "is_active": True,
            },
        )
        count += 1
    return count


class Command(BaseCommand):
    help = "استيراد كتالوجات الخدمات من النسخة الاحتياطية القديمة دون ربط عشوائي بالمزود."

    def add_arguments(self, parser):
        parser.add_argument("dump", help="مسار ملف SQL أو ZIP")
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

        tables = {name: _table_columns(text, name) for name in (
            "gameunits", "operationsgroups", "operations", "mtnoffers", "sabaoffers", "sbayoffers",
            "whyoffers", "whytbl", "adenettbl", "mobiletbl", "mtntbl", "sabatbl", "yemfgtbl",
            "wifiunitstbl", "wifinetworkstbl", "wificardstbl",
        )}
        tables = {k: v for k, v in tables.items() if v}
        _, _, services = provision()
        main_games = MainServiceCategory.objects.get(slug="games")
        main_payments = MainServiceCategory.objects.get(slug="payments")
        counts = {}

        # 2541 legacy game/package rows become the actual customer-visible
        # game products. No external provider code is invented when absent.
        groups = {str(r.get("id")): r for r in _rows(text, "operationsgroups", tables.get("operationsgroups", []))}
        games_count = 0
        for row in _rows(text, "gameunits", tables.get("gameunits", [])):
            group = groups.get(str(row.get("group_id")), {})
            game_code = str(_first(group, "game_network", default="legacy" ) or "legacy").strip().lower()
            service = services.get(game_code)
            if service is None:
                cat = _category(main_games, f"legacy-{row.get('group_id')}", _first(group, "group_name", default="ألعاب قديمة"))
                service = _legacy_service(cat, f"legacy-{game_code}", _first(group, "group_name", default=game_code), {"legacy_group_id": row.get("group_id")})
            external_code = str(_first(row, "uniq_code", default=row.get("id"))).strip()
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
                defaults={"name": str(row.get("unit_name") or external_code)[:180], "price": _decimal(row.get("unit_price")), "currency": "YER", "metadata": metadata, "is_active": True},
            )
            games_count += 1
        counts["gameunits"] = games_count

        # Current API services get typed catalog rows rather than generic
        # legacy options, so the client can render names/prices consistently.
        if "mtnoffers" in tables and services.get("you-offer"):
            counts["mtnoffers"] = _import_plan_rows(text, tables, "mtnoffers", services["you-offer"], ("offer_code", "uniq_num", "offer_num", "id"), ("offer_name", "name", "id"), ("offer_price", "item_price", "id"), {"provider_num": "offer_num", "qty": "qty", "detail": "detail"})
        if "sabaoffers" in tables and services.get("saba-offer"):
            counts["sabaoffers"] = _import_plan_rows(text, tables, "sabaoffers", services["saba-offer"], ("offer_code", "uniq_num", "id"), ("offer_name", "name", "id"), ("offer_price", "item_price", "id"), {"provider_num": "uniq_num", "qty": "qty", "detail": "detail"})
        if "sbayoffers" in tables and services.get("sbay-offer"):
            counts["sbayoffers"] = _import_plan_rows(text, tables, "sbayoffers", services["sbay-offer"], ("offer_code", "id"), ("offer_name", "id"), ("offer_price", "item_price", "id"), {"qty": "qty", "detail": "offer_call"})

        # Denomination tables: these are the package branches that really have
        # provider-selected numbers. Yemen Mobile itself remains amount-based.
        for table, code, unit, pk, sale, face in (
            ("mobiletbl", "yem-denomination", "mobile_unit", "mobile_id", "mobile_price1", "mobile_unit"),
            ("mtntbl", "you-denomination", "mtn_unit", "mtn_id", "mtn_price1", "mtn_unit"),
            ("sabatbl", "saba-denomination", "saba_unit", "saba_id", "saba_price1", "saba_unit"),
        ):
            if table not in tables or not services.get(code):
                continue
            count = 0
            for row in _rows(text, table, tables[table]):
                raw_code = str(row.get(unit) or row.get(pk) or "").strip()
                external_code = canonical_yemen_mobile_offer_code(raw_code) if code.startswith("yem-") else raw_code
                TelecomDenomination.objects.update_or_create(
                    service=services[code], external_code=external_code,
                    defaults={
                        "name": f"فئة {raw_code}",
                        "face_value": _decimal(row.get(face)),
                        "sale_price": _decimal(row.get(sale), _decimal(row.get(unit))),
                        "metadata": {"legacy_id": row.get(pk), "legacy_row": row, "catalog_source": "legacy database backup"},
                        "is_active": True,
                    },
                )
                count += 1
            counts[table] = count

        if "whytbl" in tables and services.get("why-package"):
            count = 0
            for row in _rows(text, "whytbl", tables["whytbl"]):
                code = str(row.get("package_id") or row.get("caon_num") or row.get("why_id") or "").strip()
                ServiceOption.objects.update_or_create(
                    service=services["why-package"], external_code=code, provider_num=str(row.get("why_unit") or ""), name=str(row.get("why_unit") or code),
                    defaults={"price": _decimal(row.get("item_price"), _decimal(row.get("why_price1"))), "currency": "YER", "metadata": {"legacy_id": row.get("why_id"), "qty": row.get("qty"), "caonlink": row.get("caonlink"), "catalog_source": "legacy database backup"}, "is_active": True},
                )
                count += 1
            counts["whytbl"] = count

        if "adenettbl" in tables and services.get("adenet-bill"):
            count = 0
            for row in _rows(text, "adenettbl", tables["adenettbl"]):
                code = str(row.get("id") or row.get("unit") or "").strip()
                ServiceOption.objects.update_or_create(
                    service=services["adenet-bill"], external_code=code, provider_num=str(row.get("unit") or ""), name=str(row.get("unit") or code),
                    defaults={"price": _decimal(row.get("item_price"), _decimal(row.get("price"))), "currency": "YER", "metadata": {"legacy_row": row, "catalog_source": "legacy database backup"}, "is_active": True},
                )
                count += 1
            counts["adenettbl"] = count

        if "yemfgtbl" in tables and services.get("yem4g-package"):
            count = 0
            for row in _rows(text, "yemfgtbl", tables["yemfgtbl"]):
                TelecomPlan.objects.update_or_create(
                    service=services["yem4g-package"], external_code=f"legacy-yem4g-{row.get('id')}",
                    defaults={"name": str(row.get("unit_name") or row.get("id")), "price": _decimal(row.get("unit_price")), "metadata": {"legacy_id": row.get("id"), "catalog_source": "legacy database backup"}, "is_active": True},
                )
                count += 1
            counts["yemfgtbl"] = count

        # WiFi catalog is retained as legacy-only until a current provider
        # contract for it is supplied. Never invent a Sanaacash path.
        if "wifiunitstbl" in tables:
            wifi_cat = _category(main_payments, "legacy-wifi", "شبكات الواي فاي القديمة")
            wifi_service = _legacy_service(wifi_cat, "legacy-wifi-cards", "بطاقات شبكات الواي فاي", {"source_tables": ["wifiunitstbl", "wifinetworkstbl", "wificardstbl"]})
            count = 0
            for row in _rows(text, "wifiunitstbl", tables["wifiunitstbl"]):
                ServiceOption.objects.update_or_create(
                    service=wifi_service, external_code=str(row.get("id")), provider_num=str(row.get("network_id") or ""), name=str(row.get("name") or row.get("id")),
                    defaults={"price": _decimal(row.get("price")), "currency": "YER", "metadata": {"legacy_id": row.get("id"), "network_id": row.get("network_id"), "prcnt": row.get("prcnt"), "catalog_source": "legacy database backup"}, "is_active": True},
                )
                count += 1
            counts["wifiunitstbl"] = count

        # Preserve every legacy operation definition as a reviewable service
        # without assigning it to a live provider link.
        if "operations" in tables:
            legacy_cat = _category(main_payments, "legacy-operations", "عمليات النسخة القديمة")
            count = 0
            for row in _rows(text, "operations", tables["operations"]):
                op_id = row.get("operation_id")
                if op_id in (None, ""):
                    continue
                _legacy_service(
                    legacy_cat,
                    f"legacy-operation-{op_id}",
                    row.get("operation_name") or f"عملية {op_id}",
                    {
                        "legacy_operation_id": op_id,
                        "legacy_servtype": row.get("servtype"),
                        "legacy_fields": row.get("operation_fields") or "",
                        "legacy_operation_linkid": row.get("operation_linkid") or "",
                        "legacy_amountlink": row.get("operation_amountlink") or "",
                        "legacy_uniqcode": row.get("operation_uniqcode") or "",
                        "legacy_price": row.get("operation_price") or "",
                        "legacy_price_usd": row.get("price_usd") or "",
                        "legacy_price_rial": row.get("price_rial") or "",
                        "catalog_source": "legacy database backup",
                    },
                )
                count += 1
            counts["operations"] = count

        if options["dry_run"]:
            transaction.set_rollback(True)
            self.stdout.write(self.style.WARNING("DRY RUN: لم يتم حفظ أي تغيير."))
        for key, value in counts.items():
            self.stdout.write(f"{key}: {value}")
        self.stdout.write(self.style.SUCCESS("اكتمل استيراد كتالوج الخدمات مع إبقاء عقد API الحالي هو المرجع التنفيذي."))
