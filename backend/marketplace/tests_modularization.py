from django.apps import apps
from django.contrib.admin import site
from django.forms import BaseForm
from django.test import SimpleTestCase
from django.urls import resolve


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

    def test_domain_forms_are_real_model_or_action_forms(self):
        from communication.forms import MessageForm, NotificationForm
        from finance.forms import CurrencyRateForm, VendorCityShippingForm, WalletTopUpForm
        from orders.forms import OrderStatusForm, ShipmentForm
        from promotions.forms import CouponForm, GiftTransferForm, LoanReviewForm
        from storefront.forms import DesignThemeForm, StorefrontMediaForm, StorefrontSectionForm

        for form_class in (
            DesignThemeForm, StorefrontSectionForm, StorefrontMediaForm,
            OrderStatusForm, ShipmentForm,
            CurrencyRateForm, VendorCityShippingForm, WalletTopUpForm,
            NotificationForm, MessageForm,
            CouponForm, LoanReviewForm, GiftTransferForm,
        ):
            self.assertTrue(issubclass(form_class, BaseForm))

    def test_domain_admin_routes_resolve(self):
        routes = {
            "/admin/dashboard/storefront/": "admin-dashboard-storefront",
            "/admin/dashboard/storefront/themes/new/": "admin-storefront-theme-new",
            "/admin/dashboard/orders/": "admin-dashboard-orders",
            "/admin/dashboard/orders/shipments/1/edit/": "admin-order-shipment-edit",
            "/admin/dashboard/finance/": "admin-dashboard-finance",
            "/admin/dashboard/finance/currency-rates/new/": "admin-finance-currency-rate-new",
            "/admin/dashboard/communication/": "admin-dashboard-communication",
            "/admin/dashboard/communication/notifications/new/": "admin-communication-notification-new",
            "/admin/dashboard/promotions/": "admin-dashboard-promotions",
            "/admin/dashboard/promotions/coupons/new/": "admin-promotions-coupon-new",
        }
        for path, expected_name in routes.items():
            self.assertEqual(resolve(path).url_name, expected_name)

    def test_sensitive_domain_resources_are_read_only(self):
        from orders.api import PaymentViewSet, ReservationViewSet, ShipmentViewSet, VendorOrderViewSet
        from finance.api import VendorPayoutViewSet, WalletTransactionViewSet
        from promotions.api import CouponRedemptionViewSet, ReferralViewSet, GiftTransferViewSet

        for viewset in (
            PaymentViewSet, ReservationViewSet, ShipmentViewSet, VendorOrderViewSet,
            VendorPayoutViewSet, WalletTransactionViewSet,
            CouponRedemptionViewSet, ReferralViewSet,
        ):
            self.assertEqual(set(viewset.http_method_names), {"get", "head", "options"}, viewset.__name__)
        self.assertNotIn("patch", GiftTransferViewSet.http_method_names)
        self.assertNotIn("delete", GiftTransferViewSet.http_method_names)

    def test_v2_api_root(self):
        response = self.client.get("/api/v2/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["version"], "2")
        self.assertIn("storefront", response.json()["domains"])
        self.assertIn("orders", response.json()["domains"])
        self.assertIn("finance", response.json()["domains"])
        self.assertIn("communication", response.json()["domains"])
        self.assertIn("promotions", response.json()["domains"])

    def test_public_domain_info_contracts(self):
        public_urls = {
            "/api/v2/storefront/": "storefront",
            "/api/v2/orders/": "orders",
            "/api/v2/finance/": "finance",
            "/api/v2/communication/": "communication",
            "/api/v2/promotions/": "promotions",
        }
        for url, domain in public_urls.items():
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200, url)
            self.assertEqual(response.json()["domain"], domain, url)

    def test_protected_domain_resources_require_authentication(self):
        for url in (
            "/api/v2/orders/orders/",
            "/api/v2/finance/wallets/",
            "/api/v2/communication/notifications/",
            "/api/v2/promotions/addresses/",
        ):
            response = self.client.get(url)
            self.assertIn(response.status_code, {401, 403}, url)
