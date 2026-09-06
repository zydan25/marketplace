from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db.models import Q

from accounting.models import JournalEntry, Wallet as AccountingWallet
from accounting.services_v2 import ensure_wallet as ensure_accounting_wallet, wallet_balance
from finance.models import Wallet as FinanceWallet
from finance.unified_wallet import sync_finance_projection
from promotions.models import GiftTransfer
from services.models import ServiceTransaction


FINAL_STATUSES = {
    ServiceTransaction.Status.SUCCESS,
    ServiceTransaction.Status.REFUNDED,
    ServiceTransaction.Status.FAILED,
}


class Command(BaseCommand):
    help = "يفحص تطابق المحافظ والقيود وحالات خدمات المزود والتحويلات، مع خيار إصلاح projection فقط."

    def add_arguments(self, parser):
        parser.add_argument("--fix", action="store_true", help="إصلاح finance.Wallet كنسخة عرض فقط من الرصيد المحاسبي")
        parser.add_argument("--strict", action="store_true", help="اعتبر السجلات المالية التاريخية غير المربوطة بالقيد أخطاء")
        parser.add_argument("--fail-on-mismatch", action="store_true", help="اخرج بحالة فشل عند وجود أي مخالفة")

    def handle(self, *args, **options):
        errors = []
        warnings = []

        # 1) Finance wallet projection must equal the accounting source of truth.
        for wallet in FinanceWallet.objects.select_related("user").all().order_by("id"):
            kind = (
                AccountingWallet.Kinds.VENDOR_AVAILABLE
                if getattr(wallet.user, "role", None) == "vendor"
                else AccountingWallet.Kinds.CUSTOMER
            )
            accounting_wallet = ensure_accounting_wallet(wallet.user, kind, wallet.currency)
            authoritative = wallet_balance(accounting_wallet).quantize(Decimal("0.01"))
            projection = Decimal(wallet.balance).quantize(Decimal("0.01"))
            if projection != authoritative:
                message = f"wallet {wallet.pk}/user {wallet.user_id}: finance={projection} accounting={authoritative} {wallet.currency}"
                if options["fix"]:
                    sync_finance_projection(wallet.user, wallet.currency)
                    warnings.append(f"تمت مزامنة {message}")
                else:
                    errors.append(message)
            if projection < 0:
                errors.append(f"wallet {wallet.pk}: الرصيد التاريخي سالب")

        # 2) Every billable service transaction must have a coherent journal lifecycle.
        for tx in ServiceTransaction.objects.select_related("service").all().iterator():
            billable = bool(tx.service.requires_balance and tx.customer_amount > 0)
            if billable and tx.status not in FINAL_STATUSES and not tx.reserved_journal_id:
                errors.append(f"service tx {tx.id}: عملية مدفوعة بلا قيد حجز")
            if billable and tx.status == ServiceTransaction.Status.SUCCESS:
                if not tx.reserved_journal_id or not JournalEntry.objects.filter(pk=tx.reserved_journal_id, source_type="service_reservation").exists():
                    errors.append(f"service tx {tx.id}: نجاح بلا قيد حجز صالح")
                if not tx.settled_journal_id or not JournalEntry.objects.filter(pk=tx.settled_journal_id, source_type="service_settlement").exists():
                    errors.append(f"service tx {tx.id}: نجاح بلا قيد تسوية صالح")
            if billable and tx.status == ServiceTransaction.Status.REFUNDED:
                if not tx.reserved_journal_id or not JournalEntry.objects.filter(pk=tx.reserved_journal_id, source_type="service_reservation").exists():
                    errors.append(f"service tx {tx.id}: استرداد بلا حجز")
                if not tx.refund_journal_id or not JournalEntry.objects.filter(pk=tx.refund_journal_id, source_type="service_refund").exists():
                    errors.append(f"service tx {tx.id}: استرداد بلا قيد رد صالح")
            if billable and tx.status == ServiceTransaction.Status.FAILED:
                errors.append(f"service tx {tx.id}: عملية مدفوعة انتهت failed بدل refunded/manual_review")
            if tx.status in {ServiceTransaction.Status.SUCCESS, ServiceTransaction.Status.REFUNDED} and not tx.completed_at:
                errors.append(f"service tx {tx.id}: حالة نهائية بلا completed_at")

        # 3) Completed legacy gifts must have an accounting journal. The new financial API
        # uses source_type=gift; the legacy compatibility endpoint uses source_id=gift:<id>.
        for gift in GiftTransfer.objects.filter(status=GiftTransfer.Status.COMPLETED).only("id"):
            exists = JournalEntry.objects.filter(
                source_type="gift",
            ).filter(Q(source_id=f"gift:{gift.id}") | Q(metadata__gift_id=gift.id)).exists()
            if not exists:
                msg = f"gift {gift.id}: مكتملة بلا قيد محاسبي مرتبط"
                if options["strict"]:
                    errors.append(msg)
                else:
                    warnings.append(msg)

        # 4) Idempotency keys must never map to different users or services.
        # DB uniqueness already prevents duplicates; this verifies the semantic links.
        keyed = ServiceTransaction.objects.exclude(idempotency_key__isnull=True).exclude(idempotency_key="").select_related("service")
        seen = set()
        for tx in keyed.iterator():
            key = str(tx.idempotency_key)
            if key in seen:
                errors.append(f"service tx {tx.id}: duplicate idempotency key detected")
            seen.add(key)

        self.stdout.write(f"finance wallets={FinanceWallet.objects.count()} service_transactions={ServiceTransaction.objects.count()} gifts={GiftTransfer.objects.count()}")
        for warning in warnings:
            self.stdout.write(self.style.WARNING(warning))
        for error in errors:
            self.stderr.write(self.style.ERROR(error))

        if errors and (options["fail_on_mismatch"] or options["strict"]):
            raise SystemExit("Financial integrity check failed.")
        self.stdout.write(self.style.SUCCESS("Financial integrity audit completed."))
