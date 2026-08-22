from rest_framework.test import APIRequestFactory
from rest_framework.exceptions import AuthenticationFailed
from django.test import SimpleTestCase

from marketplace.secure_catalog import SecureCategoryViewSet, SecureProductViewSet


class MarketplaceApiSecurityTests(SimpleTestCase):
    def setUp(self):
        self.factory = APIRequestFactory()

    def test_category_create_is_not_public(self):
        request = self.factory.post("/api/categories/", {"name": "غير مصرح"}, format="json")
        view = SecureCategoryViewSet.as_view({"post": "create"})
        response = view(request)
        self.assertEqual(response.status_code, 401)

    def test_product_create_is_not_public(self):
        request = self.factory.post("/api/products/", {"name": "غير مصرح"}, format="json")
        view = SecureProductViewSet.as_view({"post": "create"})
        response = view(request)
        self.assertEqual(response.status_code, 401)
