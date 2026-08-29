from django.test import TestCase
from django.urls import reverse
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from marketplace.models import User, VendorProfile

from .models import Category, CatalogOption, PriceGroup, Product, ProductImage, ProductVariant


class CatalogProxyTests(TestCase):
    def test_proxies_use_existing_tables(self):
        self.assertTrue(Category._meta.proxy)
        self.assertTrue(Product._meta.proxy)
        self.assertTrue(ProductImage._meta.proxy)
        self.assertTrue(ProductVariant._meta.proxy)
        self.assertTrue(CatalogOption._meta.proxy)
        self.assertTrue(PriceGroup._meta.proxy)
        from marketplace.models import Category as LegacyCategory, Product as LegacyProduct
        self.assertEqual(Category._meta.db_table, LegacyCategory._meta.db_table)
        self.assertEqual(Product._meta.db_table, LegacyProduct._meta.db_table)
        self.assertEqual(ProductVariant._meta.db_table, ProductVariant._meta.concrete_model._meta.db_table)


class CatalogApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.customer = User.objects.create_user(phone="733000001", username="733000001", password="Pass12345!", role="customer")
        self.vendor_user = User.objects.create_user(phone="733000002", username="733000002", password="Pass12345!", role="vendor")
        self.vendor = VendorProfile.objects.create(owner=self.vendor_user, store_name="متجر اختبار", status="active")
        self.admin = User.objects.create_user(phone="733000003", username="733000003", password="Pass12345!", role="admin", is_staff=True)
        self.category = Category.objects.create(name="إلكترونيات", slug="electronics", is_active=True)
        self.product = Product.objects.create(vendor=self.vendor, name="منتج اختبار", price="100", stock=10, is_published=True)
        self.product.categories.add(self.category)

    def test_catalog_tree_is_public(self):
        response = self.client.get("/api/catalog/tree/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("categories", response.data)
        self.assertIn("options", response.data)

    def test_product_list_keeps_public_contract(self):
        response = self.client.get("/api/products/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["name"], "منتج اختبار")

    def test_vendor_cannot_edit_other_vendor_product(self):
        other_user = User.objects.create_user(phone="733000004", username="733000004", password="Pass12345!", role="vendor")
        other_vendor = VendorProfile.objects.create(owner=other_user, store_name="متجر آخر", status="active")
        other_product = Product.objects.create(vendor=other_vendor, name="خاص", price="90", stock=2)
        token, _ = Token.objects.get_or_create(user=self.vendor_user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
        response = self.client.patch(f"/api/products/{other_product.pk}/", {"name": "تعديل غير مسموح"}, format="json")
        self.assertEqual(response.status_code, 404)

    def test_vendor_can_manage_own_variant_through_new_endpoint(self):
        token, _ = Token.objects.get_or_create(user=self.vendor_user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
        response = self.client.post("/api/variants/", {"product": self.product.pk, "color": "أسود", "size": "M", "stock": 4}, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertTrue(ProductVariant.objects.filter(product=self.product, color="أسود", size="M").exists())

    def test_admin_can_manage_price_groups_and_options(self):
        token, _ = Token.objects.get_or_create(user=self.admin)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
        pg = self.client.post("/api/price-groups/", {"name": "سعر الجملة", "code": "WHOLESALE", "adjustment_type": "percentage", "percentage": "10", "fixed_amount": "0", "is_active": True}, format="json")
        self.assertEqual(pg.status_code, 201)
        opt = self.client.post("/api/catalog-options/", {"group": "color", "name": "أسود", "category": self.category.pk, "sort_order": 1}, format="json")
        self.assertEqual(opt.status_code, 201)
        self.assertTrue(CatalogOption.objects.filter(group="color", name="أسود").exists())


class CatalogDashboardTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(phone="744000001", username="744000001", password="Admin12345!", role="admin", is_staff=True)
        self.vendor_user = User.objects.create_user(phone="744000002", username="744000002", password="Vendor12345!", role="vendor")
        self.vendor = VendorProfile.objects.create(owner=self.vendor_user, store_name="متجر اللوحة", status="active")
        self.client.force_login(self.admin)

    def test_overview_and_catalog_pages_are_html(self):
        response = self.client.get(reverse("catalog-dashboard:home"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "مركز الكتالوج")
        self.assertEqual(self.client.get(reverse("catalog-dashboard:products")).status_code, 200)
        self.assertEqual(self.client.get(reverse("catalog-dashboard:categories")).status_code, 200)
        self.assertEqual(self.client.get(reverse("catalog-dashboard:options")).status_code, 200)
        self.assertEqual(self.client.get(reverse("catalog-dashboard:price-groups")).status_code, 200)

    def test_create_product_and_variant_from_dashboard(self):
        category = Category.objects.create(name="أجهزة", slug="devices", is_active=True)
        response = self.client.post(reverse("catalog-dashboard:product-create"), {
            "vendor": self.vendor.pk, "categories": [category.pk], "sku": "", "name": "هاتف", "slug": "",
            "description": "وصف", "brand": "علامة", "material": "", "shipping_note": "", "return_policy": "",
            "price": "1000", "sale_price": "900", "currency": "YER", "stock": "8", "colors": "[]", "sizes": "[]",
            "hashtags": "[]", "details": "{}", "is_published": "on", "is_trending": "on",
        })
        self.assertEqual(response.status_code, 302)
        product = Product.objects.get(name="هاتف")
        self.assertTrue(product.slug)
        response = self.client.post(reverse("catalog-dashboard:variant-create", kwargs={"product_id": product.pk}), {"sku": "", "color": "أسود", "size": "L", "price_override": "950", "stock": "3", "is_active": "on"})
        self.assertEqual(response.status_code, 302)
        self.assertTrue(ProductVariant.objects.filter(product=product, color="أسود", size="L").exists())

    def test_category_toggle_is_safe(self):
        category = Category.objects.create(name="ملابس", slug="clothes", is_active=True)
        response = self.client.post(reverse("catalog-dashboard:category-toggle", kwargs={"category_id": category.pk}))
        self.assertEqual(response.status_code, 302)
        category.refresh_from_db()
        self.assertFalse(category.is_active)

    def test_non_admin_is_denied(self):
        self.client.force_login(self.vendor_user)
        response = self.client.get(reverse("catalog-dashboard:home"))
        self.assertEqual(response.status_code, 403)