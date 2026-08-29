from django.test import TestCase
from django.urls import reverse
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from marketplace.models import User

from .models import VendorApplication, VendorProfile


class VendorProxyTests(TestCase):
    def test_proxies_use_existing_tables(self):
        from marketplace.models import VendorProfile as LegacyProfile
        from marketplace.marketplace_models import VendorApplication as LegacyApplication
        self.assertTrue(VendorProfile._meta.proxy)
        self.assertTrue(VendorApplication._meta.proxy)
        self.assertEqual(VendorProfile._meta.db_table, LegacyProfile._meta.db_table)
        self.assertEqual(VendorApplication._meta.db_table, LegacyApplication._meta.db_table)


class VendorApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.customer = User.objects.create_user(phone="733111111", username="733111111", password="Pass12345!", role="customer")
        self.vendor_user = User.objects.create_user(phone="733111112", username="733111112", password="Pass12345!", role="vendor")
        self.vendor = VendorProfile.objects.create(owner=self.vendor_user, store_name="متجر أول", slug="first", status="active")
        self.other_user = User.objects.create_user(phone="733111113", username="733111113", password="Pass12345!", role="vendor")
        self.other_vendor = VendorProfile.objects.create(owner=self.other_user, store_name="متجر ثان", slug="second", status="active")
        self.admin = User.objects.create_user(phone="733111114", username="733111114", password="Pass12345!", role="admin", is_staff=True)

    def auth(self, user):
        token, _ = Token.objects.get_or_create(user=user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

    def test_public_list_only_returns_active_vendors(self):
        VendorProfile.objects.create(owner=User.objects.create_user(phone="733111115", username="733111115", password="Pass12345!", role="vendor"), store_name="موقوف", slug="disabled", status="suspended")
        response = self.client.get("/api/vendors/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 2)

    def test_vendor_can_edit_only_own_store(self):
        self.auth(self.vendor_user)
        response = self.client.patch("/api/vendors/first/", {"description": "وصف جديد"}, format="json")
        self.assertEqual(response.status_code, 200)
        self.vendor.refresh_from_db()
        self.assertEqual(self.vendor.description, "وصف جديد")
        response = self.client.patch("/api/vendors/second/", {"description": "غير مسموح"}, format="json")
        self.assertEqual(response.status_code, 404)

    def test_customer_cannot_create_vendor(self):
        self.auth(self.customer)
        response = self.client.post("/api/vendors/", {"store_name": "متجر", "description": "", "phone": "733123123", "address": ""}, format="json")
        self.assertEqual(response.status_code, 403)

    def test_vendor_application_lifecycle(self):
        self.auth(self.customer)
        create = self.client.post("/api/vendor-applications/", {"store_name": "متجر جديد", "description": "وصف", "phone": "733222222", "address": "صنعاء"}, format="json")
        self.assertEqual(create.status_code, 201)
        app_id = create.data["id"]
        self.auth(self.admin)
        approve = self.client.post(f"/api/vendor-applications/{app_id}/approve/")
        self.assertEqual(approve.status_code, 200)
        app = VendorApplication.objects.get(pk=app_id)
        self.assertEqual(app.status, VendorApplication.Status.APPROVED)
        customer = User.objects.get(phone="733111111")
        self.assertEqual(customer.role, "vendor")
        self.assertTrue(VendorProfile.objects.filter(owner=customer, store_name="متجر جديد").exists())

    def test_vendor_application_rejection_keeps_account_customer(self):
        self.auth(self.customer)
        create = self.client.post("/api/vendor-applications/", {"store_name": "طلب مرفوض", "description": "", "phone": "733333333", "address": ""}, format="json")
        self.assertEqual(create.status_code, 201)
        self.auth(self.admin)
        reject = self.client.post(f"/api/vendor-applications/{create.data['id']}/reject/", {"review_note": "البيانات غير مكتملة"}, format="json")
        self.assertEqual(reject.status_code, 200)
        app = VendorApplication.objects.get(pk=create.data["id"])
        self.assertEqual(app.status, VendorApplication.Status.REJECTED)
        self.assertEqual(User.objects.get(phone="733111111").role, "customer")


class VendorDashboardTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(phone="744111111", username="744111111", password="Admin12345!", role="admin", is_staff=True)
        self.customer = User.objects.create_user(phone="744111112", username="744111112", password="Customer12345!", role="customer")
        self.vendor = VendorProfile.objects.create(owner=User.objects.create_user(phone="744111113", username="744111113", password="Vendor12345!", role="vendor"), store_name="متجر الإدارة", slug="admin-store", status="active")
        self.client.force_login(self.admin)

    def test_dashboard_pages_render(self):
        self.assertEqual(self.client.get(reverse("vendors-dashboard:home")).status_code, 200)
        self.assertContains(self.client.get(reverse("vendors-dashboard:home")), "مركز التجار")
        self.assertEqual(self.client.get(reverse("vendors-dashboard:vendors")).status_code, 200)
        self.assertEqual(self.client.get(reverse("vendors-dashboard:applications")).status_code, 200)
        self.assertEqual(self.client.get(reverse("vendors-dashboard:vendor-detail", kwargs={"vendor_id": self.vendor.pk})).status_code, 200)

    def test_vendor_status_and_update(self):
        response = self.client.post(reverse("vendors-dashboard:vendor-status", kwargs={"vendor_id": self.vendor.pk, "status": "suspended"}))
        self.assertEqual(response.status_code, 302)
        self.vendor.refresh_from_db()
        self.assertEqual(self.vendor.status, "suspended")
        response = self.client.get(reverse("vendors-dashboard:vendor-update", kwargs={"vendor_id": self.vendor.pk}))
        self.assertEqual(response.status_code, 200)

    def test_application_approval_from_dashboard(self):
        app = VendorApplication.objects.create(applicant=self.customer, store_name="تاجر اللوحة", description="", phone="744222222", address="صنعاء")
        response = self.client.post(reverse("vendors-dashboard:application-action", kwargs={"application_id": app.pk, "action": "approve"}))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(VendorApplication.objects.get(pk=app.pk).status, VendorApplication.Status.APPROVED)
        self.customer.refresh_from_db()
        self.assertEqual(self.customer.role, "vendor")

    def test_non_admin_is_denied(self):
        self.client.force_login(self.customer)
        response = self.client.get(reverse("vendors-dashboard:home"))
        self.assertEqual(response.status_code, 403)

    def test_csv_export(self):
        response = self.client.get(reverse("vendors-dashboard:export"))
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/csv", response["Content-Type"])
        self.assertIn("متجر الإدارة", response.content.decode("utf-8-sig"))
