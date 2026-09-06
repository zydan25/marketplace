from decimal import Decimal
from unittest.mock import patch

from cryptography.fernet import Fernet
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from accounting.models import Wallet as AccountingWallet
from accounting.services_v2 import ensure_wallet
from marketplace.models import User

from .models import MainServiceCategory, ProviderConnection, ProviderLink, Service, ServiceDistribution, ServiceTask, ServiceTransaction, TelecomDenomination
from .provider import ProviderClient
from .management.commands.provision_sanaacash import create_or_update_sanaacash_provider, LINKS, SERVICES, YEMEN_MOBILE_OFFERS, SABA_OFFERS, YOU_DENOMINATIONS, SABA_DENOMINATIONS
from .management.commands.provision_sanaacash import provision
from .security import encrypt_secret


@override_settings(SERVICES_CREDENTIALS_KEY=Fernet.generate_key().decode())
class ServiceTests(TestCase):
    def setUp(self):
        self.customer = User.objects.create_user(username="service-customer", password="Test-pass-123", phone="777777777", role="customer")
        ensure_wallet(self.customer, AccountingWallet.Kinds.CUSTOMER, "YER")
        self.main = MainServiceCategory.objects.create(name="اختبارات", slug="tests")
        self.category = self.main.categories.create(name="خدمات", slug="services")
        self.service = Service.objects.create(
            category=self.category,
            name="استعلام",
            slug="query-service",
            code="QUERY_TEST",
            service_kind=Service.ServiceKinds.QUERY,
            requires_balance=False,
            pricing_mode=Service.PricingModes.FIXED,
            price=Decimal("0"),
        )
        self.service.fields.create(key="mobile", label="الهاتف", required=True, validation={"min_length": 9, "max_length": 9})
        self.provider = ProviderConnection.objects.create(
            code="provider",
            name="مزود",
            connection_type=ProviderConnection.Types.SANAACASH,
            base_url="https://example.invalid/api/yr/",
            userid="u",
            username="user",
        )
        self.provider.set_password("password")
        self.provider.save()
        self.client = APIClient()
        self.client.force_authenticate(self.customer)

    def test_query_does_not_charge_wallet(self):
        with patch("services.api.reserve_service_funds") as reserve:
            response = self.client.post(
                "/api/v2/services/requests/",
                {"service_id": self.service.pk, "payload": {"mobile": self.customer.phone}},
                format="json",
            )
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
            response = self.client.post(
                "/api/v2/services/requests/",
                {"service_id": service.pk, "item_id": item.pk, "item_type": "telecom_denominations", "payload": {"mobile": "777777777", "external_code": "999"}},
                format="json",
                HTTP_IDEMPOTENCY_KEY="item-test-1",
            )
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
        first = provision()
        second = provision()
        self.assertIsNotNone(first)
        self.assertIsNotNone(second)
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
        paid_service = Service.objects.create(
            category=self.service.category,
            name="خدمة مدفوعة للـWebhook",
            slug="webhook-paid-test",
            code="WEBHOOK_PAID_TEST",
            service_kind=Service.ServiceKinds.PURCHASE,
            requires_balance=True,
            pricing_mode=Service.PricingModes.FIXED,
            price=Decimal("100"),
            currency="YER",
        )
        paid_service.fields.create(key="mobile", label="الهاتف", required=True)
        tx = ServiceTransaction.objects.create(
            customer=self.customer,
            service=paid_service,
            customer_amount=Decimal("100"),
            mobile="777777777",
            provider_transid=12347,
            provider_transaction_id="12347",
            status=ServiceTransaction.Status.PENDING_PROVIDER,
            webhook_secret_encrypted=encrypt_secret("correct"),
            reserved_journal_id=44,
        )
        with patch("services.webhook.settle_service") as settle:
            settle.return_value = type("JournalStub", (), {"pk": 44})()
            response = self.client.get("/api/v2/services/webhook/sanaacash/", {"action": "done", "backpass": "correct", "transid": "12347", "message": "ok"})
        self.assertEqual(response.status_code, 200)
        tx.refresh_from_db()
        self.assertEqual(tx.status, ServiceTransaction.Status.SUCCESS)
        self.assertEqual(tx.settled_journal_id, 44)

    def test_webhook_rejects_invalid_backpass(self):
        tx = ServiceTransaction.objects.create(customer=self.customer, service=self.service, customer_amount=Decimal("100"), mobile="777777777", provider_transid=12348, provider_transaction_id="12348", status=ServiceTransaction.Status.PENDING_PROVIDER, webhook_secret_encrypted=encrypt_secret("correct"), reserved_journal_id=44)
        response = self.client.get("/api/v2/services/webhook/sanaacash/", {"action": "done", "backpass": "wrong", "transid": "12348"})
        self.assertEqual(response.status_code, 403)
        tx.refresh_from_db()
        self.assertNotEqual(tx.status, ServiceTransaction.Status.SUCCESS)
