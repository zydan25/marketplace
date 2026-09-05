from decimal import Decimal
from types import SimpleNamespace

from django.contrib.auth import get_user_model
from django.test import TestCase

from .models import Account, JournalEntry, Wallet
from .order_ledger import _item_allocations, item_accounting_amount
from .services_v2 import account_balance, ensure_chart, ensure_wallet, post_entry, wallet_summary


class AccountingCoreTests(TestCase):
    def setUp(self):
        self.User = get_user_model()
        self.customer = self.User.objects.create_user(username="customer-test", phone="967700000001", password="TestPass123", role="customer")
        self.vendor = self.User.objects.create_user(username="vendor-test", phone="967700000002", password="TestPass123", role="vendor")

    def test_chart_has_required_roots_and_hierarchy(self):
        chart = ensure_chart()
        self.assertTrue(Account.objects.filter(code="1000", is_group=True).exists())
        self.assertTrue(Account.objects.filter(code="3000", is_group=True).exists())
        self.assertTrue(Account.objects.filter(code="4000", is_group=True).exists())
        self.assertTrue(Account.objects.filter(code="6000", is_group=True).exists())
        self.assertFalse(chart["main_cash"].is_group)
        wallet = ensure_wallet(self.customer, Wallet.Kinds.CUSTOMER, "YER")
        self.assertTrue(wallet.account.parent.is_group)
        self.assertTrue(wallet.account.parent.party_user_id == self.customer.id)
        self.assertFalse(wallet.account.is_group)

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

    def test_vendor_wallets_are_separate(self):
        summary = wallet_summary(self.vendor, "YER")
        self.assertEqual(summary["vendor"]["pending"], "0.00")
        self.assertEqual(summary["vendor"]["available"], "0.00")
        self.assertEqual(summary["vendor"]["withdrawable"], "0.00")
        self.assertTrue(Wallet.objects.filter(owner=self.vendor, kind=Wallet.Kinds.VENDOR_PENDING).exists())
        self.assertTrue(Wallet.objects.filter(owner=self.vendor, kind=Wallet.Kinds.VENDOR_AVAILABLE).exists())
        self.assertTrue(Wallet.objects.filter(owner=self.vendor, kind=Wallet.Kinds.WITHDRAWAL_HOLD).exists())

    def test_item_allocation_preserves_vendor_order_net_after_shipping_and_discount(self):
        class Items:
            def __init__(self, links):
                self.links = links
            def select_related(self, *args):
                return self
            def order_by(self, *args):
                return self.links

        item1 = SimpleNamespace(id=1, vendor_net=Decimal("90.00"), vendor_total=Decimal("100.00"), commission=Decimal("10.00"))
        item2 = SimpleNamespace(id=2, vendor_net=Decimal("45.00"), vendor_total=Decimal("50.00"), commission=Decimal("5.00"))
        links = [SimpleNamespace(order_item=item1), SimpleNamespace(order_item=item2)]
        vendor_order = SimpleNamespace(vendor_net=Decimal("150.00"), items=Items(links))
        allocations = _item_allocations(vendor_order)
        allocated_net = sum((row[0] for row in allocations.values()), Decimal("0.00"))
        self.assertEqual(allocated_net, Decimal("150.00"))
        self.assertEqual(item_accounting_amount(vendor_order, item1)[2] + item_accounting_amount(vendor_order, item2)[2], Decimal("200.00"))
