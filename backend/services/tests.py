from decimal import Decimal
from unittest.mock import patch
import hashlib

from cryptography.fernet import Fernet
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from accounting.services_v2 import ensure_wallet
from .models import MainServiceCategory, ProviderConnection, ProviderLink, Service, ServiceCategory, ServiceTask, ServiceTransaction
from .provider import ProviderClient
from .security import decrypt_secret


@override_settings(SERVICES_CREDENTIALS_KEY=Fernet.generate_key().decode(), SERVICES_WEBHOOK_BASE_URL="https://shopik.alattab.site")
class ServicePlatformTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.customer = User.objects.create_user(username="svc-customer", password="test-pass-123", phone="777777777", role="customer")
        ensure_wallet(self.customer, "customer", "YER")
        main = MainServiceCategory.objects.create(name="اختبار", slug="test-services")
        category = ServiceCategory.objects.create(main_category=main, name="اتصالات", slug="telecom")
        self.service = Service.objects.create(category=category, name="شحن اختبار", slug="test-recharge", code="TEST_RECHARGE", pricing_mode="fixed", price=Decimal("100.00"))
        self.service.fields.create(key="mobile", label="رقم الهاتف", required=True, validation={"min_length": 9, "max_length": 9})
        provider = ProviderConnection.objects.create(name="مزود الاختبار", code="test-provider", connection_type="sanaacash", base_url="https://example.invalid/api/yr/", userid="u", username="user", timeout_seconds=1)
        provider.set_password("pass")
        provider.save()
        self.link = ProviderLink.objects.create(provider=provider, name="شحن", code="test-link", path_template="yem", operation="bill", field_map={"amount": "amount"}, status_path_template="info", status_params={"action": "status"}, success_codes=["0"], pending_codes=["-2"])
        self.service.distributions.create(provider_link=self.link, priority=1)
        self.client = APIClient()
        self.client.force_authenticate(self.customer)

    def test_catalog_and_request_reserves_only(self):
        response = self.client.get("/api/v2/services/catalog/")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["categories"])
        with patch("services.api.reserve_service_funds") as reserve:
            reserve.return_value = type("JournalStub", (), {"pk": 1})()
            response = self.client.post("/api/v2/services/requests/", {"service_id": self.service.pk, "payload": {"mobile": "777777777"}}, format="json")
        self.assertEqual(response.status_code, 202)
        self.assertTrue(reserve.called)
        self.assertTrue(ServiceTask.objects.filter(transaction_id=response.data["id"]).exists())
        tx = ServiceTransaction.objects.get(pk=response.data["id"])
        self.assertTrue(decrypt_secret(tx.webhook_secret_encrypted))

    def test_token_matches_contract(self):
        token = ProviderClient.sanaacash_token("secret", "123", "login", "777777777")
        h = hashlib.md5(b"secret").hexdigest()
        expected = hashlib.md5((h + "123" + "login" + "777777777").encode()).hexdigest()
        self.assertEqual(token, expected)

    def test_insufficient_balance_rejects_request(self):
        response = self.client.post("/api/v2/services/requests/", {"service_id": self.service.pk, "payload": {"mobile": "777777777"}}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertFalse(ServiceTransaction.objects.exists())

    def test_provider_params_include_backpass_and_backurl(self):
        tx = ServiceTransaction.objects.create(customer=self.customer, service=self.service, customer_amount=Decimal("100"), mobile="777777777", provider_transaction_id="TX-1", webhook_secret_encrypted=__import__("services.security", fromlist=["encrypt_secret"]).encrypt_secret("secret-backpass"))
        params, _ = ProviderClient(self.link.provider)._params(self.link, tx)
        self.assertEqual(params["userid"], "u")
        self.assertEqual(params["backpass"], "secret-backpass")
        self.assertEqual(params["backurl"], "https://shopik.alattab.site/api/v2/services/webhook/sanaacash/")

    def test_sanaacash_webhook_rejects_wrong_backpass(self):
        tx = ServiceTransaction.objects.create(customer=self.customer, service=self.service, customer_amount=Decimal("100"), mobile="777777777", provider_transaction_id="WEB-1", webhook_secret_encrypted=__import__("services.security", fromlist=["encrypt_secret"]).encrypt_secret("correct"))
        response = self.client.get("/api/v2/services/webhook/sanaacash/", {"action": "done", "backpass": "wrong", "transid": tx.provider_transaction_id})
        self.assertEqual(response.status_code, 403)
        tx.refresh_from_db()
        self.assertNotEqual(tx.status, ServiceTransaction.Status.SUCCESS)

    def test_sanaacash_webhook_finalizes_done(self):
        tx = ServiceTransaction.objects.create(customer=self.customer, service=self.service, customer_amount=Decimal("100"), mobile="777777777", provider_transaction_id="WEB-2", status=ServiceTransaction.Status.PENDING_PROVIDER, webhook_secret_encrypted=__import__("services.security", fromlist=["encrypt_secret"]).encrypt_secret("correct"))
        with patch("services.webhook.settle_service") as settle:
            settle.return_value = type("JournalStub", (), {"pk": 44})()
            response = self.client.get("/api/v2/services/webhook/sanaacash/", {"action": "done", "backpass": "correct", "transid": tx.provider_transaction_id, "message": "ok"})
        self.assertEqual(response.status_code, 200)
        tx.refresh_from_db()
        self.assertEqual(tx.status, ServiceTransaction.Status.SUCCESS)
        self.assertEqual(tx.settled_journal_id, 44)
        self.assertIsNotNone(tx.webhook_received_at)

    def test_sanaacash_webhook_finalizes_ban_with_refund(self):
        tx = ServiceTransaction.objects.create(customer=self.customer, service=self.service, customer_amount=Decimal("100"), mobile="777777777", provider_transaction_id="WEB-3", status=ServiceTransaction.Status.PENDING_PROVIDER, webhook_secret_encrypted=__import__("services.security", fromlist=["encrypt_secret"]).encrypt_secret("correct"))
        with patch("services.webhook.refund_service") as refund:
            refund.return_value = type("JournalStub", (), {"pk": 45})()
            response = self.client.get("/api/v2/services/webhook/sanaacash/", {"action": "ban", "backpass": "correct", "transid": tx.provider_transaction_id, "message": "banned"})
        self.assertEqual(response.status_code, 200)
        tx.refresh_from_db()
        self.assertEqual(tx.status, ServiceTransaction.Status.REFUNDED)
        self.assertEqual(tx.refund_journal_id, 45)
        self.assertEqual(tx.error_code, "PROVIDER_BAN")
