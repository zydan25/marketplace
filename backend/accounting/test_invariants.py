from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from accounting.models import Account, JournalEntry, Voucher, Wallet
from accounting.services_v2 import ensure_chart, ensure_wallet, fund_order, post_entry, wallet_balance


class AccountingInvariantTests(TestCase):
    def setUp(self):
        self.User = get_user_model()
        self.user = self.User.objects.create_user(username="acct-test", password="x", role="customer")
        ensure_chart()

    def test_post_entry_rejects_group_accounts(self):
        root = Account.objects.get(code="3000")
        with self.assertRaises(ValueError):
            post_entry("اختبار", [{"account": root, "debit": Decimal("1.00")}, {"account": Account.objects.get(code="600001"), "credit": Decimal("1.00")}])

    def test_voucher_has_one_to_one_journal(self):
        cash = Account.objects.get(code="100001")
        party = Account.objects.create(
            code="300099", name="عميل اختبار", parent=Account.objects.get(code="3000"),
            account_type=Account.Types.LIABILITY, normal_side=Account.NormalSides.CREDIT,
        )
        entry = post_entry("سند قبض اختبار", [{"account": cash, "debit": Decimal("25.00")}, {"account": party, "credit": Decimal("25.00")}], source_type="voucher", source_id="TEST")
        voucher = Voucher.objects.create(
            number="RV-TEST-1", voucher_type=Voucher.Types.RECEIPT, voucher_date="2026-09-05",
            amount=Decimal("25.00"), cash_account=cash, party_account=party, journal_entry=entry,
        )
        self.assertEqual(voucher.journal_entry_id, entry.id)
        self.assertEqual(entry.voucher.id, voucher.id)

    def test_customer_wallet_balance_is_journal_derived(self):
        wallet = ensure_wallet(self.user, Wallet.Kinds.CUSTOMER, "YER")
        opening = Account.objects.get(code="500001")
        post_entry("رصيد افتتاحي", [{"account": opening, "debit": Decimal("100.00")}, {"account": wallet.account, "credit": Decimal("100.00")}], source_type="test", source_id="wallet")
        self.assertEqual(wallet_balance(wallet), Decimal("100.00"))
