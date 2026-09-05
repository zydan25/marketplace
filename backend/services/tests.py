from decimal import Decimal
from unittest.mock import patch

from cryptography.fernet import Fernet
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from accounting.services_v2 import ensure_wallet
from .models import MainServiceCategory, ProviderConnection, ProviderLink, Service, ServiceCategory, ServiceTask, ServiceTransaction
from .provider import ProviderClient


@override_settings(SERVICES_CREDENTIALS_KEY=Fernet.generate_key().decode())
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
        self.link = ProviderLink.objects.create(provider=provider, name="شحن", code="test-link", path_template="yem", operation="bill", field_map={"amount": "amount"})
        self.service.distributions.create(provider_link=self.link, priority=1)
        self.client = APIClient()
        self.client.force_authenticate(self.customer)

    def test_catalog_and_request_reserves_only(self):
        response = self.client.get("/api/v2/services/catalog/")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["categories"])
        with patch("services.api.reserve_service_funds") as reserve:
            response = self.client.post("/api/v2/services/requests/", {"service_id": self.service.pk, "payload": {"mobile": "777777777"}}, format="json")
        self.assertEqual(response.status_code, 202)
        self.assertTrue(reserve.called)
        self.assertTrue(ServiceTask.objects.filter(transaction_id=response.data["id"]).exists())

    def test_token_matches_contract(self):
        token = ProviderClient.sanaacash_token("secret", "123", "login", "777777777")
        import hashlib
        h = hashlib.md5(b"secret").hexdigest()
        expected = hashlib.md5((h + "123" + "login" + "777777777").encode()).hexdigest()
        self.assertEqual(token, expected)

    def test_insufficient_balance_rejects_request(self):
        response = self.client.post("/api/v2/services/requests/", {"service_id": self.service.pk, "payload": {"mobile": "777777777"}}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertFalse(ServiceTransaction.objects.exists())
