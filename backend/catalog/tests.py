import base64

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
        variant = ProductVariant.objects.get(product=self.product, color="أسود", size="M")
        response = self.client.patch(f"/api/variants/{variant.pk}/", {"stock": 5}, format="json")
        self.assertEqual(response.status_code, 200)
        variant.refresh_from_db()
        self.assertEqual(variant.stock, 5)

    def test_admin_can_manage_price_groups_and_options(self):
        token, _ = Token.objects.get_or_create(user=self.admin)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
        pg = self.client.post("/api/price-groups/", {"name": "سعر الجملة", "code": "WHOLESALE", "adjustment_type": "percentage", "percentage": "10", "fixed_amount": "0", "is_active": True}, format="json")
        self.assertEqual(pg.status_code, 201)
        opt = self.client.post("/api/catalog-options/", {"group": "color", "name": "أسود", "category": self.category.pk, "sort_order": 1}, format="json")
        self.assertEqual(opt.status_code, 201)
        self.assertTrue(CatalogOption.objects.filter(group="color", name="أسود").exists())

    def test_public_cannot_write_catalog(self):
        response = self.client.post("/api/categories/", {"name": "غير مسموح", "slug": "not-allowed"}, format="json")
        self.assertEqual(response.status_code, 401)


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
        self.assertTrue(product.sku.startswith("SKU-"))
        response = self.client.post(reverse("catalog-dashboard:variant-create", kwargs={"product_id": product.pk}), {"sku": "", "color": "أسود", "size": "L", "price_override": "950", "stock": "3", "is_active": "on"})
        self.assertEqual(response.status_code, 302)
        self.assertTrue(ProductVariant.objects.filter(product=product, color="أسود", size="L").exists())

    def test_edit_variant_option_and_price_group(self):
        category = Category.objects.create(name="أجهزة", slug="devices-edit", is_active=True)
        product = Product.objects.create(vendor=self.vendor, name="حاسوب", price="2000", stock=9)
        product.categories.add(category)
        variant = ProductVariant.objects.create(product=product, sku="EDIT-V1", color="أسود", size="M", stock=2)
        response = self.client.get(reverse("catalog-dashboard:variant-edit", kwargs={"variant_id": variant.pk}))
        self.assertEqual(response.status_code, 200)
        response = self.client.post(reverse("catalog-dashboard:variant-edit", kwargs={"variant_id": variant.pk}), {"sku": "EDIT-V2", "color": "أبيض", "size": "L", "price_override": "1900", "stock": "4", "is_active": "on"})
        self.assertEqual(response.status_code, 302)
        variant.refresh_from_db()
        self.assertEqual(variant.sku, "EDIT-V2")
        option = CatalogOption.objects.create(group="color", name="أحمر", slug="red", category=category, sort_order=2)
        response = self.client.post(reverse("catalog-dashboard:option-update", kwargs={"option_id": option.pk}), {"group": "color", "name": "أحمر فاتح", "slug": "red-light", "category": category.pk, "sort_order": 3, "is_active": "on"})
        self.assertEqual(response.status_code, 302)
        option.refresh_from_db()
        self.assertEqual(option.name, "أحمر فاتح")
        group = PriceGroup.objects.create(name="تجزئة", code="RETAIL", adjustment_type="percentage", percentage=0, fixed_amount=0, is_active=True)
        response = self.client.post(reverse("catalog-dashboard:price-group-update", kwargs={"group_id": group.pk}), {"name": "جملة", "code": "WHOLESALE2", "adjustment_type": "fixed", "percentage": 0, "fixed_amount": 25, "is_active": "on"})
        self.assertEqual(response.status_code, 302)
        group.refresh_from_db()
        self.assertEqual(group.code, "WHOLESALE2")

    def test_product_bulk_action_and_export(self):
        one = Product.objects.create(vendor=self.vendor, name="واحد", price="10", stock=1, is_published=False)
        two = Product.objects.create(vendor=self.vendor, name="اثنان", price="20", stock=1, is_published=False)
        response = self.client.post(reverse("catalog-dashboard:products-bulk"), {"bulk_action": "publish", "selected_products": [one.pk, two.pk]})
        self.assertEqual(response.status_code, 302)
        one.refresh_from_db(); two.refresh_from_db()
        self.assertTrue(one.is_published); self.assertTrue(two.is_published)
        response = self.client.get(reverse("catalog-dashboard:products-export"))
        self.assertEqual(response.status_code, 200)
        self.assertIn("واحد", response.content.decode("utf-8-sig"))

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

    def test_legacy_catalog_link_redirects_to_new_center(self):
        response = self.client.get("/admin/marketplace/product/")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], reverse("catalog-dashboard:products"))

    def test_image_management_and_primary_selection(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        product = Product.objects.create(vendor=self.vendor, name="صور", price="50", stock=4)
        png = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=")
        image = SimpleUploadedFile("one.png", png, content_type="image/png")
        response = self.client.post(reverse("catalog-dashboard:image-create", kwargs={"product_id": product.pk}), {"image": image, "alt_text": "صورة", "sort_order": 0, "is_primary": "on"})
        self.assertEqual(response.status_code, 302)
        self.assertTrue(ProductImage.objects.filter(product=product, is_primary=True).exists())
