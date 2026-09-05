from collections import defaultdict
from datetime import date
from decimal import Decimal
import uuid

from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from .models import Account, JournalEntry, JournalLine, Voucher, Wallet


ROOTS = {
    "cash": ("1000", "الصناديق", Account.Types.GROUP, Account.NormalSides.DEBIT),
    "employees": ("2000", "الموظفون", Account.Types.GROUP, Account.NormalSides.CREDIT),
    "customers": ("3000", "العملاء", Account.Types.GROUP, Account.NormalSides.CREDIT),
    "suppliers": ("4000", "الموردون والتجار", Account.Types.GROUP, Account.NormalSides.CREDIT),
    "equity": ("5000", "حقوق الملكية", Account.Types.GROUP, Account.NormalSides.CREDIT),
    "income": ("6000", "الإيرادات", Account.Types.GROUP, Account.NormalSides.CREDIT),
    "expense": ("7000", "المصروفات", Account.Types.GROUP, Account.NormalSides.DEBIT),
}


def _leaf_account(parent, name, account_type, normal_side, *, party_type="", party_user=None, metadata=None):
    existing = Account.objects.filter(parent=parent, name=name, party_type=party_type, party_user=party_user).first()
    if existing:
        return existing
    locked_parent = Account.objects.select_for_update().get(pk=parent.pk)
    siblings = Account.objects.select_for_update().filter(parent=locked_parent).order_by("code")
    prefix = locked_parent.code
    used = []
    for row in siblings:
        suffix = row.code[len(prefix):] if row.code.startswith(prefix) else ""
        if suffix.isdigit() and len(suffix) <= 2:
            used.append(int(suffix))
    next_suffix = next((n for n in range(1, 100) if n not in used), None)
    if next_suffix is None:
        raise ValueError(f"لا يمكن إنشاء أكثر من 99 حسابًا تحت {parent}.")
    code = f"{prefix}{next_suffix:02d}"
    return Account.objects.create(
        code=code,
        name=name,
        parent=locked_parent,
        account_type=account_type,
        normal_side=normal_side,
        is_group=False,
        party_type=party_type,
        party_user=party_user,
        metadata=metadata or {},
    )


@transaction.atomic
def ensure_chart():
    accounts = {}
    for key, (code, name, account_type, normal_side) in ROOTS.items():
        accounts[key], _ = Account.objects.get_or_create(
            code=code,
            defaults={
                "name": name,
                "account_type": account_type,
                "normal_side": normal_side,
                "is_group": True,
            },
        )
    accounts["main_cash"], _ = Account.objects.get_or_create(
        code="100001",
        defaults={
            "name": "الصندوق الرئيسي",
            "parent": accounts["cash"],
            "account_type": Account.Types.ASSET,
            "normal_side": Account.NormalSides.DEBIT,
            "is_group": False,
        },
    )
    accounts["opening_equity"], _ = Account.objects.get_or_create(
        code="500001",
        defaults={
            "name": "أرصدة افتتاحية وترحيل سابق",
            "parent": accounts["equity"],
            "account_type": Account.Types.EQUITY,
            "normal_side": Account.NormalSides.CREDIT,
            "is_group": False,
        },
    )
    accounts["commission_income"], _ = Account.objects.get_or_create(
        code="600001",
        defaults={
            "name": "عمولات المنصة",
            "parent": accounts["income"],
            "account_type": Account.Types.INCOME,
            "normal_side": Account.NormalSides.CREDIT,
            "is_group": False,
        },
    )
    accounts["refund_expense"], _ = Account.objects.get_or_create(
        code="700001",
        defaults={
            "name": "استردادات وتسويات الطلبات",
            "parent": accounts["expense"],
            "account_type": Account.Types.EXPENSE,
            "normal_side": Account.NormalSides.DEBIT,
            "is_group": False,
        },
    )
    return accounts


def ensure_party_account(user, party_type):
    chart = ensure_chart()
    root_key = "customers" if party_type == "customer" else "suppliers"
    root = chart[root_key]
    name = user.get_full_name().strip() or user.phone or user.username or f"حساب {user.pk}"
    return _leaf_account(
        root,
        name,
        Account.Types.LIABILITY,
        Account.NormalSides.CREDIT,
        party_type=party_type,
        party_user=user,
    )


def ensure_wallet(user, kind, currency="YER"):
    party_type = "customer" if kind == Wallet.Kinds.CUSTOMER else "vendor"
    party = ensure_party_account(user, party_type)
    names = {
        Wallet.Kinds.CUSTOMER: "محفظة العميل",
        Wallet.Kinds.VENDOR_PENDING: "مستحقات التاجر المعلقة",
        Wallet.Kinds.VENDOR_AVAILABLE: "رصيد التاجر المتاح",
        Wallet.Kinds.WITHDRAWAL_HOLD: "طلبات السحب المعلقة",
    }
    account = _leaf_account(
        party,
        f"{names[kind]} {currency}",
        Account.Types.LIABILITY,
        Account.NormalSides.CREDIT,
        party_type=f"wallet:{kind}",
        party_user=user,
        metadata={"wallet_kind": kind, "currency": currency},
    )
    wallet, _ = Wallet.objects.get_or_create(
        owner=user,
        kind=kind,
        currency=currency,
        defaults={"account": account},
    )
    if wallet.account_id != account.id:
        wallet.account = account
        wallet.save(update_fields=["account", "updated_at"])
    return wallet


def account_balance(account):
    totals = account.journal_lines.filter(entry__status=JournalEntry.Status.POSTED).aggregate(
        debit=Sum("debit"), credit=Sum("credit")
    )
    debit = totals["debit"] or Decimal("0.00")
    credit = totals["credit"] or Decimal("0.00")
    return (debit - credit) if account.normal_side == Account.NormalSides.DEBIT else (credit - debit)


def wallet_balance(wallet):
    return account_balance(wallet.account)


def _next_entry_number(prefix="JE"):
    return f"{prefix}-{timezone.now():%Y%m%d}-{uuid.uuid4().hex[:8].upper()}"


@transaction.atomic
def post_entry(description, lines, *, source_type="", source_id="", idempotency_key=None, created_by=None, entry_date=None, metadata=None):
    if idempotency_key:
        existing = JournalEntry.objects.filter(idempotency_key=idempotency_key).first()
        if existing:
            return existing
    normalized = []
    debit_total = Decimal("0.00")
    credit_total = Decimal("0.00")
    for item in lines:
        account = item["account"]
        debit = Decimal(str(item.get("debit", "0"))).quantize(Decimal("0.01"))
        credit = Decimal(str(item.get("credit", "0"))).quantize(Decimal("0.01"))
        if account.is_group:
            raise ValueError(f"الحساب {account.code} رئيسي ولا يمكن استخدامه في القيد.")
        if debit < 0 or credit < 0 or (debit > 0 and credit > 0) or (debit == 0 and credit == 0):
            raise ValueError("كل سطر يجب أن يحتوي قيمة مدين أو دائن واحدة فقط.")
        debit_total += debit
        credit_total += credit
        normalized.append({"account": account, "description": item.get("description", ""), "debit": debit, "credit": credit})
    if debit_total != credit_total:
        raise ValueError(f"القيد غير متوازن: المدين {debit_total} والدائن {credit_total}.")
    entry = JournalEntry.objects.create(
        number=_next_entry_number(),
        entry_date=entry_date or date.today(),
        description=description,
        source_type=source_type,
        source_id=str(source_id or ""),
        idempotency_key=idempotency_key,
        created_by=created_by,
        metadata=metadata or {},
    )
    JournalLine.objects.bulk_create([
        JournalLine(entry=entry, account=row["account"], description=row["description"], debit=row["debit"], credit=row["credit"])
        for row in normalized
    ])
    return entry


def ensure_legacy_customer_opening(user, balance, currency):
    ensure_wallet(user, Wallet.Kinds.CUSTOMER, currency)
    amount = Decimal(balance or 0).quantize(Decimal("0.01"))
    key = f"opening:legacy:customer:{user.pk}:{currency}"
    if amount <= 0 or JournalEntry.objects.filter(idempotency_key=key).exists():
        return
    chart = ensure_chart()
    wallet = ensure_wallet(user, Wallet.Kinds.CUSTOMER, currency)
    post_entry(
        "ترحيل رصيد العميل من المحفظة القديمة",
        [
            {"account": chart["opening_equity"], "debit": amount},
            {"account": wallet.account, "credit": amount},
        ],
        source_type="legacy_wallet",
        source_id=user.pk,
        idempotency_key=key,
        metadata={"legacy_balance": str(amount), "currency": currency},
    )


def ensure_legacy_vendor_available(user, balance, currency):
    amount = Decimal(balance or 0).quantize(Decimal("0.01"))
    key = f"opening:legacy:vendor-available:{user.pk}:{currency}"
    if amount <= 0 or JournalEntry.objects.filter(idempotency_key=key).exists():
        return
    chart = ensure_chart()
    wallet = ensure_wallet(user, Wallet.Kinds.VENDOR_AVAILABLE, currency)
    post_entry(
        "ترحيل رصيد التاجر المتاح من المحفظة القديمة",
        [
            {"account": chart["opening_equity"], "debit": amount},
            {"account": wallet.account, "credit": amount},
        ],
        source_type="legacy_vendor_wallet",
        source_id=user.pk,
        idempotency_key=key,
        metadata={"legacy_balance": str(amount), "currency": currency},
    )


def fund_order(order, *, created_by=None):
    from orders.models import VendorOrder

    ensure_wallet(order.customer, Wallet.Kinds.CUSTOMER, order.currency)
    customer_wallet = ensure_wallet(order.customer, Wallet.Kinds.CUSTOMER, order.currency)
    vendor_orders = list(VendorOrder.objects.select_related("vendor__owner").filter(order=order).order_by("id"))
    lines = [{"account": customer_wallet.account, "debit": Decimal(order.total), "description": f"حجز قيمة الطلب {order.order_number}"}]
    commission = Decimal("0.00")
    for vendor_order in vendor_orders:
        vendor_net = Decimal(vendor_order.vendor_net)
        if vendor_net > 0:
            pending = ensure_wallet(vendor_order.vendor.owner, Wallet.Kinds.VENDOR_PENDING, order.currency)
            lines.append({"account": pending.account, "credit": vendor_net, "description": f"مستحقات معلقة للطلب {vendor_order.order_number}"})
        commission += Decimal(vendor_order.commission)
    if commission > 0:
        income = ensure_chart()["commission_income"]
        lines.append({"account": income, "credit": commission, "description": f"عمولة المنصة للطلب {order.order_number}"})
    return post_entry(
        f"حجز وتمويل الطلب {order.order_number}",
        lines,
        source_type="order",
        source_id=order.pk,
        idempotency_key=f"order:fund:{order.pk}",
        created_by=created_by,
        metadata={"order_total": str(order.total), "currency": order.currency},
    )


def release_vendor_pending(vendor_user, amount, currency, *, vendor_order_id, created_by=None):
    amount = Decimal(amount).quantize(Decimal("0.01"))
    if amount <= 0:
        return None
    pending = ensure_wallet(vendor_user, Wallet.Kinds.VENDOR_PENDING, currency)
    available = ensure_wallet(vendor_user, Wallet.Kinds.VENDOR_AVAILABLE, currency)
    return post_entry(
        f"تحرير مستحقات الطلب {vendor_order_id}",
        [
            {"account": pending.account, "debit": amount},
            {"account": available.account, "credit": amount},
        ],
        source_type="vendor_order_release",
        source_id=vendor_order_id,
        idempotency_key=f"vendor-order:release:{vendor_order_id}",
        created_by=created_by,
        metadata={"vendor_order_id": vendor_order_id, "currency": currency},
    )


def hold_withdrawal(user, amount, currency, *, withdrawal_id, created_by=None):
    amount = Decimal(amount).quantize(Decimal("0.01"))
    available = ensure_wallet(user, Wallet.Kinds.VENDOR_AVAILABLE, currency)
    hold = ensure_wallet(user, Wallet.Kinds.WITHDRAWAL_HOLD, currency)
    return post_entry(
        f"حجز طلب السحب {withdrawal_id}",
        [
            {"account": available.account, "debit": amount},
            {"account": hold.account, "credit": amount},
        ],
        source_type="withdrawal_hold",
        source_id=withdrawal_id,
        idempotency_key=f"withdrawal:hold:{withdrawal_id}",
        created_by=created_by,
    )


def settle_withdrawal(user, amount, currency, *, withdrawal_id, created_by=None):
    amount = Decimal(amount).quantize(Decimal("0.01"))
    hold = ensure_wallet(user, Wallet.Kinds.WITHDRAWAL_HOLD, currency)
    cash = ensure_chart()["main_cash"]
    return post_entry(
        f"صرف طلب السحب {withdrawal_id}",
        [
            {"account": hold.account, "debit": amount},
            {"account": cash, "credit": amount},
        ],
        source_type="withdrawal_paid",
        source_id=withdrawal_id,
        idempotency_key=f"withdrawal:paid:{withdrawal_id}",
        created_by=created_by,
    )


def reject_withdrawal(user, amount, currency, *, withdrawal_id, created_by=None):
    amount = Decimal(amount).quantize(Decimal("0.01"))
    hold = ensure_wallet(user, Wallet.Kinds.WITHDRAWAL_HOLD, currency)
    available = ensure_wallet(user, Wallet.Kinds.VENDOR_AVAILABLE, currency)
    return post_entry(
        f"إلغاء حجز طلب السحب {withdrawal_id}",
        [
            {"account": hold.account, "debit": amount},
            {"account": available.account, "credit": amount},
        ],
        source_type="withdrawal_rejected",
        source_id=withdrawal_id,
        idempotency_key=f"withdrawal:reject:{withdrawal_id}",
        created_by=created_by,
    )


def statement_for_user(user, currency="YER", wallet_kinds=None):
    kinds = wallet_kinds or [Wallet.Kinds.CUSTOMER, Wallet.Kinds.VENDOR_PENDING, Wallet.Kinds.VENDOR_AVAILABLE, Wallet.Kinds.WITHDRAWAL_HOLD]
    wallets = [ensure_wallet(user, kind, currency) for kind in kinds]
    account_ids = [wallet.account_id for wallet in wallets]
    lines = JournalLine.objects.filter(
        account_id__in=account_ids,
        entry__status=JournalEntry.Status.POSTED,
    ).select_related("entry", "account").order_by("entry__entry_date", "entry_id", "id")
    running = defaultdict(lambda: Decimal("0.00"))
    result = []
    for line in lines:
        delta = Decimal(line.credit) - Decimal(line.debit)
        running[line.account_id] += delta
        result.append({
            "journal": line.entry.number,
            "date": line.entry.entry_date.isoformat(),
            "description": line.entry.description,
            "wallet": line.account.metadata.get("wallet_kind", "") if hasattr(line.account, "metadata") else "",
            "account": line.account.code,
            "debit": str(line.debit),
            "credit": str(line.credit),
            "balance": str(running[line.account_id]),
            "source_type": line.entry.source_type,
            "source_id": line.entry.source_id,
        })
    return result


def wallet_summary(user, currency="YER"):
    wallets = {}
    for kind in Wallet.Kinds.values:
        wallet = ensure_wallet(user, kind, currency)
        wallets[kind] = wallet_balance(wallet)
    return {
        "currency": currency,
        "customer": {"available": str(wallets[Wallet.Kinds.CUSTOMER])},
        "vendor": {
            "pending": str(wallets[Wallet.Kinds.VENDOR_PENDING]),
            "available": str(wallets[Wallet.Kinds.VENDOR_AVAILABLE]),
            "withdrawal_hold": str(wallets[Wallet.Kinds.WITHDRAWAL_HOLD]),
            "withdrawable": str(max(Decimal("0.00"), wallets[Wallet.Kinds.VENDOR_AVAILABLE])),
            "total": str(wallets[Wallet.Kinds.VENDOR_PENDING] + wallets[Wallet.Kinds.VENDOR_AVAILABLE]),
        },
    }
