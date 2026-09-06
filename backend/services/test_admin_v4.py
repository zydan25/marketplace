from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings

from .admin_v4 import FIELD_LIBRARY, choose_link
from .models import MainServiceCategory, Service, ServiceCategory
from .provider_setup import create_or_update_sanaacash_provider


@override_settings(SERVICES_CREDENTIALS_KEY="MDEyMzQ1Njc4OTAxMjM0NTY3ODkwMTIzNDU2Nzg5MDE=")
class ServiceAdminV4Tests(TestCase):
    def setUp(self):
        User = get_user_model()
        User.objects.create_user(username="admin-v4", password="pass", is_staff=True, role="admin")
        main = MainServiceCategory.objects.create(name="اختبار الخدمات", slug="test-main")
        category = ServiceCategory.objects.create(main_category=main, name="اتصالات", slug="telecom")
        self.service = Service.objects.create(category=category, name="فئات يمن موبايل", slug="yem-denom-test", code="yem-denomination", pricing_mode="item", price=Decimal("0"))
        self.provider = create_or_update_sanaacash_provider(code="test-admin-provider", name="مزود الإدارة الاختباري", base_url="https://example.invalid/api/yr/", userid="1", username="login", password="secret")

    def test_service_field_library_contains_api_keys(self):
        keys = {key for key, _, _ in FIELD_LIBRARY}
        for key in {"mobile", "num", "type", "offerid", "offerkey", "method", "solfa", "customer_id", "placeid", "playerid", "playername", "zoneid", "uniqcode"}:
            self.assertIn(key, keys)

    def test_distribution_resolves_canonical_link_not_first_bill_link(self):
        link = choose_link(self.service, self.provider)
        self.assertIsNotNone(link)
        self.assertTrue(link.code.endswith("-yem_denomination"))

    def test_admin_service_page_renders(self):
        self.assertTrue(self.client.login(username="admin-v4", password="pass"))
        response = self.client.get("/api/admin/dashboard/services/services/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "تحديد الحقول")

    def test_provider_setup_is_idempotent(self):
        first = create_or_update_sanaacash_provider(code="idempotent-provider", name="ربطية", userid="2", username="u", password="p", base_url="https://example.invalid/api/yr/")
        second = create_or_update_sanaacash_provider(code="idempotent-provider", name="ربطية معدلة", userid="3", username="u2", password="", base_url="https://example.invalid/api/yr/")
        self.assertEqual(first.pk, second.pk)
        self.assertEqual(second.name, "ربطية معدلة")
        self.assertEqual(second.get_password(), "p")
