"""Safely migrate legacy clients/balances by matching phone numbers.

The command is dry-run by default. It never creates a new user and never
overwrites a non-zero accounting balance automatically.
"""

import re
from decimal import Decimal, InvalidOperation

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from accounting.models import Wallet
from accounting.services_v2 import ensure_legacy_customer_opening, ensure_legacy_vendor_available, wallet_balance
from marketplace.models import User


def _insert_text(sql, table):
    match = re.search(r"INSERT INTO `" + re.escape(table) + r"` VALUES (.*?);", sql, re.S | re.I)
    return match.group(1) if match else ""


def _parse_rows(sql, table):
    text = _insert_text(sql, table)
    if not text:
        return []
    raw_rows, current, depth = [], [], 0
    quoted = escaped = False
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
            quoted = True; current.append(char)
        elif char == "(":
            depth += 1; current.append(char)
        elif char == ")":
            depth -= 1; current.append(char)
            if depth == 0:
                raw_rows.append("".join(current)[1:-1]); current = []
        elif depth:
            current.append(char)
    return [_parse_row(row) for row in raw_rows]


def _parse_row(row):
    parts, current = [], []
    quoted = escaped = False
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
            quoted = True; current.append(char)
        elif char == ",":
            parts.append("".join(current).strip()); current = []
        else:
            current.append(char)
    parts.append("".join(current).strip())
    result = []
    for value in parts:
        if value.upper() == "NULL":
            result.append(None)
        elif len(value) >= 2 and value[0] == "'" and value[-1] == "'":
            result.append(value[1:-1].replace("\\'", "'").replace("\\\\", "\\"))
        else:
            try:
                result.append(int(value))
            except ValueError:
                try:
                    result.append(Decimal(value))
                except (InvalidOperation, ValueError):
                    result.append(value)
    return result


def _digits(value):
    if value is None:
        return ""
    return str(value).translate(str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "01234567890123456789"))


class Command(BaseCommand):
    help = "مطابقة أرصدة clients/balancetbl القديمة مع المستخدمين الحاليين بأمان."

    def add_arguments(self, parser):
        parser.add_argument("--sql", required=True)
        parser.add_argument("--apply", action="store_true")
        parser.add_argument("--fail-on-conflict", action="store_true")

    def handle(self, *args, **options):
        try:
            sql = open(options["sql"], "r", encoding="utf-8", errors="ignore").read()
        except OSError as exc:
            raise CommandError(str(exc)) from exc

        clients = _parse_rows(sql, "clients")
        balances = _parse_rows(sql, "balancetbl")
        client_by_id = {int(row[0]): row for row in clients if row and str(row[0]).isdigit()}
        legacy_balances = {int(row[2]): Decimal(str(row[1] or 0)) for row in balances if len(row) >= 3 and str(row[2]).isdigit()}

        matched = missing = conflicts = migrated = 0
        for client_id, legacy_balance in sorted(legacy_balances.items()):
            client = client_by_id.get(client_id)
            if not client or len(client) < 36:
                continue
            phone = _digits(client[3])
            user = User.objects.filter(phone=phone).first() if phone else None
            if not user:
                missing += 1
                continue
            matched += 1
            legacy_balance = legacy_balance.quantize(Decimal("0.01"))
            currency = "YER"
            role = getattr(user, "role", "customer")
            kind = Wallet.Kinds.VENDOR_AVAILABLE if role == "vendor" else Wallet.Kinds.CUSTOMER
            accounting_wallet = __import__("accounting.services_v2", fromlist=["ensure_wallet"]).ensure_wallet(user, kind, currency)
            current = wallet_balance(accounting_wallet).quantize(Decimal("0.01"))

            if legacy_balance == current:
                continue
            if current != Decimal("0.00"):
                conflicts += 1
                self.stderr.write(self.style.ERROR(f"CONFLICT client={client_id} user={user.pk} phone={phone}: legacy={legacy_balance} accounting={current}"))
                continue
            if legacy_balance < 0:
                conflicts += 1
                self.stderr.write(self.style.ERROR(f"CONFLICT client={client_id} user={user.pk}: negative legacy balance {legacy_balance}"))
                continue
            if not options["apply"]:
                self.stdout.write(f"PLAN client={client_id} user={user.pk} {legacy_balance} {currency}")
                continue

            with transaction.atomic():
                if role == "vendor":
                    ensure_legacy_vendor_available(user, legacy_balance, currency)
                else:
                    ensure_legacy_customer_opening(user, legacy_balance, currency)
            migrated += 1

        self.stdout.write(
            f"matched={matched} missing={missing} conflicts={conflicts} migrated={migrated} mode={'APPLY' if options['apply'] else 'DRY-RUN'}"
        )
        if conflicts and options["fail_on_conflict"]:
            raise SystemExit("Legacy balance import failed because of conflicts.")
