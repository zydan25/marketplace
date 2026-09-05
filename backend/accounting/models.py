from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class Account(models.Model):
    class Types(models.TextChoices):
        ASSET = "asset", "أصل"
        LIABILITY = "liability", "التزام"
        EQUITY = "equity", "حقوق ملكية"
        INCOME = "income", "إيراد"
        EXPENSE = "expense", "مصروف"
        GROUP = "group", "مجموعة"

    class NormalSides(models.TextChoices):
        DEBIT = "debit", "مدين"
        CREDIT = "credit", "دائن"

    code = models.CharField(max_length=32, unique=True)
    name = models.CharField(max_length=180)
    parent = models.ForeignKey("self", null=True, blank=True, on_delete=models.PROTECT, related_name="children")
    account_type = models.CharField(max_length=20, choices=Types.choices)
    normal_side = models.CharField(max_length=10, choices=NormalSides.choices)
    is_group = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    party_type = models.CharField(max_length=20, blank=True)
    party_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="accounting_accounts",
    )
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["code"]
        indexes = [
            models.Index(fields=["parent", "is_active"], name="acct_parent_active_idx"),
            models.Index(fields=["party_user", "party_type"], name="acct_party_type_idx"),
        ]

    def clean(self):
        if self.parent_id and self.parent_id == self.id:
            raise ValidationError({"parent": "لا يمكن أن يكون الحساب أبًا لنفسه."})
        if self.is_group and self.party_user_id:
            raise ValidationError({"party_user": "الحسابات الرئيسية لا ترتبط بمستخدم."})
        if self.is_group and not self.parent_id and self.account_type != self.Types.GROUP:
            raise ValidationError({"account_type": "الحساب الجذر يجب أن يكون من نوع مجموعة."})

    def __str__(self):
        return f"{self.code} - {self.name}"


class Wallet(models.Model):
    class Kinds(models.TextChoices):
        CUSTOMER = "customer", "محفظة العميل"
        VENDOR_PENDING = "vendor_pending", "مستحقات التاجر المعلقة"
        VENDOR_AVAILABLE = "vendor_available", "رصيد التاجر المتاح"
        WITHDRAWAL_HOLD = "withdrawal_hold", "طلبات سحب معلقة"

    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="accounting_wallets")
    kind = models.CharField(max_length=24, choices=Kinds.choices)
    currency = models.CharField(max_length=6, default="YER")
    account = models.OneToOneField(Account, on_delete=models.PROTECT, related_name="wallet")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["owner", "kind", "currency"], name="uniq_accounting_wallet")
        ]
        indexes = [models.Index(fields=["owner", "kind"], name="acct_wallet_owner_kind_idx")]

    def __str__(self):
        return f"{self.owner} / {self.get_kind_display()} / {self.currency}"


class JournalEntry(models.Model):
    class Status(models.TextChoices):
        POSTED = "posted", "مرحل"
        VOID = "void", "ملغى"

    number = models.CharField(max_length=40, unique=True)
    entry_date = models.DateField()
    description = models.CharField(max_length=255)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.POSTED)
    source_type = models.CharField(max_length=80, blank=True)
    source_id = models.CharField(max_length=80, blank=True)
    idempotency_key = models.CharField(max_length=180, unique=True, null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT, related_name="created_journal_entries"
    )
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-entry_date", "-id"]
        indexes = [
            models.Index(fields=["source_type", "source_id"], name="acct_je_source_idx"),
            models.Index(fields=["entry_date", "status"], name="acct_je_date_status_idx"),
        ]

    def __str__(self):
        return f"{self.number} - {self.description}"


class JournalLine(models.Model):
    entry = models.ForeignKey(JournalEntry, on_delete=models.PROTECT, related_name="lines")
    account = models.ForeignKey(Account, on_delete=models.PROTECT, related_name="journal_lines")
    description = models.CharField(max_length=255, blank=True)
    debit = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal("0.00"))
    credit = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal("0.00"))

    class Meta:
        indexes = [
            models.Index(fields=["account", "entry"], name="acct_line_account_entry_idx"),
        ]

    def clean(self):
        debit = Decimal(self.debit or 0)
        credit = Decimal(self.credit or 0)
        if debit < 0 or credit < 0:
            raise ValidationError("قيم المدين والدائن لا يمكن أن تكون سالبة.")
        if (debit > 0) == (credit > 0):
            raise ValidationError("كل سطر يجب أن يكون مدينًا أو دائنًا فقط.")
        if self.account_id and self.account.is_group:
            raise ValidationError({"account": "لا يمكن استخدام الحساب الرئيسي في القيد؛ اختر الحساب الفرعي."})


class Voucher(models.Model):
    class Types(models.TextChoices):
        RECEIPT = "receipt", "سند قبض"
        PAYMENT = "payment", "سند صرف"

    number = models.CharField(max_length=40, unique=True)
    voucher_type = models.CharField(max_length=12, choices=Types.choices)
    voucher_date = models.DateField()
    amount = models.DecimalField(max_digits=18, decimal_places=2)
    currency = models.CharField(max_length=6, default="YER")
    cash_account = models.ForeignKey(Account, on_delete=models.PROTECT, related_name="cash_vouchers")
    party_account = models.ForeignKey(Account, on_delete=models.PROTECT, related_name="party_vouchers")
    journal_entry = models.OneToOneField(JournalEntry, on_delete=models.PROTECT, related_name="voucher")
    description = models.CharField(max_length=255, blank=True)
    source_type = models.CharField(max_length=80, blank=True)
    source_id = models.CharField(max_length=80, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)


class WithdrawalRequest(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "معلق"
        APPROVED = "approved", "معتمد"
        PAID = "paid", "مصروف"
        REJECTED = "rejected", "مرفوض"

    number = models.CharField(max_length=40, unique=True)
    requester = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="accounting_withdrawals")
    amount = models.DecimalField(max_digits=18, decimal_places=2)
    currency = models.CharField(max_length=6, default="YER")
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PENDING)
    note = models.TextField(blank=True)
    source_type = models.CharField(max_length=80, blank=True)
    source_id = models.CharField(max_length=80, blank=True)
    hold_journal = models.ForeignKey(JournalEntry, null=True, blank=True, on_delete=models.PROTECT, related_name="withdrawal_holds")
    settlement_journal = models.ForeignKey(JournalEntry, null=True, blank=True, on_delete=models.PROTECT, related_name="withdrawal_settlements")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["requester", "status"], name="acct_withdraw_req_status_idx"),
        ]
