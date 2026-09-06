from decimal import Decimal
from unittest.mock import patch

from cryptography.fernet import Fernet
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from accounting.models import Wallet as AccountingWallet
from accounting.services_v2 import ensure_legacy_customer_opening, ensure_wallet, wallet_balance
from marketplace.models import User

from .accounting_bridge import reserve_service_funds
from .models import MainServiceCategory, ProviderConnection, ProviderLink, Service, ServiceCategory, ServiceTask, ServiceTransaction
from .provider import ProviderClient, ProviderResult
from .security import encrypt_secret
from .executor import process_task


@override_settings(
    SERVICES_CREDENTIALS_KEY=Fernet.generate_key().decode(),
    SERVICES_WEBHOOK_BASE_URL="https://shopik.alattab.site",
)
class ServiceSecurityRegressionTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="safe-user", password="Test-pass-123", phone="777700001", role="customer")
        ensure_wallet(self.user, AccountingWallet.Kinds.CUSTOMER, "YER")
        ensure_legacy_customer_opening(self.user, Decimal("1000"), "YER")
        self.main = MainServiceCategory.objects.create(name="أمان", slug="security-tests")
        self.category = ServiceCategory.objects.create(main_category=self.main, name="خدمات", slug="service-tests")
        self.service = Service.objects.create(
            category=self.category,
            name="خدمة مدفوعة",
            slug="secure-paid-service",
            code="SECURE_PAID_TEST",
            service_kind=Service.ServiceKinds.PURCHASE,
            requires_balance=True,
            pricing_mode=Service.PricingModes.FIXED,
            price=Decimal("100"),
            currency="YER",
        )
        self.service.fields.create(key="mobile", label="الهاتف", required=True, validation={"min_length": 9, "max_length": 9})
        self.provider = ProviderConnection.objects.create(
            name="اختبار",
            code="secure-test-provider",
            connection_type="sanaacash",
            base_url="https://example.invalid/api/yr/",
            userid="u",
            username="user",
        )
        self.provider.set_password("password")
        self.provider.save()
        self.link = ProviderLink.objects.create(
            provider=self.provider,
            name="اختبار",
            code="secure-test-link",
            operation="test",
            path_template="test",
            status_path_template="info",
            status_params={"action": "status"},
            success_codes=["0"],
            pending_codes=["-2"],
        )
        from .models import ServiceDistribution
        ServiceDistribution.objects.create(service=self.service, provider_link=self.link, priority=1)
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_paid_request_requires_and_reuses_idempotency_key(self):
        payload = {"service_id": self.service.pk, "payload": {"mobile": self.user.phone}}
        missing = self.client.post("/api/v2/services/requests/", payload, format="json")
        self.assertEqual(missing.status_code, 400)
        first = self.client.post("/api/v2/services/requests/", payload, format="json", HTTP_IDEMPOTENCY_KEY="sec-key-1")
        second = self.client.post("/api/v2/services/requests/", payload, format="json", HTTP_IDEMPOTENCY_KEY="sec-key-1")
        self.assertEqual(first.status_code, 202)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(first.data["id"], second.data["id"])
        self.assertEqual(ServiceTransaction.objects.filter(idempotency_key="sec-key-1").count(), 1)

    def test_idempotency_key_cannot_be_reused_for_different_payload(self):
        base = {"service_id": self.service.pk, "payload": {"mobile": self.user.phone}}
        self.client.post("/api/v2/services/requests/", base, format="json", HTTP_IDEMPOTENCY_KEY="sec-key-2")
        changed = {"service_id": self.service.pk, "payload": {"mobile": "777700009"}}
        response = self.client.post("/api/v2/services/requests/", changed, format="json", HTTP_IDEMPOTENCY_KEY="sec-key-2")
        self.assertEqual(response.status_code, 409)

    def test_webhook_ban_refunds_once(self):
        tx = ServiceTransaction.objects.create(
            customer=self.user,
            service=self.service,
            customer_amount=Decimal("100"),
            mobile=self.user.phone,
            provider_transid=12345,
            provider_transaction_id="12345",
            status=ServiceTransaction.Status.PENDING_PROVIDER,
            webhook_secret_encrypted=encrypt_secret("back-secret"),
        )
        journal = reserve_service_funds(tx)
        tx.reserved_journal_id = journal.pk
        tx.save(update_fields=["reserved_journal_id", "updated_at"])
        before = wallet_balance(ensure_wallet(self.user, AccountingWallet.Kinds.CUSTOMER, "YER"))
        anonymous = APIClient()
        first = anonymous.get("/api/v2/services/webhook/sanaacash/", {"action": "ban", "backpass": "back-secret", "transid": "12345", "message": "رفض"})
        second = anonymous.get("/api/v2/services/webhook/sanaacash/", {"action": "ban", "backpass": "back-secret", "transid": "12345", "message": "رفض"})
        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        tx.refresh_from_db()
        self.assertEqual(tx.status, ServiceTransaction.Status.REFUNDED)
        self.assertEqual(wallet_balance(ensure_wallet(self.user, AccountingWallet.Kinds.CUSTOMER, "YER")), before)
        self.assertTrue(tx.refund_journal_id)

    def _queued_billable_task(self, *, with_status=True):
        link = self.link
        if not with_status:
            link.status_path_template = ""
            link.status_params = {}
            link.save(update_fields=["status_path_template", "status_params", "updated_at"])
        tx = ServiceTransaction.objects.create(
            customer=self.user,
            service=self.service,
            customer_amount=Decimal("100"),
            mobile=self.user.phone,
            status=ServiceTransaction.Status.ACCEPTED,
            webhook_secret_encrypted=encrypt_secret("secret"),
        )
        journal = reserve_service_funds(tx)
        tx.reserved_journal_id = journal.pk
        tx.save(update_fields=["reserved_journal_id", "updated_at"])
        task = ServiceTask.objects.create(transaction=tx, kind=ServiceTask.Kinds.SUBMIT)
        return tx, task, link

    @patch("services.executor.ProviderClient.call")
    def test_network_failure_never_auto_refunds(self, call):
        call.return_value = ProviderResult(code="NETWORK", description="timeout", pending=False, success=False, response={})
        tx, task, _ = self._queued_billable_task(with_status=True)
        process_task(task.pk)
        tx.refresh_from_db()
        self.assertEqual(tx.status, ServiceTransaction.Status.PENDING_PROVIDER)
        self.assertIsNone(tx.refund_journal_id)

    @patch("services.executor.ProviderClient.call")
    def test_pending_without_status_route_goes_to_manual_review(self, call):
        call.return_value = ProviderResult(code="-2", description="under process", pending=True, success=False, response={"resultCode": "-2"})
        tx, task, _ = self._queued_billable_task(with_status=False)
        process_task(task.pk)
        tx.refresh_from_db()
        self.assertEqual(tx.status, ServiceTransaction.Status.MANUAL_REVIEW)
        self.assertIsNone(tx.refund_journal_id)
