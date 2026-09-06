from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction

from accounting.models import Wallet as AccountingWallet
from accounting.services_v2 import ensure_wallet, wallet_balance, ensure_legacy_customer_opening, ensure_legacy_vendor_available
from finance.models import Wallet as FinanceWallet


class Command(BaseCommand):
    help = "يفحص محافظ finance القديمة ويحوّل الأرصدة إلى القيود فقط عند غياب رصيد محاسبي متعارض."

    def add_arguments(self, parser):
        parser.add_argument("--apply", action="store_true", help="نفّذ الترحيل؛ بدونها تكون العملية معاينة فقط")
        parser.add_argument("--fail-on-conflict", action="store_true", help="افشل إذا وجد رصيد محاسبي غير صفري مختلف عن الرصيد القديم")

    def handle(self, *args, **options):
        apply = options["apply"]
        conflicts = []
        planned = []
        migrated = 0

        for legacy in FinanceWallet.objects.select_related("user").order_by("id"):
            amount = Decimal(legacy.balance).quantize(Decimal("0.01"))
            currency = str(legacy.currency or "YER").upper()
            kind = (
                AccountingWallet.Kinds.VENDOR_AVAILABLE
                if getattr(legacy.user, "role", None) == "vendor"
                else AccountingWallet.Kinds.CUSTOMER
            )
            accounting_wallet = ensure_wallet(legacy.user, kind, currency)
            current = wallet_balance(accounting_wallet).quantize(Decimal("0.01"))

            if amount == current:
                self.stdout.write(f"OK user={legacy.user_id} {currency}: {amount}")
                continue

            if current != Decimal("0.00"):
                conflicts.append(f"user={legacy.user_id} {currency}: legacy={amount} accounting={current}")
                continue

            if amount < 0:
                conflicts.append(f"user={legacy.user_id} {currency}: legacy balance is negative ({amount})")
                continue

            planned.append((legacy.user, amount, currency, kind))
            if apply and amount > 0:
                with transaction.atomic():
                    if kind == AccountingWallet.Kinds.VENDOR_AVAILABLE:
                        ensure_legacy_vendor_available(legacy.user, amount, currency)
                    else:
                        ensure_legacy_customer_opening(legacy.user, amount, currency)
                migrated += 1

        self.stdout.write(f"planned={len(planned)} migrated={migrated} conflicts={len(conflicts)} mode={'APPLY' if apply else 'DRY-RUN'}")
        for conflict in conflicts:
            self.stderr.write(self.style.ERROR(conflict))

        if conflicts and options["fail_on_conflict"]:
            raise SystemExit("Legacy wallet migration aborted because of conflicting accounting balances.")
        self.stdout.write(self.style.SUCCESS("Legacy wallet migration completed safely."))
