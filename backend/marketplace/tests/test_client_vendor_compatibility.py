from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from marketplace.models import StorefrontSection, VendorPayout, VendorProfile, Wallet


User = get_user_model()


class ClientVendorCompatibilityTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(phone="967700000001", password="pass1234", role="vendor")
        self.vendor = VendorProfile.objects.create(owner=self.user, store_name="متجري", status="active")
        self.client.force_authenticate(self.user)

    def test_vendor_can_manage_hidden_storefront_section(self):
        section = StorefrontSection.objects.create(owner=self.user, vendor=self.vendor, title="بانر", section_type="banner", config={"slides": []}, is_visible=False)
        response = self.client.patch(f"/api/storefront-sections/{section.id}/", {"is_visible": True}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(StorefrontSection.objects.get(pk=section.pk).is_visible)

        response = self.client.delete(f"/api/storefront-sections/{section.id}/")
        self.assertEqual(response.status_code, 204)
        self.assertFalse(StorefrontSection.objects.filter(pk=section.pk).exists())

    def test_vendor_finance_summary_uses_wallet_balance_for_available_amount(self):
        wallet = Wallet.objects.create(user=self.user, balance=Decimal("1250.00"), currency="YER")
        response = self.client.get("/api/vendor-finance/summary/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["wallet_balance"], "1250.00")
        self.assertEqual(response.data["available"], "1250.00")

    def test_pending_withdrawal_is_subtracted_from_available_wallet_balance(self):
        Wallet.objects.create(user=self.user, balance=Decimal("1250.00"), currency="YER")
        self.client.post("/api/vendor-finance/request_payout/", {"amount": "250.00"}, format="json")
        response = self.client.get("/api/vendor-finance/summary/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["wallet_balance"], "1250.00")
        self.assertEqual(response.data["available"], "1000.00")
        self.assertEqual(VendorPayout.objects.filter(vendor=self.vendor, status="pending").count(), 1)
