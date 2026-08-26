from decimal import Decimal
import json

from django.test import TestCase
from django.urls import reverse
from rest_framework.authtoken.models import Token

from marketplace.models import DesignTheme, Product, ProductImage, StorefrontSection, User, VendorProfile
from marketplace.models_extended import ProductVariant


class VendorPermissionTests(TestCase):
    def setUp(self):
        self.vendor_user = User.objects.create_user(
            username="vendor-a",
            phone="967700000001",
            password="StrongPass123!",
            role="vendor",
        )
        self.other_user = User.objects.create_user(
            username="vendor-b",
            phone="967700000002",
            password="StrongPass123!",
            role="vendor",
        )
        self.vendor = VendorProfile.objects.create(
            owner=self.vendor_user,
            store_name="متجر أ",
            slug="store-a",
            status="active",
        )
        self.other_vendor = VendorProfile.objects.create(
            owner=self.other_user,
            store_name="متجر ب",
            slug="store-b",
            status="active",
        )
        self.token = Token.objects.create(user=self.vendor_user)

        self.product = Product.objects.create(
            vendor=self.vendor,
            sku="A-001",
            name="منتج أ",
            price=Decimal("100"),
            stock=10,
            is_published=True,
        )
        Product.objects.create(
            vendor=self.other_vendor,
            sku="B-001",
            name="منتج ب",
            price=Decimal("120"),
            stock=8,
            is_published=True,
        )
        self.variant = ProductVariant.objects.create(
            product=self.product,
            sku="A-001-BLUE-M",
            color="أزرق",
            size="M",
            stock=5,
        )
        self.hidden_section = StorefrontSection.objects.create(
            owner=self.vendor_user,
            vendor=self.vendor,
            title="مسودة التاجر",
            section_type="hero",
            config={"published": False},
            sort_order=1,
            is_visible=False,
        )
        self.other_section = StorefrontSection.objects.create(
            owner=self.other_user,
            vendor=self.other_vendor,
            title="قسم متجر آخر",
            section_type="hero",
            config={"published": False},
            sort_order=1,
            is_visible=False,
        )
        self.theme = DesignTheme.objects.create(
            owner=self.vendor_user,
            vendor=self.vendor,
            name="هوية أ",
            is_global=False,
            is_active=True,
        )

    def authenticate(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token.key}")

    def test_vendor_can_list_own_products_including_drafts(self):
        self.product.is_published = False
        self.product.save(update_fields=["is_published", "updated_at"])
        self.authenticate()
        response = self.client.get("/api/products/")
        self.assertEqual(response.status_code, 200)
        results = response.json().get("results", response.json())
        ids = {int(item["id"]) for item in results}
        self.assertIn(self.product.id, ids)

    def test_vendor_can_create_product_for_own_store(self):
        self.authenticate()
        response = self.client.post(
            "/api/products/",
            data=json.dumps({
                "name": "منتج جديد",
                "sku": "A-NEW-001",
                "price": "150",
                "stock": 20,
                "currency": "YER",
                "is_published": True,
                "is_trending": False,
                "categories": [],
                "colors": [],
                "sizes": [],
                "hashtags": [],
                "details": {},
                "variants": [],
            }),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201)
        created = Product.objects.get(sku="A-NEW-001")
        self.assertEqual(created.vendor_id, self.vendor.id)

    def test_vendor_cannot_create_product_for_other_store(self):
        self.authenticate()
        response = self.client.post(
            "/api/products/",
            data=json.dumps({
                "vendor_id": self.other_vendor.id,
                "name": "محاولة",
                "sku": "A-BAD-001",
                "price": "50",
                "stock": 1,
                "currency": "YER",
                "is_published": True,
                "variants": [],
            }),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 403)

    def test_vendor_can_update_own_product_with_existing_variant_identified_by_sku(self):
        self.authenticate()
        response = self.client.patch(
            f"/api/products/{self.product.id}/",
            data=json.dumps({
                "name": "منتج أ معدل",
                "variants": [{
                    "sku": self.variant.sku,
                    "color": "أزرق",
                    "size": "L",
                    "stock": 6,
                    "price_override": "110",
                }],
            }),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.variant.refresh_from_db()
        self.assertEqual(self.variant.size, "L")
        self.assertEqual(self.variant.stock, 6)

    def test_vendor_cannot_update_other_store_product(self):
        other = Product.objects.get(sku="B-001")
        self.authenticate()
        response = self.client.patch(
            f"/api/products/{other.id}/",
            data=json.dumps({"name": "لا يجب"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 403)

    def test_vendor_can_update_hidden_own_storefront_section(self):
        self.authenticate()
        response = self.client.patch(
            f"/api/storefront-sections/{self.hidden_section.id}/",
            data=json.dumps({"title": "مسودة معدلة"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.hidden_section.refresh_from_db()
        self.assertEqual(self.hidden_section.title, "مسودة معدلة")

    def test_vendor_cannot_update_other_storefront_section(self):
        self.authenticate()
        response = self.client.patch(
            f"/api/storefront-sections/{self.other_section.id}/",
            data=json.dumps({"title": "محاولة"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 404)

    def test_vendor_can_update_own_theme(self):
        self.authenticate()
        response = self.client.patch(
            f"/api/themes/{self.theme.id}/",
            data=json.dumps({"name": "هوية أ معدلة", "is_active": True, "tokens": {"primary": "#111111"}, "layout": {"direction": "rtl"}}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.theme.refresh_from_db()
        self.assertEqual(self.theme.name, "هوية أ معدلة")
