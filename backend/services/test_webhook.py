from decimal import Decimal

from cryptography.fernet import Fernet
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from accounting.models import Wallet as AccountingWallet
from accounting.services_v2 import ensure_legacy_customer_opening, ensure_wallet, wallet_balance
from marketplace.models import User

from .accounting_bridge import reserve_service_funds
from .models import MainServiceCategory, Service, ServiceCategory, ServiceTransaction
from .security import encrypt_secret


@override_settings(SERVICES_CREDENTIALS_KEY=Fernet.generate_key().decode())
class SanaacashWebhookTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="webhook-user", password="Test-pass-123", phone="777700111", role="customer")
        ensure_wallet(self.user, AccountingWallet.Kinds.CUSTOMER, "YER")
        ensure_legacy_customer_opening(self.user, Decimal("1000"), "YER")
        main = MainServiceCategory.objects.create(name="Webhook", slug="webhook-tests")
        category = ServiceCategory.objects.create(main_category=main, name="Services", slug="webhook-services")
        self.service = Service.objects.create(
            category=category,
            name="Webhook paid",
            slug="webhook-paid",
            code="WEBHOOK_PAID_TEST",
            service_kind=Service.ServiceKinds.PURCHASE,
            requires_balance=True,
            pricing_mode=Service.PricingModes.FIXED,
            price=Decimal("100"),
            currency="YER",
        )
        self.tx = ServiceTransaction.objects.create(
            customer=self.user,
            service=self.service,
            customer_amount=Decimal("100"),
            currency="YER",
            mobile=self.user.phone,
            provider_transid=54321,
            provider_transaction_id="54321",
            status=ServiceTransaction.Status.PENDING_PROVIDER,
            webhook_secret_encrypted=encrypt_secret("webhook-secret"),
        )
        journal = reserve_service_funds(self.tx)
        self.tx.reserved_journal_id = journal.pk
        self.tx.save(update_fields=["reserved_journal_id", "updated_at"])
        self.client = APIClient()

    def test_done_finalizes_once_and_replay_is_harmless(self):
        first = self.client.get("/api/v2/services/webhook/sanaacash/", {"action": "done", "backpass": "webhook-secret", "transid": "54321"})
        second = self.client.get("/api/v2/services/webhook/sanaacash/", {"action": "done", "backpass": "webhook-secret", "transid": "54321"})
        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.tx.refresh_from_db()
        self.assertEqual(self.tx.status, ServiceTransaction.Status.SUCCESS)
        self.assertTrue(self.tx.settled_journal_id)
        self.assertEqual(wallet_balance(ensure_wallet(self.user, AccountingWallet.Kinds.CUSTOMER, "YER")), Decimal("900.00"))

    def test_invalid_backpass_cannot_finalize(self):
        response = self.client.get("/api/v2/services/webhook/sanaacash/", {"action": "done", "backpass": "wrong", "transid": "54321"})
        self.assertEqual(response.status_code, 403)
        self.tx.refresh_from_db()
        self.assertEqual(self.tx.status, ServiceTransaction.Status.PENDING_PROVIDER)

    def test_paid_webhook_without_reservation_enters_manual_review(self):
        self.tx.reserved_journal_id = None
        self.tx.save(update_fields=["reserved_journal_id", "updated_at"])
        response = self.client.get("/api/v2/services/webhook/sanaacash/", {"action": "ban", "backpass": "webhook-secret", "transid": "54321"})
        self.assertEqual(response.status_code, 409)
        self.tx.refresh_from_db()
        self.assertEqual(self.tx.status, ServiceTransaction.Status.MANUAL_REVIEW)
