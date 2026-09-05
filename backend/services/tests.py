from decimal import Decimal
from unittest.mock import patch
import hashlib

from cryptography.fernet import Fernet
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from accounting.services_v2 import ensure_wallet
from .models import MainServiceCategory, ProviderConnection, ProviderLink, Service, ServiceCategory, ServiceTask, ServiceTransaction, TelecomDenomination
from .provider import ProviderClient
from .provider_setup import create_or_update_sanaacash_provider
from .security import decrypt_secret
from .management.commands.provision_sanaacash import provision


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
        self.provider = provider
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

    def test_generic_provider_template_is_independent(self):
        provider = create_or_update_sanaacash_provider(code="backup-provider", name="مزود احتياطي", userid="u2", domain_name="api2.example", username="login2", password="secret2", note="مزود احتياطي للإنتاج", base_url="https://api2.example/api/yr/")
        self.assertEqual(provider.name, "مزود احتياطي")
        self.assertEqual(provider.base_url, "https://api2.example/api/yr/")
        self.assertEqual(provider.metadata.get("note"), "مزود احتياطي للإنتاج")
        self.assertEqual(provider.get_password(), "secret2")
        self.assertTrue(provider.links.filter(is_active=True).exists())
        self.assertEqual(provider.links.get(operation="games_cards").provider_id, provider.id)
        self.assertTrue(provider.links.get(operation="games_cards").distributions.filter(is_active=True).exists())
        provider_again = create_or_update_sanaacash_provider(code="backup-provider", name="مزود احتياطي", userid="u2", domain_name="api2.example", username="login2", password="secret2", note="مزود احتياطي للإنتاج", base_url="https://api2.example/api/yr/")
        self.assertEqual(provider_again.pk, provider.pk)
        self.assertEqual(MainServiceCategory.objects.count(), 4)

    def test_provision_is_compatible_with_migration_seed(self):
        provision()
        provision()
        self.assertEqual(MainServiceCategory.objects.get(slug="payments").name, "التسديدات")
        self.assertEqual(MainServiceCategory.objects.get(slug="games").name, "الألعاب")
        self.assertEqual(MainServiceCategory.objects.get(slug="software").name, "البرامج والبطاقات")
        self.assertEqual(Service.objects.count(), 58)
        self.assertEqual(ServiceCategory.objects.count(), 13)

    def test_item_catalog_data_is_hydrated_server_side(self):
        service = Service.objects.create(category=self.service.category, name="فئات يمن موبايل", slug="yem-denomination-test", code="YEM_DENOM_TEST", pricing_mode="item")
        service.fields.create(key="mobile", label="رقم الهاتف", required=True, validation={"min_length": 9, "max_length": 9})
        service.fields.create(key="external_code", label="كود المنتج", required=False)
        service.fields.create(key="amount", label="قيمة الفئة", field_type="decimal", required=False)
        item = TelecomDenomination.objects.create(service=service, name="100 ريال", external_code="100", face_value=Decimal("100"), sale_price=Decimal("105"))
        with patch("services.api.reserve_service_funds") as reserve:
            reserve.return_value = type("JournalStub", (), {"pk": 7})()
            response = self.client.post("/api/v2/services/requests/", {"service_id": service.pk, "item_id": item.pk, "item_type": "telecom_denominations", "payload": {"mobile": "777777777"}}, format="json")
        self.assertEqual(response.status_code, 202)
        tx = ServiceTransaction.objects.get(pk=response.data["id"])
        self.assertEqual(tx.payload["external_code"], "100")
        self.assertEqual(tx.payload["amount"], "100.00")

    def test_provider_params_include_backpass_and_backurl(self):
        tx = ServiceTransaction.objects.create(customer=self.customer, service=self.service, customer_amount=Decimal("100"), mobile="777777777", provider_transaction_id="TX-1", webhook_secret_encrypted=__import__("services.security", fromlist=["encrypt_secret"]).encrypt_secret("secret-backpass"))
        params, _ = ProviderClient(self.link.provider)._params(self.link, tx)
        self.assertEqual(params["userid"], "u")
        self.assertEqual(params["backpass"], "secret-backpass")
        self.assertEqual(params["backurl"], "https://shopik.alattab.site/api/v2/services/webhook/sanaacash/")

    @patch("services.provider.requests.get")
    def test_provider_balance_matches_contract(self, get):
        response = type("ResponseStub", (), {"status_code": 200, "text": '{"resultCode":"0","balance":"12345.50"}', "json": lambda self: {"resultCode": "0", "balance": "12345.50"}})()
        get.return_value = response
        result = ProviderClient(self.provider).check_balance()
        self.assertTrue(result.success)
        self.assertEqual(result.response["balance"], "12345.50")
        kwargs = get.call_args.kwargs
        self.assertEqual(kwargs["params"]["userid"], "u")
        self.assertEqual(kwargs["params"]["action"], "balance")
        self.assertEqual(kwargs["params"]["mobile"], "0")
        self.assertTrue(kwargs["params"]["transid"].startswith("BAL-"))
        self.assertEqual(kwargs["url"] if "url" in kwargs else get.call_args.args[0], "https://example.invalid/api/yr/info")

    @patch("services.provider.requests.get")
    def test_provider_balance_does_not_create_transaction(self, get):
        get.return_value = type("ResponseStub", (), {"status_code": 200, "text": '{"resultCode":"0","balance":"99"}', "json": lambda self: {"resultCode": "0", "balance": "99"}})()
        before = ServiceTransaction.objects.count()
        result = ProviderClient(self.provider).check_balance()
        self.assertTrue(result.success)
        self.assertEqual(ServiceTransaction.objects.count(), before)

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
