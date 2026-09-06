from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from accounting.models import JournalEntry, Wallet as AccountingWallet
from accounting.services_v2 import ensure_legacy_customer_opening, ensure_wallet, wallet_balance
from accounting.transfer_service import transfer_between_users
from marketplace.models import User
from marketplace.models_extra import GiftTransfer
from finance.models import Wallet as FinanceWallet
from finance.unified_wallet import sync_finance_projection
from services.models import MainServiceCategory, Service, ServiceCategory, ServiceOption


@override_settings(
    SERVICES_CREDENTIALS_KEY="ZHVtbXkta2V5LWR1bW15LWR1bW15LWR1bW15LWR1bW15",
    SERVICES_WEBHOOK_BASE_URL="https://shopik.alattab.site",
)
class UnifiedWalletTests(TestCase):
    def setUp(self):
        self.sender = User.objects.create_user(username="sender", password="Test-pass-123", phone="777777701", role="customer")
        self.receiver = User.objects.create_user(username="receiver", password="Test-pass-123", phone="777777702", role="customer")
        ensure_wallet(self.sender, AccountingWallet.Kinds.CUSTOMER, "YER")
        ensure_wallet(self.receiver, AccountingWallet.Kinds.CUSTOMER, "YER")

    def test_transfer_is_ledger_backed_and_idempotent(self):
        ensure_legacy_customer_opening(self.sender, Decimal("1000"), "YER")
        first = transfer_between_users(
            self.sender,
            self.receiver,
            Decimal("250"),
            "YER",
            source_type="transfer",
            source_id="test:1",
            idempotency_key="transfer-test-001",
            created_by=self.sender,
        )
        second = transfer_between_users(
            self.sender,
            self.receiver,
            Decimal("250"),
            "YER",
            source_type="transfer",
            source_id="test:1",
            idempotency_key="transfer-test-001",
            created_by=self.sender,
        )
        self.assertEqual(first.pk, second.pk)
        self.assertEqual(wallet_balance(ensure_wallet(self.sender, AccountingWallet.Kinds.CUSTOMER, "YER")), Decimal("750.00"))
        self.assertEqual(wallet_balance(ensure_wallet(self.receiver, AccountingWallet.Kinds.CUSTOMER, "YER")), Decimal("250.00"))
        self.assertEqual(JournalEntry.objects.filter(idempotency_key="transfer-test-001").count(), 1)

    def test_legacy_finance_balance_cannot_be_modified_directly(self):
        wallet = FinanceWallet.objects.create(user=self.sender, currency="YER", balance=Decimal("0"))
        wallet.balance = Decimal("100")
        with self.assertRaises(ValidationError):
            wallet.save(update_fields=["balance", "updated_at"])

    def test_finance_projection_matches_accounting(self):
        ensure_legacy_customer_opening(self.sender, Decimal("500"), "YER")
        projection = sync_finance_projection(self.sender, "YER")
        self.assertEqual(projection.balance, Decimal("500.00"))
        self.assertEqual(wallet_balance(ensure_wallet(self.sender, AccountingWallet.Kinds.CUSTOMER, "YER")), Decimal("500.00"))

    def test_legacy_gift_creates_accounting_journal(self):
        ensure_legacy_customer_opening(self.sender, Decimal("1000"), "YER")
        sync_finance_projection(self.sender, "YER")
        sync_finance_projection(self.receiver, "YER")
        client = APIClient()
        client.force_authenticate(self.sender)
        created = client.post(
            "/api/gifts/",
            {"receiver_phone": self.receiver.phone, "amount": "125", "message": "اختبار"},
            format="json",
        )
        self.assertEqual(created.status_code, 201)
        gift = GiftTransfer.objects.get(pk=created.data["id"])
        confirmed = client.post(f"/api/gifts/{gift.pk}/confirm/", {}, format="json")
        self.assertEqual(confirmed.status_code, 200)
        gift.refresh_from_db()
        self.assertEqual(gift.status, GiftTransfer.Status.COMPLETED)
        self.assertTrue(JournalEntry.objects.filter(source_type="gift", source_id=f"gift:{gift.pk}").exists())

    def test_secure_service_request_requires_idempotency(self):
        main = MainServiceCategory.objects.create(name="اختبارات", slug="tests")
        category = ServiceCategory.objects.create(main_category=main, name="خدمات", slug="test-services")
        service = Service.objects.create(
            category=category,
            name="خدمة مدفوعة",
            slug="paid-service",
            code="PAID_TEST",
            service_kind=Service.ServiceKinds.PURCHASE,
            requires_balance=True,
            pricing_mode=Service.PricingModes.ITEM,
            currency="YER",
        )
        service.fields.create(key="mobile", label="الهاتف", required=True, validation={"min_length": 9, "max_length": 9})
        ServiceOption.objects.create(service=service, name="عنصر", external_code="X", provider_num="1", price=100)
        client = APIClient()
        client.force_authenticate(self.sender)
        response = client.post(
            "/api/v2/services/requests/",
            {"service_id": service.pk, "item_type": "service_options", "item_id": 1, "payload": {"mobile": self.sender.phone}},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("idempotency_key", response.data)
