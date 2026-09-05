from collections import defaultdict
from datetime import date
from decimal import Decimal
import uuid

from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from .models import Account, JournalEntry, JournalLine, Wallet

ROOTS = {
    "cash": ("1000", "الصناديق", Account.Types.GROUP, Account.NormalSides.DEBIT),
    "employees": ("2000", "الموظفون", Account.Types.GROUP, Account.NormalSides.CREDIT),
    "customers": ("3000", "العملاء", Account.Types.GROUP, Account.NormalSides.CREDIT),
    "suppliers": ("4000", "الموردون والتجار", Account.Types.GROUP, Account.NormalSides.CREDIT),
    "equity": ("5000", "حقوق الملكية", Account.Types.GROUP, Account.NormalSides.CREDIT),
    "income": ("6000", "الإيرادات", Account.Types.GROUP, Account.NormalSides.CREDIT),
    "expense": ("7000", "المصروفات", Account.Types.GROUP, Account.NormalSides.DEBIT),
}


def _next_code(parent):
    parent = Account.objects.select_for_update().get(pk=parent.pk)
    used = set()
    for row in Account.objects.select_for_update().filter(parent=parent):
        suffix = row.code[len(parent.code):] if row.code.startswith(parent.code) else ""
        if suffix.isdigit() and 1 <= len(suffix) <= 2:
            used.add(int(suffix))
    n = next((n for n in range(1, 100) if n not in used), None)
    if n is None:
        raise ValueError(f"لا توجد أرقام حساب متاحة تحت {parent.code}.")
    return parent, f"{parent.code}{n:02d}"


def _get_or_create_child(parent, name, *, is_group, account_type, normal_side, party_type="", party_user=None, metadata=None):
    existing = Account.objects.filter(parent=parent, name=name, party_type=party_type, party_user=party_user).first()
    if existing:
        return existing
    parent, code = _next_code(parent)
    return Account.objects.create(
        code=code, name=name, parent=parent, is_group=is_group,
        account_type=account_type, normal_side=normal_side,
        party_type=party_type, party_user=party_user, metadata=metadata or {},
    )


@transaction.atomic
def ensure_chart():
    result = {}
    for key, (code, name, account_type, side) in ROOTS.items():
        result[key], _ = Account.objects.get_or_create(
            code=code,
            defaults={"name": name, "account_type": account_type, "normal_side": side, "is_group": True},
        )
    for code, name, parent_key, account_type, side in [
        ("100001", "الصندوق الرئيسي", "cash", Account.Types.ASSET, Account.NormalSides.DEBIT),
        ("500001", "أرصدة افتتاحية وترحيل سابق", "equity", Account.Types.EQUITY, Account.NormalSides.CREDIT),
        ("600001", "عمولات المنصة", "income", Account.Types.INCOME, Account.NormalSides.CREDIT),
        ("700001", "استردادات وتسويات الطلبات", "expense", Account.Types.EXPENSE, Account.NormalSides.DEBIT),
    ]:
        result_name, _ = Account.objects.get_or_create(
            code=code,
            defaults={"name": name, "parent": result[parent_key], "account_type": account_type, "normal_side": side, "is_group": False},
        )
        result["main_cash" if code == "100001" else "opening_equity" if code == "500001" else "commission_income" if code == "600001" else "refund_expense"] = result_name
    return result


def ensure_party_account(user, party_type):
    chart = ensure_chart()
    root = chart["customers" if party_type == "customer" else "suppliers"]
    name = (user.get_full_name() or getattr(user, "phone", "") or getattr(user, "username", "") or f"حساب {user.pk}").strip()
    return _get_or_create_child(
        root, name, is_group=True, account_type=Account.Types.GROUP,
        normal_side=Account.NormalSides.CREDIT, party_type=party_type, party_user=user,
    )


def ensure_wallet(user, kind, currency="YER"):
    names = {
        Wallet.Kinds.CUSTOMER: "محفظة العميل",
        Wallet.Kinds.VENDOR_PENDING: "مستحقات التاجر المعلقة",
        Wallet.Kinds.VENDOR_AVAILABLE: "رصيد التاجر المتاح",
        Wallet.Kinds.WITHDRAWAL_HOLD: "طلبات السحب المعلقة",
    }
    party = ensure_party_account(user, "customer" if kind == Wallet.Kinds.CUSTOMER else "vendor")
    account = _get_or_create_child(
        party, f"{names[kind]} {currency}", is_group=False,
        account_type=Account.Types.LIABILITY, normal_side=Account.NormalSides.CREDIT,
        party_type=f"wallet:{kind}", party_user=user,
        metadata={"wallet_kind": kind, "currency": currency},
    )
    wallet, _ = Wallet.objects.get_or_create(owner=user, kind=kind, currency=currency, defaults={"account": account})
    if wallet.account_id != account.id:
        wallet.account = account
        wallet.save(update_fields=["account", "updated_at"])
    return wallet


def account_balance(account):
    if account.is_group:
        return sum((account_balance(child) for child in account.children.filter(is_active=True)), Decimal("0.00"))
    totals = account.journal_lines.filter(entry__status=JournalEntry.Status.POSTED).aggregate(debit=Sum("debit"), credit=Sum("credit"))
    debit = totals["debit"] or Decimal("0.00")
    credit = totals["credit"] or Decimal("0.00")
    return (debit - credit) if account.normal_side == Account.NormalSides.DEBIT else (credit - debit)


def wallet_balance(wallet):
    return account_balance(wallet.account)


def _entry_number():
    return f"JE-{timezone.now():%Y%m%d}-{uuid.uuid4().hex[:10].upper()}"


@transaction.atomic
def post_entry(description, lines, *, source_type="", source_id="", idempotency_key=None, created_by=None, entry_date=None, metadata=None):
    if idempotency_key:
        existing = JournalEntry.objects.filter(idempotency_key=idempotency_key).first()
        if existing:
            return existing
    normalized, debit_total, credit_total = [], Decimal("0.00"), Decimal("0.00")
    for row in lines:
        account = Account.objects.select_for_update().get(pk=row["account"].pk)
        debit = Decimal(str(row.get("debit", "0"))).quantize(Decimal("0.01"))
        credit = Decimal(str(row.get("credit", "0"))).quantize(Decimal("0.01"))
        if account.is_group:
            raise ValueError(f"الحساب {account.code} رئيسي ولا يقبل القيود.")
        if debit < 0 or credit < 0 or (debit > 0 and credit > 0) or (debit == 0 and credit == 0):
            raise ValueError("السطر المحاسبي يجب أن يحتوي مدينًا أو دائنًا موجبًا فقط.")
        normalized.append((account, debit, credit, row.get("description", "")))
        debit_total += debit
        credit_total += credit
    if debit_total != credit_total:
        raise ValueError(f"القيد غير متوازن: المدين {debit_total} والدائن {credit_total}.")
    entry = JournalEntry.objects.create(
        number=_entry_number(), entry_date=entry_date or date.today(), description=description,
        source_type=source_type, source_id=str(source_id or ""), idempotency_key=idempotency_key,
        created_by=created_by, metadata=metadata or {}, status=JournalEntry.Status.POSTED,
    )
    JournalLine.objects.bulk_create([
        JournalLine(entry=entry, account=account, debit=debit, credit=credit, description=desc)
        for account, debit, credit, desc in normalized
    ])
    return entry


def ensure_legacy_customer_opening(user, balance, currency):
    wallet = ensure_wallet(user, Wallet.Kinds.CUSTOMER, currency)
    amount = Decimal(balance or 0).quantize(Decimal("0.01"))
    key = f"opening:customer:{user.pk}:{currency}"
    if amount <= 0 or JournalEntry.objects.filter(idempotency_key=key).exists():
        return wallet
    post_entry(
        "ترحيل رصيد العميل من النظام السابق",
        [{"account": ensure_chart()["opening_equity"], "debit": amount}, {"account": wallet.account, "credit": amount}],
        source_type="legacy_wallet", source_id=user.pk, idempotency_key=key,
        metadata={"legacy_balance": str(amount), "currency": currency},
    )
    return wallet


def ensure_legacy_vendor_available(user, balance, currency):
    amount = Decimal(balance or 0).quantize(Decimal("0.01"))
    key = f"opening:vendor:{user.pk}:{currency}"
    if amount <= 0 or JournalEntry.objects.filter(idempotency_key=key).exists():
        return
    wallet = ensure_wallet(user, Wallet.Kinds.VENDOR_AVAILABLE, currency)
    post_entry(
        "ترحيل رصيد التاجر المتاح من النظام السابق",
        [{"account": ensure_chart()["opening_equity"], "debit": amount}, {"account": wallet.account, "credit": amount}],
        source_type="legacy_vendor_wallet", source_id=user.pk, idempotency_key=key,
        metadata={"legacy_balance": str(amount), "currency": currency},
    )


def fund_order(order, *, created_by=None):
    from orders.models import VendorOrder
    customer = ensure_wallet(order.customer, Wallet.Kinds.CUSTOMER, order.currency)
    vendor_orders = list(VendorOrder.objects.select_related("vendor__owner").filter(order=order).order_by("id"))
    order_total = Decimal(order.total).quantize(Decimal("0.01"))
    lines = [{"account": customer.account, "debit": order_total, "description": f"خصم/حجز طلب {order.order_number}"}]
    allocated = Decimal("0.00")
    commission = Decimal("0.00")
    for vendor_order in vendor_orders:
        net = Decimal(vendor_order.vendor_net).quantize(Decimal("0.01"))
        commission += Decimal(vendor_order.commission).quantize(Decimal("0.01"))
        allocated += net
        if net > 0:
            pending = ensure_wallet(vendor_order.vendor.owner, Wallet.Kinds.VENDOR_PENDING, order.currency)
            lines.append({"account": pending.account, "credit": net, "description": f"مستحق معلق للطلب {vendor_order.order_number}"})
    if commission > 0:
        lines.append({"account": ensure_chart()["commission_income"], "credit": commission, "description": f"عمولة طلب {order.order_number}"})
    if allocated + commission != order_total:
        raise ValueError(f"لا يمكن ترحيل الطلب محاسبيًا: صافي التاجر {allocated} + العمولة {commission} != إجمالي الطلب {order_total}.")
    return post_entry(
        f"تمويل وحجز الطلب {order.order_number}", lines,
        source_type="order", source_id=order.pk, idempotency_key=f"order:fund:{order.pk}", created_by=created_by,
        metadata={"order_total": str(order_total), "currency": order.currency},
    )


def release_vendor_pending(vendor_user, amount, currency, *, vendor_order_id, created_by=None):
    amount = Decimal(amount).quantize(Decimal("0.01"))
    if amount <= 0:
        return None
    pending = ensure_wallet(vendor_user, Wallet.Kinds.VENDOR_PENDING, currency)
    available = ensure_wallet(vendor_user, Wallet.Kinds.VENDOR_AVAILABLE, currency)
    return post_entry(
        f"تحويل المستحق المعلق إلى الرصيد المتاح للطلب {vendor_order_id}",
        [{"account": pending.account, "debit": amount}, {"account": available.account, "credit": amount}],
        source_type="vendor_order_release", source_id=vendor_order_id,
        idempotency_key=f"vendor-order:release:{vendor_order_id}", created_by=created_by,
    )


def hold_withdrawal(user, amount, currency, *, withdrawal_id, created_by=None):
    amount = Decimal(amount).quantize(Decimal("0.01"))
    available = ensure_wallet(user, Wallet.Kinds.VENDOR_AVAILABLE, currency)
    hold = ensure_wallet(user, Wallet.Kinds.WITHDRAWAL_HOLD, currency)
    return post_entry(
        f"حجز طلب السحب {withdrawal_id}",
        [{"account": available.account, "debit": amount}, {"account": hold.account, "credit": amount}],
        source_type="withdrawal_hold", source_id=withdrawal_id, idempotency_key=f"withdrawal:hold:{withdrawal_id}", created_by=created_by,
    )


def settle_withdrawal(user, amount, currency, *, withdrawal_id, created_by=None):
    amount = Decimal(amount).quantize(Decimal("0.01"))
    hold = ensure_wallet(user, Wallet.Kinds.WITHDRAWAL_HOLD, currency)
    cash = ensure_chart()["main_cash"]
    return post_entry(
        f"صرف طلب السحب {withdrawal_id}",
        [{"account": hold.account, "debit": amount}, {"account": cash, "credit": amount}],
        source_type="withdrawal_paid", source_id=withdrawal_id, idempotency_key=f"withdrawal:paid:{withdrawal_id}", created_by=created_by,
    )


def reject_withdrawal(user, amount, currency, *, withdrawal_id, created_by=None):
    amount = Decimal(amount).quantize(Decimal("0.01"))
    hold = ensure_wallet(user, Wallet.Kinds.WITHDRAWAL_HOLD, currency)
    available = ensure_wallet(user, Wallet.Kinds.VENDOR_AVAILABLE, currency)
    return post_entry(
        f"إلغاء حجز طلب السحب {withdrawal_id}",
        [{"account": hold.account, "debit": amount}, {"account": available.account, "credit": amount}],
        source_type="withdrawal_rejected", source_id=withdrawal_id, idempotency_key=f"withdrawal:reject:{withdrawal_id}", created_by=created_by,
    )


def statement_for_user(user, currency="YER", wallet_kinds=None):
    kinds = wallet_kinds or [Wallet.Kinds.CUSTOMER]
    if getattr(user, "role", None) == "vendor" and wallet_kinds is None:
        kinds += [Wallet.Kinds.VENDOR_PENDING, Wallet.Kinds.VENDOR_AVAILABLE, Wallet.Kinds.WITHDRAWAL_HOLD]
    wallets = [ensure_wallet(user, kind, currency) for kind in kinds]
    account_ids = [w.account_id for w in wallets]
    rows = JournalLine.objects.filter(account_id__in=account_ids, entry__status=JournalEntry.Status.POSTED).select_related("account", "entry").order_by("entry__entry_date", "entry_id", "id")
    running = defaultdict(lambda: Decimal("0.00"))
    result = []
    for row in rows:
        running[row.account_id] += Decimal(row.credit) - Decimal(row.debit)
        result.append({"journal": row.entry.number, "date": row.entry.entry_date.isoformat(), "description": row.entry.description, "wallet": row.account.metadata.get("wallet_kind", ""), "account": row.account.code, "debit": str(row.debit), "credit": str(row.credit), "balance": str(running[row.account_id]), "source_type": row.entry.source_type, "source_id": row.entry.source_id})
    return result


def wallet_summary(user, currency="YER"):
    customer = ensure_wallet(user, Wallet.Kinds.CUSTOMER, currency)
    result = {"currency": currency, "customer": {"available": str(wallet_balance(customer))}}
    if getattr(user, "role", None) == "vendor":
        pending = ensure_wallet(user, Wallet.Kinds.VENDOR_PENDING, currency)
        available = ensure_wallet(user, Wallet.Kinds.VENDOR_AVAILABLE, currency)
        hold = ensure_wallet(user, Wallet.Kinds.WITHDRAWAL_HOLD, currency)
        pb, ab, hb = wallet_balance(pending), wallet_balance(available), wallet_balance(hold)
        result["vendor"] = {"pending": str(pb), "available": str(ab), "withdrawal_hold": str(hb), "withdrawable": str(max(Decimal("0.00"), ab)), "total": str(pb + ab)}
    else:
        result["vendor"] = {"pending": "0.00", "available": "0.00", "withdrawal_hold": "0.00", "withdrawable": "0.00", "total": "0.00"}
    return result
