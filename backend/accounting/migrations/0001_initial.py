from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def seed_chart(apps, schema_editor):
    Account = apps.get_model("accounting", "Account")
    roots = [
        ("1000", "الصناديق", "group", "debit"),
        ("2000", "الموظفون", "group", "credit"),
        ("3000", "العملاء", "group", "credit"),
        ("4000", "الموردون والتجار", "group", "credit"),
        ("5000", "حقوق الملكية", "group", "credit"),
        ("6000", "الإيرادات", "group", "credit"),
        ("7000", "المصروفات", "group", "debit"),
    ]
    for code, name, account_type, normal_side in roots:
        Account.objects.get_or_create(code=code, defaults={"name": name, "account_type": account_type, "normal_side": normal_side, "is_group": True})
    equity = Account.objects.get(code="5000")
    income = Account.objects.get(code="6000")
    expense = Account.objects.get(code="7000")
    cash = Account.objects.get(code="1000")
    Account.objects.get_or_create(code="100001", defaults={"name": "الصندوق الرئيسي", "parent_id": cash.id, "account_type": "asset", "normal_side": "debit", "is_group": False})
    Account.objects.get_or_create(code="500001", defaults={"name": "أرصدة افتتاحية وترحيل سابق", "parent_id": equity.id, "account_type": "equity", "normal_side": "credit", "is_group": False})
    Account.objects.get_or_create(code="600001", defaults={"name": "عمولات المنصة", "parent_id": income.id, "account_type": "income", "normal_side": "credit", "is_group": False})
    Account.objects.get_or_create(code="700001", defaults={"name": "استردادات وتسويات الطلبات", "parent_id": expense.id, "account_type": "expense", "normal_side": "debit", "is_group": False})


class Migration(migrations.Migration):
    initial = True
    dependencies = [migrations.swappable_dependency(settings.AUTH_USER_MODEL)]

    operations = [
        migrations.CreateModel(
            name="Account",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("code", models.CharField(max_length=32, unique=True)),
                ("name", models.CharField(max_length=180)),
                ("account_type", models.CharField(choices=[("asset", "أصل"), ("liability", "التزام"), ("equity", "حقوق ملكية"), ("income", "إيراد"), ("expense", "مصروف"), ("group", "مجموعة")], max_length=20)),
                ("normal_side", models.CharField(choices=[("debit", "مدين"), ("credit", "دائن")], max_length=10)),
                ("is_group", models.BooleanField(default=False)),
                ("is_active", models.BooleanField(default=True)),
                ("party_type", models.CharField(blank=True, max_length=20)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("parent", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="children", to="accounting.account")),
                ("party_user", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="accounting_accounts", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["code"]},
        ),
        migrations.CreateModel(
            name="JournalEntry",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("number", models.CharField(max_length=40, unique=True)),
                ("entry_date", models.DateField()),
                ("description", models.CharField(max_length=255)),
                ("status", models.CharField(choices=[("posted", "مرحل"), ("void", "ملغى")], default="posted", max_length=12)),
                ("source_type", models.CharField(blank=True, max_length=80)),
                ("source_id", models.CharField(blank=True, max_length=80)),
                ("idempotency_key", models.CharField(blank=True, max_length=180, null=True, unique=True)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="created_journal_entries", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-entry_date", "-id"]},
        ),
        migrations.CreateModel(
            name="JournalLine",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("description", models.CharField(blank=True, max_length=255)),
                ("debit", models.DecimalField(decimal_places=2, default=0, max_digits=18)),
                ("credit", models.DecimalField(decimal_places=2, default=0, max_digits=18)),
                ("account", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="journal_lines", to="accounting.account")),
                ("entry", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="lines", to="accounting.journalentry")),
            ],
        ),
        migrations.CreateModel(
            name="Wallet",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("kind", models.CharField(choices=[("customer", "محفظة العميل"), ("vendor_pending", "مستحقات التاجر المعلقة"), ("vendor_available", "رصيد التاجر المتاح"), ("withdrawal_hold", "طلبات سحب معلقة")], max_length=24)),
                ("currency", models.CharField(default="YER", max_length=6)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("account", models.OneToOneField(on_delete=django.db.models.deletion.PROTECT, related_name="wallet", to="accounting.account")),
                ("owner", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="accounting_wallets", to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name="Voucher",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("number", models.CharField(max_length=40, unique=True)),
                ("voucher_type", models.CharField(choices=[("receipt", "سند قبض"), ("payment", "سند صرف")], max_length=12)),
                ("voucher_date", models.DateField()),
                ("amount", models.DecimalField(decimal_places=2, max_digits=18)),
                ("currency", models.CharField(default="YER", max_length=6)),
                ("description", models.CharField(blank=True, max_length=255)),
                ("source_type", models.CharField(blank=True, max_length=80)),
                ("source_id", models.CharField(blank=True, max_length=80)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("cash_account", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="cash_vouchers", to="accounting.account")),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL)),
                ("journal_entry", models.OneToOneField(on_delete=django.db.models.deletion.PROTECT, related_name="voucher", to="accounting.journalentry")),
                ("party_account", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="party_vouchers", to="accounting.account")),
            ],
        ),
        migrations.CreateModel(
            name="WithdrawalRequest",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("number", models.CharField(max_length=40, unique=True)),
                ("amount", models.DecimalField(decimal_places=2, max_digits=18)),
                ("currency", models.CharField(default="YER", max_length=6)),
                ("status", models.CharField(choices=[("pending", "معلق"), ("approved", "معتمد"), ("paid", "مصروف"), ("rejected", "مرفوض")], default="pending", max_length=12)),
                ("note", models.TextField(blank=True)),
                ("source_type", models.CharField(blank=True, max_length=80)),
                ("source_id", models.CharField(blank=True, max_length=80)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("hold_journal", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="withdrawal_holds", to="accounting.journalentry")),
                ("requester", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="accounting_withdrawals", to=settings.AUTH_USER_MODEL)),
                ("settlement_journal", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="withdrawal_settlements", to="accounting.journalentry")),
            ],
        ),
        migrations.AddIndex(model_name="account", index=models.Index(fields=["parent", "is_active"], name="acct_parent_active_idx")),
        migrations.AddIndex(model_name="account", index=models.Index(fields=["party_user", "party_type"], name="acct_party_type_idx")),
        migrations.AddIndex(model_name="journalentry", index=models.Index(fields=["source_type", "source_id"], name="acct_je_source_idx")),
        migrations.AddIndex(model_name="journalentry", index=models.Index(fields=["entry_date", "status"], name="acct_je_date_status_idx")),
        migrations.AddIndex(model_name="journalline", index=models.Index(fields=["account", "entry"], name="acct_line_account_entry_idx")),
        migrations.AddIndex(model_name="wallet", index=models.Index(fields=["owner", "kind"], name="acct_wallet_owner_kind_idx")),
        migrations.AddIndex(model_name="withdrawalrequest", index=models.Index(fields=["requester", "status"], name="acct_withdraw_req_status_idx")),
        migrations.AddConstraint(model_name="wallet", constraint=models.UniqueConstraint(fields=("owner", "kind", "currency"), name="uniq_accounting_wallet")),
        migrations.RunPython(seed_chart, migrations.RunPython.noop),
    ]
