from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from .models import Account, JournalEntry, Wallet
from .services import account_balance, ensure_chart, ensure_wallet, post_entry, wallet_summary


class AccountingCoreTests(TestCase):
    def setUp(self):
        self.User = get_user_model()
        self.customer = self.User.objects.create_user(username="customer-test", phone="967700000001", password="TestPass123", role="customer")
        self.vendor = self.User.objects.create_user(username="vendor-test", phone="967700000002", password="TestPass123", role="vendor")

    def test_chart_has_required_roots_and_non_postable_roots(self):
        chart = ensure_chart()
        self.assertTrue(Account.objects.filter(code="1000", is_group=True).exists())
        self.assertTrue(Account.objects.filter(code="3000", is_group=True).exists())
        self.assertTrue(Account.objects.filter(code="4000", is_group=True).exists())
        self.assertTrue(Account.objects.filter(code="6000", is_group=True).exists())
        self.assertTrue(chart["main_cash"].is_group is False)

    def test_customer_wallet_is_leaf_and_journal_changes_balance(self):
        ensure_chart()
        customer_wallet = ensure_wallet(self.customer, Wallet.Kinds.CUSTOMER, "YER")
        cash = Account.objects.get(code="100001")
        post_entry(
            "اختبار شحن العميل",
            [{"account": cash, "debit": Decimal("100.00")}, {"account": customer_wallet.account, "credit": Decimal("100.00")}],
            idempotency_key="test-customer-topup",
        )
        self.assertEqual(account_balance(customer_wallet.account), Decimal("100.00"))
        self.assertFalse(customer_wallet.account.is_group)
        self.assertEqual(JournalEntry.objects.count(), 1)

    def test_vendor_has_pending_and_available_wallets(self):
        summary = wallet_summary(self.vendor, "YER")
        self.assertIn("pending", summary["vendor"])
        self.assertIn("available", summary["vendor"])
        self.assertIn("withdrawable", summary["vendor"])
        self.assertTrue(Wallet.objects.filter(owner=self.vendor, kind=Wallet.Kinds.CUSTOMER).exists())
        self.assertTrue(Wallet.objects.filter(owner=self.vendor, kind=Wallet.Kinds.VENDOR_PENDING).exists())
        self.assertTrue(Wallet.objects.filter(owner=self.vendor, kind=Wallet.Kinds.VENDOR_AVAILABLE).exists())
