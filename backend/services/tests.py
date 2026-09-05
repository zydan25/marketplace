import hashlib
from decimal import Decimal
from unittest.mock import patch

from cryptography.fernet import Fernet
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from accounting.services_v2 import ensure_wallet
from .catalog_data import CATEGORIES, LINKS, SERVICES, SABA_DENOMINATIONS, SABA_OFFERS, YOU_DENOMINATIONS, YOU_OFFERS, YEMEN_MOBILE_OFFERS
from .models import MainServiceCategory, ProviderConnection, ProviderLink, Service, ServiceDistribution, ServiceRequestReference, ServiceTask, ServiceTransaction, TelecomDenomination
from .provider import ProviderClient
from .provider_setup import create_or_update_sanaacash_provider
from .security import decrypt_secret, encrypt_secret
from .management.commands.provision_sanaacash import provision


@override_settings(SERVICES_CREDENTIALS_KEY=Fernet.generate_key().decode(), SERVICES_WEBHOOK_BASE_URL="https://shopik.alattab.site")
class ServicePlatformTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.customer = User.objects.create_user(username="svc-customer", password="test-pass-123", phone="777777777", role="customer")
        ensure_wallet(self.customer, "customer", "YER")
        main = MainServiceCategory.objects.create(name="اختبار", slug="test-services")
        category = __import__("services.models", fromlist=["ServiceCategory"]).ServiceCategory.objects.create(main_category=main, name="اتصالات", slug="telecom")
        self.service = Service.objects.create(category=category, name="شحن اختبار", slug="test-recharge", code="TEST_RECHARGE", pricing_mode="fixed", price=Decimal("100.00"))
        self.service.fields.create(key="mobile", label="رقم الهاتف", required=True, validation={"min_length": 9, "max_length": 9})
        provider = ProviderConnection.objects.create(name="مزود الاختبار", code="test-provider", connection_type="sanaacash", base_url="https://example.invalid/api/yr/", userid="u", username="user", timeout_seconds=1)
        provider.set_password("pass")
        provider.save()
        self.provider = provider
        self.link = ProviderLink.objects.create(provider=provider, name="شحن", code="test-link", path_template="yem", operation="test", request_encoding="query", field_map={"mobile": "mobile", "amount": "amount"}, status_path_template="info", status_params={"action": "status"}, success_codes=["0"], pending_codes=["-2"])
        ServiceDistribution.objects.create(service=self.service, provider_link=self.link, priority=1)
        self.client = APIClient()
        self.client.force_authenticate(self.customer)

    def test_token_matches_contract(self):
        token = ProviderClient.sanaacash_token("secret", "12345", "login", "777777777")
        h = hashlib.md5(b"secret").hexdigest()
        expected = hashlib.md5((h + "12345" + "login" + "777777777").encode()).hexdigest()
        self.assertEqual(token, expected)

    def test_numeric_transid_is_random_unique_and_persisted(self):
        first = ProviderClient.new_numeric_transid(self.provider, request_kind="test")
        second = ProviderClient.new_numeric_transid(self.provider, request_kind="test")
        self.assertGreaterEqual(first, 10000)
        self.assertGreaterEqual(second, 10000)
        self.assertNotEqual(first, second)
        self.assertTrue(str(first).isdigit())
        self.assertTrue(ServiceRequestReference.objects.filter(transid=first, provider=self.provider).exists())
        self.assertTrue(ServiceRequestReference.objects.filter(transid=second, provider=self.provider).exists())

    @patch("services.provider.requests.get")
    def test_provider_balance_uses_integer_transid(self, get):
        get.return_value = type("ResponseStub", (), {"status_code": 200, "text": '{"resultCode":"0","balance":"12345.50"}', "json": lambda self: {"resultCode": "0", "balance": "12345.50"}})()
        result = ProviderClient(self.provider).check_balance()
        self.assertTrue(result.success)
        params = get.call_args.kwargs["params"]
        self.assertTrue(params["transid"].isdigit())
        self.assertGreaterEqual(int(params["transid"]), 10000)
        self.assertEqual(params["action"], "balance")
        self.assertEqual(params["mobile"], "0")
        self.assertTrue(ServiceRequestReference.objects.filter(transid=int(params["transid"]), provider=self.provider).exists())

    @patch("services.provider.requests.post")
    def test_post_form_is_sent_in_body(self, post):
        post.return_value = type("ResponseStub", (), {"status_code": 200, "text": '{"resultCode":"0"}', "json": lambda self: {"resultCode": "0"}})()
        link = ProviderLink.objects.create(provider=self.provider, name="كهرباء", code="electric-test", path_template="electwater", operation="electric_bill", http_method="POST", request_encoding="form", fixed_params={"action": "bill", "act": "elect"}, field_map={"customer_id": "customer_id", "placeid": "placeid", "amount": "amount"}, success_codes=["0"], pending_codes=["-2"])
        tx = ServiceTransaction.objects.create(customer=self.customer, service=self.service, customer_amount=Decimal("100"), mobile="777777777", provider_transid=12345, provider_transaction_id="12345", payload={"customer_id": "55", "placeid": "2", "amount": "100"})
        ProviderClient(self.provider).call(link, tx)
        self.assertEqual(post.call_args.kwargs["data"]["customer_id"], "55")
        self.assertNotIn("params", post.call_args.kwargs)

    def test_free_query_request_does_not_reserve_funds(self):
        query = Service.objects.create(category=self.service.category, name="استعلام", slug="query-test", code="QUERY_TEST", service_kind="query", requires_balance=False, pricing_mode="fixed", price=Decimal("0"))
        query.fields.create(key="mobile", label="رقم الهاتف", required=True, validation={"min_length": 9, "max_length": 9})
        with patch("services.api.reserve_service_funds") as reserve:
            response = self.client.post("/api/v2/services/requests/", {"service_id": query.pk, "payload": {"mobile": "777777777"}}, format="json")
        self.assertEqual(response.status_code, 202)
        reserve.assert_not_called()
        tx = ServiceTransaction.objects.get(pk=response.data["id"])
        self.assertEqual(tx.customer_amount, Decimal("0.00"))

    def test_item_value_is_hydrated_server_side(self):
        service = Service.objects.create(category=self.service.category, name="فئة", slug="item-test", code="ITEM_TEST", pricing_mode="item")
        service.fields.create(key="mobile", label="رقم الهاتف", required=True, validation={"min_length": 9, "max_length": 9})
        service.fields.create(key="external_code", label="كود المنتج", required=False)
        item = TelecomDenomination.objects.create(service=service, name="100 ريال", external_code="100", face_value=100, sale_price=105, metadata={"provider_num": "8"})
        with patch("services.api.reserve_service_funds") as reserve:
            reserve.return_value = type("JournalStub", (), {"pk": 7})()
            response = self.client.post("/api/v2/services/requests/", {"service_id": service.pk, "item_id": item.pk, "item_type": "telecom_denominations", "payload": {"mobile": "777777777", "external_code": "999"}}, format="json")
        self.assertEqual(response.status_code, 202)
        tx = ServiceTransaction.objects.get(pk=response.data["id"])
        self.assertEqual(tx.payload["external_code"], "100")
        self.assertEqual(tx.payload["num"], "8")
        self.assertTrue(reserve.called)

    def test_games_type_is_service_code_not_user_supplied(self):
        service = Service.objects.create(category=self.service.category, name="PUBG", slug="pubg-test", code="pubg", pricing_mode="item")
        for key in ("mobile", "uniqcode", "playerid"):
            service.fields.create(key=key, label=key, required=True)
        provider_link = ProviderLink.objects.create(provider=self.provider, name="Games", code="games-test", path_template="gameswcards", operation="games_cards", field_map={"type": "{{service.code}}", "uniqcode": "uniqcode", "playerid": "playerid", "mobile": "mobile"}, success_codes=["0"], pending_codes=["-2"])
        ServiceDistribution.objects.create(service=service, provider_link=provider_link)
        tx = ServiceTransaction.objects.create(customer=self.customer, service=service, customer_amount=Decimal("100"), mobile="777777777", provider_transid=12346, provider_transaction_id="12346", payload={"uniqcode": "u1", "playerid": "p1"})
        params, _ = ProviderClient(self.provider)._params(provider_link, tx)
        self.assertEqual(params["type"], "pubg")

    def test_provision_is_idempotent_and_seeds_catalog(self):
        provision()
        provision()
        self.assertEqual(MainServiceCategory.objects.filter(slug__in=[slug for _, slug, _ in __import__("services.catalog_data", fromlist=["MAIN"]).MAIN.values()]).count(), 3)
        self.assertEqual(Service.objects.filter(code__in=[row[0] for row in SERVICES]).count(), len(SERVICES))
        self.assertEqual(TelecomDenomination.objects.filter(service__code="you-denomination").count(), len(YOU_DENOMINATIONS))
        self.assertEqual(TelecomDenomination.objects.filter(service__code="saba-denomination").count(), len(SABA_DENOMINATIONS))
        self.assertEqual(__import__("services.models", fromlist=["TelecomPlan"]).TelecomPlan.objects.filter(service__code="saba-offer").count(), len(SABA_OFFERS))
        self.assertEqual(__import__("services.models", fromlist=["TelecomPlan"]).TelecomPlan.objects.filter(service__code="yem-bill-offer").count(), len(YEMEN_MOBILE_OFFERS))

    def test_provider_setup_creates_routes_and_distributions(self):
        provider = create_or_update_sanaacash_provider(code="backup-provider", name="مزود احتياطي", userid="u2", username="login2", password="secret2", base_url="https://api2.example/api/yr/")
        self.assertTrue(provider.links.filter(is_active=True).count() >= len(LINKS))
        self.assertTrue(provider.links.filter(operation="games_cards").exists())
        self.assertTrue(ServiceDistribution.objects.filter(provider_link__provider=provider, is_active=True).exists())
        self.assertEqual(provider.get_password(), "secret2")

    def test_webhook_done_works_for_numeric_transid(self):
        tx = ServiceTransaction.objects.create(customer=self.customer, service=self.service, customer_amount=Decimal("100"), mobile="777777777", provider_transid=12347, provider_transaction_id="12347", status=ServiceTransaction.Status.PENDING_PROVIDER, webhook_secret_encrypted=encrypt_secret("correct"))
        with patch("services.webhook.settle_service") as settle:
            settle.return_value = type("JournalStub", (), {"pk": 44})()
            response = self.client.get("/api/v2/services/webhook/sanaacash/", {"action": "done", "backpass": "correct", "transid": "12347", "message": "ok"})
        self.assertEqual(response.status_code, 200)
        tx.refresh_from_db()
        self.assertEqual(tx.status, ServiceTransaction.Status.SUCCESS)
        self.assertEqual(tx.settled_journal_id, 44)

    def test_webhook_rejects_invalid_backpass(self):
        tx = ServiceTransaction.objects.create(customer=self.customer, service=self.service, customer_amount=Decimal("100"), mobile="777777777", provider_transid=12348, provider_transaction_id="12348", status=ServiceTransaction.Status.PENDING_PROVIDER, webhook_secret_encrypted=encrypt_secret("correct"))
        response = self.client.get("/api/v2/services/webhook/sanaacash/", {"action": "done", "backpass": "wrong", "transid": "12348"})
        self.assertEqual(response.status_code, 403)
        tx.refresh_from_db()
        self.assertNotEqual(tx.status, ServiceTransaction.Status.SUCCESS)
