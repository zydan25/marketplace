from decimal import Decimal

from django.db import transaction

from .models import Account, JournalEntry, Wallet
from .services_v2 import account_balance, ensure_wallet, post_entry


def _project_transfer(sender, recipient, amount, currency, entry, source_type):
    from finance.unified_wallet import record_projection_transaction

    incoming_type = "reward" if source_type == "gift" else "top_up"
    record_projection_transaction(
        sender,
        -amount,
        currency,
        transaction_type="payment",
        reference=entry.number,
        note=f"{'هدية' if source_type == 'gift' else 'تحويل'} إلى {recipient.phone}",
        metadata={"accounting_journal": entry.number, "source_type": source_type, "recipient_id": recipient.pk},
    )
    record_projection_transaction(
        recipient,
        amount,
        currency,
        transaction_type=incoming_type,
        reference=f"{entry.number}:receiver",
        note=f"{'هدية' if source_type == 'gift' else 'تحويل'} من {sender.phone}",
        metadata={"accounting_journal": entry.number, "source_type": source_type, "sender_id": sender.pk},
    )


def transfer_between_users(
    sender,
    recipient,
    amount,
    currency="YER",
    *,
    source_type="transfer",
    source_id="",
    note="",
    idempotency_key=None,
    created_by=None,
):
    amount = Decimal(str(amount)).quantize(Decimal("0.01"))
    currency = str(currency or "YER").upper()
    source_type = str(source_type or "transfer").strip() or "transfer"
    if amount <= 0:
        raise ValueError("المبلغ يجب أن يكون أكبر من صفر.")
    if sender.pk == recipient.pk:
        raise ValueError("لا يمكن التحويل إلى الحساب نفسه.")
    if getattr(sender, "role", None) != "customer" or getattr(recipient, "role", None) != "customer":
        raise ValueError("التحويلات والهدايا مخصصة بين حسابات العملاء.")

    with transaction.atomic():
        if idempotency_key:
            existing = JournalEntry.objects.filter(idempotency_key=idempotency_key).first()
            if existing:
                metadata = existing.metadata or {}
                expected = {
                    "sender_id": sender.pk,
                    "recipient_id": recipient.pk,
                    "currency": currency,
                    "amount": str(amount),
                    "source_type": source_type,
                }
                actual = {
                    "sender_id": metadata.get("sender_id"),
                    "recipient_id": metadata.get("recipient_id"),
                    "currency": str(metadata.get("currency", "")).upper(),
                    "amount": str(metadata.get("amount", "")),
                    "source_type": metadata.get("source_type", source_type),
                }
                if actual != expected:
                    raise ValueError("Idempotency-Key سبق استخدامه لعملية مالية مختلفة.")
                # The journal already owns the financial effect. Never project
                # the same transfer a second time when a client retries the
                # request or a reverse proxy repeats it.
                return existing

        source = ensure_wallet(sender, Wallet.Kinds.CUSTOMER, currency)
        target = ensure_wallet(recipient, Wallet.Kinds.CUSTOMER, currency)
        account_ids = sorted([source.account_id, target.account_id])
        locked = {
            account.pk: account
            for account in Account.objects.select_for_update().filter(pk__in=account_ids)
        }
        source_account = locked[source.account_id]
        target_account = locked[target.account_id]
        available = account_balance(source_account)
        if available < amount:
            raise ValueError(f"الرصيد غير كافٍ. المتاح {available} {currency}.")

        metadata = {
            "sender_id": sender.pk,
            "recipient_id": recipient.pk,
            "currency": currency,
            "amount": str(amount),
            "source_type": source_type,
            "source_id": str(source_id or ""),
            "note": note,
        }
        entry = post_entry(
            note or ("تحويل رصيد" if source_type == "transfer" else "إرسال هدية"),
            [
                {"account": source_account, "debit": amount, "description": "خصم من محفظة المرسل"},
                {"account": target_account, "credit": amount, "description": "إضافة إلى محفظة المستلم"},
            ],
            source_type=source_type,
            source_id=source_id or f"{sender.pk}:{recipient.pk}",
            idempotency_key=idempotency_key,
            created_by=created_by or sender,
            metadata=metadata,
        )
        _project_transfer(sender, recipient, amount, currency, entry, source_type)
        return entry


def refund_to_customer(
    customer,
    amount,
    currency,
    *,
    source_account,
    source_type="refund",
    source_id="",
    description="استرداد للعميل",
    idempotency_key=None,
    created_by=None,
):
    amount = Decimal(str(amount)).quantize(Decimal("0.01"))
    if amount <= 0:
        raise ValueError("قيمة الاسترداد يجب أن تكون أكبر من صفر.")
    target = ensure_wallet(customer, Wallet.Kinds.CUSTOMER, currency)
    source = source_account
    if source.is_group:
        raise ValueError("حساب مصدر الاسترداد يجب أن يكون حسابًا فرعيًا.")
    entry = post_entry(
        description,
        [
            {"account": source, "debit": amount},
            {"account": target.account, "credit": amount},
        ],
        source_type=source_type,
        source_id=source_id,
        idempotency_key=idempotency_key,
        created_by=created_by,
        metadata={"customer_id": customer.pk, "currency": str(currency).upper(), "amount": str(amount)},
    )
    from finance.unified_wallet import record_projection_transaction
    record_projection_transaction(
        customer,
        amount,
        currency,
        transaction_type="refund",
        reference=entry.number,
        note=description,
        metadata={"accounting_journal": entry.number, "source_type": source_type},
    )
    return entry
