from django.contrib.admin import site
from django.apps import apps
from django.test import SimpleTestCase


class DomainArchitectureTests(SimpleTestCase):
    expected_apps = {
        "accounts", "catalog", "vendors", "storefront", "orders", "finance", "communication", "promotions"
    }

    def test_domain_apps_are_installed(self):
        installed = {config.label for config in apps.get_app_configs()}
        self.assertTrue(self.expected_apps.issubset(installed))

    def test_domain_models_are_proxy_compatibility_models(self):
        expected = {
            "storefront": ["DesignTheme", "StorefrontSection", "StorefrontMedia"],
            "orders": ["Order", "OrderItem", "VendorOrder", "VendorOrderItem", "OrderStatusHistory", "Shipment", "InventoryReservation", "Payment"],
            "finance": ["Wallet", "WalletTransaction", "Payment", "VendorPayout", "VendorLedgerEntry", "CurrencyRate", "VendorCityShipping"],
            "communication": ["Notification", "Conversation", "Message"],
            "promotions": ["Coupon", "CouponRedemption", "Referral", "Address", "Loan", "GiftTransfer"],
        }
        for app_label, model_names in expected.items():
            for model_name in model_names:
                model = apps.get_model(app_label, model_name)
                self.assertTrue(model._meta.proxy, f"{app_label}.{model_name} must remain a proxy during the safe refactor")

    def test_new_admin_registrations_exist(self):
        expected = [
            ("storefront", "DesignTheme"), ("storefront", "StorefrontSection"), ("storefront", "StorefrontMedia"),
            ("orders", "Order"), ("orders", "VendorOrder"), ("orders", "Shipment"), ("orders", "Payment"),
            ("finance", "Wallet"), ("finance", "VendorPayout"), ("finance", "CurrencyRate"),
            ("communication", "Notification"), ("communication", "Conversation"), ("communication", "Message"),
            ("promotions", "Coupon"), ("promotions", "Loan"), ("promotions", "GiftTransfer"),
        ]
        for app_label, model_name in expected:
            self.assertIn(apps.get_model(app_label, model_name), site._registry)

    def test_v2_api_root(self):
        response = self.client.get("/api/v2/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["version"], "2")
        self.assertIn("storefront", response.json()["domains"])
        self.assertIn("orders", response.json()["domains"])
        self.assertIn("finance", response.json()["domains"])
        self.assertIn("communication", response.json()["domains"])
        self.assertIn("promotions", response.json()["domains"])

    def test_public_storefront_contract(self):
        response = self.client.get("/api/v2/storefront/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["domain"], "storefront")

    def test_protected_domains_require_authentication(self):
        for url in ("/api/v2/orders/", "/api/v2/finance/", "/api/v2/communication/", "/api/v2/promotions/"):
            response = self.client.get(url)
            self.assertIn(response.status_code, {401, 403}, url)
