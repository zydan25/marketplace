from decimal import Decimal

from django.test import TestCase
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from .models import Category, DesignTheme, Order, Product, User, VendorProfile


class MarketplaceApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.customer = User.objects.create_user(phone="700000001", username="700000001", password="secret123", role="customer")
        self.vendor_user = User.objects.create_user(phone="700000002", username="700000002", password="secret123", role="vendor")
        self.vendor = VendorProfile.objects.create(owner=self.vendor_user, store_name="متجر الاختبار", slug="test-store", status="active")
        self.category = Category.objects.create(name="فساتين", slug="dresses")
        self.product = Product.objects.create(vendor=self.vendor, sku="SKU-1", name="فستان اختبار", slug="test-dress", price=Decimal("100.00"), stock=4, is_published=True)
        self.product.categories.add(self.category)

    def authenticate(self, user):
        token, _ = Token.objects.get_or_create(user=user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

    def test_customer_registration_returns_token_and_wallet(self):
        response = self.client.post("/api/auth/register/", {"phone": "700000003", "password": "secret123", "first_name": "عميل"}, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertTrue(response.data["token"])
        self.assertTrue(User.objects.get(phone="700000003").wallet)

    def test_public_catalog_and_search(self):
        response = self.client.get("/api/products/?q=اختبار")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["sku"], "SKU-1")

    def test_customer_can_create_order_and_stock_decreases(self):
        self.authenticate(self.customer)
        response = self.client.post("/api/orders/", {"items": [{"product_id": self.product.id, "quantity": 2, "size": "M"}], "shipping_address": {"city": "إب"}}, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Order.objects.count(), 1)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 2)
        self.assertEqual(response.data["total"], "200.00")

    def test_vendor_can_create_product_but_customer_cannot(self):
        self.authenticate(self.customer)
        denied = self.client.post("/api/products/", {"name": "محاولة", "sku": "NO", "slug": "no", "price": "10", "stock": 1}, format="json")
        self.assertEqual(denied.status_code, 403)
        self.authenticate(self.vendor_user)
        allowed = self.client.post("/api/products/", {"name": "منتج جديد", "sku": "SKU-2", "slug": "new-product", "price": "20", "stock": 3}, format="json")
        self.assertEqual(allowed.status_code, 201)
        self.assertEqual(allowed.data["vendor"]["slug"], "test-store")

    def test_vendor_can_create_own_theme(self):
        self.authenticate(self.vendor_user)
        response = self.client.post("/api/themes/", {"name": "هوية التاجر", "tokens": {"primary": "#123456"}, "layout": {"showHero": True}}, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertFalse(response.data["is_global"])
        self.assertEqual(DesignTheme.objects.get(vendor=self.vendor).tokens["primary"], "#123456")
