import io
import json

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from PIL import Image

from marketplace.models import StorefrontSection, User, VendorProfile


class StorefrontEditorTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(phone="966500000001", username="966500000001", password="StrongPass123!", role="admin", is_staff=True)
        self.vendor = User.objects.create_user(phone="966500000002", username="966500000002", password="StrongPass123!", role="vendor")
        self.other_vendor_user = User.objects.create_user(phone="966500000003", username="966500000003", password="StrongPass123!", role="vendor")
        self.customer = User.objects.create_user(phone="966500000004", username="966500000004", password="StrongPass123!", role="customer")
        self.vendor_profile = VendorProfile.objects.create(owner=self.vendor, store_name="Vendor A", slug="vendor-a", status="active")
        self.other_profile = VendorProfile.objects.create(owner=self.other_vendor_user, store_name="Vendor B", slug="vendor-b", status="active")
        self.global_section = StorefrontSection.objects.create(owner=self.admin, title="الرئيسية", section_type="hero", vendor=None, config={"subtitle": "مرحبا"}, sort_order=0, is_visible=True)
        self.vendor_section = StorefrontSection.objects.create(owner=self.vendor, title="متجري", section_type="hero", vendor=self.vendor_profile, config={}, sort_order=0, is_visible=True)
        self.other_section = StorefrontSection.objects.create(owner=self.other_vendor_user, title="متجر آخر", section_type="hero", vendor=self.other_profile, config={}, sort_order=0, is_visible=True)

    def _png_upload(self, name="test.png"):
        buffer = io.BytesIO()
        Image.new("RGB", (2, 2), "white").save(buffer, format="PNG")
        return SimpleUploadedFile(name, buffer.getvalue(), content_type="image/png")

    def test_admin_can_update_global_section(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse("admin-storefront-section-update", args=[self.global_section.id]),
            data=json.dumps({"title": "رئيسية جديدة", "is_visible": False, "sort_order": 2, "config": {"image_url": "/media/hero.webp", "button_label": "تسوق الآن", "target_url": "/collection"}}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.global_section.refresh_from_db()
        self.assertEqual(self.global_section.title, "رئيسية جديدة")
        self.assertFalse(self.global_section.is_visible)
        self.assertEqual(self.global_section.config["target_url"], "/collection")

    def test_admin_can_create_global_section(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse("admin-storefront-section-create"),
            data=json.dumps({"title": "بنر جديد", "section_type": "banner"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        created = StorefrontSection.objects.get(title="بنر جديد")
        self.assertIsNone(created.vendor_id)
        self.assertEqual(created.section_type, "banner")

    def test_vendor_can_create_only_own_section(self):
        self.client.force_login(self.vendor)
        response = self.client.post(
            reverse("admin-storefront-section-create"),
            data=json.dumps({"title": "قسم متجري", "section_type": "product_grid"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        created = StorefrontSection.objects.get(title="قسم متجري")
        self.assertEqual(created.vendor_id, self.vendor_profile.id)

    def test_vendor_can_update_own_section_only(self):
        self.client.force_login(self.vendor)
        own = self.client.post(
            reverse("admin-storefront-section-update", args=[self.vendor_section.id]),
            data=json.dumps({"title": "واجهة متجري", "config": {"subtitle": "تخفيضات"}}),
            content_type="application/json",
        )
        other = self.client.post(
            reverse("admin-storefront-section-update", args=[self.other_section.id]),
            data=json.dumps({"title": "لا يجب التعديل"}),
            content_type="application/json",
        )
        self.assertEqual(own.status_code, 200)
        self.assertEqual(other.status_code, 403)

    def test_vendor_can_open_editor_but_sees_only_own_sections(self):
        self.client.force_login(self.vendor)
        response = self.client.get(reverse("admin-storefront-editor"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "متجري")
        self.assertNotContains(response, "متجر آخر")
        self.assertNotContains(response, "الرئيسية")

    def test_customer_cannot_open_editor(self):
        self.client.force_login(self.customer)
        response = self.client.get(reverse("admin-storefront-editor"))
        self.assertEqual(response.status_code, 403)

    def test_section_config_must_be_object(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse("admin-storefront-section-update", args=[self.global_section.id]),
            data=json.dumps({"config": ["invalid"]}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    def test_create_rejects_unknown_section_type(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse("admin-storefront-section-create"),
            data=json.dumps({"title": "قسم غير صالح", "section_type": "unknown"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    def test_publish_action_publishes_and_returns_config(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse("admin-storefront-section-update", args=[self.global_section.id]),
            data=json.dumps({"action": "publish"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.global_section.refresh_from_db()
        self.assertTrue(self.global_section.is_visible)
        self.assertTrue(self.global_section.config["published"])
        self.assertIn("config", response.json())

    def test_nested_slide_image_is_saved(self):
        self.client.force_login(self.admin)
        payload = {
            "action": "save",
            "title": "عرض",
            "section_type": "hero",
            "sort_order": 1,
            "is_visible": True,
            "config": {
                "slides": [{"id": "slide-1", "title": "صيف", "imageUrl": "", "visible": True, "isActive": True, "sortOrder": 0}]
            },
        }
        response = self.client.post(
            reverse("admin-storefront-section-update", args=[self.global_section.id]),
            data={"payload": json.dumps(payload), "asset:slides:0:image": self._png_upload()},
        )
        self.assertEqual(response.status_code, 200)
        self.global_section.refresh_from_db()
        self.assertTrue(self.global_section.config["slides"][0]["imageUrl"].startswith("/"))

    def test_unsupported_image_type_is_rejected_cleanly(self):
        self.client.force_login(self.admin)
        payload = {"action": "save", "title": "عرض", "section_type": "hero", "sort_order": 1, "is_visible": True, "config": {}}
        response = self.client.post(
            reverse("admin-storefront-section-update", args=[self.global_section.id]),
            data={"payload": json.dumps(payload), "image": SimpleUploadedFile("test.bmp", b"not-an-image", content_type="image/bmp")},
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("غير مدعوم", response.json().get("detail", ""))
