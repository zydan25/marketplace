import json

from django.test import TestCase
from django.urls import reverse

from marketplace.models import StorefrontSection, User, VendorProfile


class StorefrontEditorTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(phone="966500000001", username="966500000001", password="StrongPass123!", role="admin", is_staff=True)
        self.vendor = User.objects.create_user(phone="966500000002", username="966500000002", password="StrongPass123!", role="vendor")
        self.other_vendor_user = User.objects.create_user(phone="966500000003", username="966500000003", password="StrongPass123!", role="vendor")
        self.vendor_profile = VendorProfile.objects.create(owner=self.vendor, store_name="Vendor A", slug="vendor-a", status="active")
        self.other_profile = VendorProfile.objects.create(owner=self.other_vendor_user, store_name="Vendor B", slug="vendor-b", status="active")
        self.global_section = StorefrontSection.objects.create(owner=self.admin, title="الرئيسية", section_type="hero", vendor=None, config={"subtitle": "مرحبا"}, sort_order=0, is_visible=True)
        self.vendor_section = StorefrontSection.objects.create(owner=self.vendor, title="متجري", section_type="hero", vendor=self.vendor_profile, config={}, sort_order=0, is_visible=True)
        self.other_section = StorefrontSection.objects.create(owner=self.other_vendor_user, title="متجر آخر", section_type="hero", vendor=self.other_profile, config={}, sort_order=0, is_visible=True)

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

    def test_editor_requires_staff(self):
        self.client.force_login(self.vendor)
        response = self.client.get(reverse("admin-storefront-editor"))
        self.assertEqual(response.status_code, 302)

    def test_section_config_must_be_object(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse("admin-storefront-section-update", args=[self.global_section.id]),
            data=json.dumps({"config": ["invalid"]}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
