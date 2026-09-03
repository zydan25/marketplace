from django.test import TestCase
from django.urls import reverse
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from marketplace.models import User, Wallet
from .models import User as AccountsUser, UserPreference as AccountsUserPreference


class AccountsStageOneTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_user_compatibility_proxy_points_to_existing_user_table(self):
        user = User.objects.create_user(phone="711000001", username="711000001", password="SafePass123!", role="customer")
        proxy = AccountsUser.objects.get(pk=user.pk)
        self.assertEqual(proxy.pk, user.pk)
        self.assertEqual(proxy._meta.db_table, user._meta.db_table)
        self.assertTrue(AccountsUser._meta.proxy)

    def test_preference_has_concrete_accounts_ownership_and_existing_table(self):
        user = User.objects.create_user(phone="711000010", username="711000010", password="SafePass123!", role="customer")
        preference = AccountsUserPreference.objects.create(user=user)
        self.assertEqual(preference.pk, AccountsUserPreference.objects.get(pk=preference.pk).pk)
        self.assertEqual(AccountsUserPreference._meta.db_table, "marketplace_userpreference")
        self.assertFalse(AccountsUserPreference._meta.proxy)

    def test_registration_uses_accounts_route_and_creates_wallet(self):
        response = self.client.post("/api/auth/register/", {"phone": "711000002", "password": "SafePass456!", "first_name": "عميل"}, format="json")
        self.assertEqual(response.status_code, 201)
        user = User.objects.get(phone="711000002")
        self.assertTrue(Token.objects.filter(user=user).exists())
        self.assertTrue(Wallet.objects.filter(user=user).exists())

    def test_me_keeps_existing_auth_contract(self):
        user = User.objects.create_user(phone="711000003", username="711000003", password="SafePass789!", role="customer")
        token, _ = Token.objects.get_or_create(user=user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
        response = self.client.get("/api/auth/me/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["phone"], "711000003")

    def test_preferences_api_keeps_existing_path(self):
        user = User.objects.create_user(phone="711000004", username="711000004", password="SafePass789!", role="customer")
        token, _ = Token.objects.get_or_create(user=user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
        response = self.client.patch("/api/preferences/", {"currency": "SAR", "notifications_enabled": False}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["currency"], "SAR")
        self.assertFalse(AccountsUserPreference.objects.get(user=user).notifications_enabled)


class AccountsDashboardTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(phone="700000001", username="700000001", password="AdminPass123!", role="admin", is_staff=True, is_active=True)
        self.user = User.objects.create_user(phone="700000002", username="700000002", password="CustomerPass123!", role="customer", first_name="أحمد", is_active=True)
        self.other = User.objects.create_user(phone="700000004", username="700000004", password="CustomerPass456!", role="customer", first_name="محمد", is_active=True)
        self.client.force_login(self.admin)

    def test_dashboard_home_and_users_are_html_pages(self):
        response = self.client.get(reverse("accounts-dashboard:home"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "إدارة الحسابات")
        response = self.client.get(reverse("accounts-dashboard:users"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "أحمد")

    def test_user_edit_and_action_keep_account_lifecycle_safe(self):
        response = self.client.post(
            reverse("accounts-dashboard:user-save", kwargs={"user_id": self.user.pk}),
            {"username": self.user.username, "phone": self.user.phone, "first_name": "أحمد محمد", "middle_name": "", "third_name": "", "last_name": "", "email": "ahmed@example.com", "governorate": "صنعاء", "role": "customer", "points_balance": 12, "is_active": "on", "is_phone_verified": "on"},
        )
        self.assertEqual(response.status_code, 302)
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, "أحمد محمد")
        self.assertTrue(self.user.is_phone_verified)
        response = self.client.post(reverse("accounts-dashboard:user-action", kwargs={"user_id": self.user.pk, "action": "deactivate"}))
        self.assertEqual(response.status_code, 302)
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_active)

    def test_account_create_and_preference_update(self):
        response = self.client.post(
            reverse("accounts-dashboard:user-create"),
            {"username": "700000003", "phone": "700000003", "first_name": "جديد", "middle_name": "", "third_name": "", "last_name": "مستخدم", "email": "new@example.com", "governorate": "تعز", "role": "customer", "points_balance": 0, "is_active": "on", "password1": "NewSafePass123!", "password2": "NewSafePass123!"},
        )
        self.assertEqual(response.status_code, 302)
        created = User.objects.get(phone="700000003")
        self.assertTrue(created.check_password("NewSafePass123!"))
        self.assertTrue(AccountsUserPreference.objects.filter(user=created).exists())
        response = self.client.post(reverse("accounts-dashboard:user-preferences-save", kwargs={"user_id": created.pk}), {"currency": "SAR", "notifications_enabled": "on"})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(AccountsUserPreference.objects.get(user=created).currency, "SAR")

    def test_non_admin_cannot_open_accounts_dashboard(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("accounts-dashboard:home"))
        self.assertEqual(response.status_code, 403)

    def test_export_is_csv(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse("accounts-dashboard:users-export"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/csv; charset=utf-8")
        self.assertIn("700000002", response.content.decode("utf-8-sig"))

    def test_revoke_api_token_from_dashboard(self):
        token = Token.objects.create(user=self.user)
        response = self.client.post(reverse("accounts-dashboard:user-action", kwargs={"user_id": self.user.pk, "action": "revoke-api-token"}))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Token.objects.filter(pk=token.pk).exists())

    def test_bulk_action_changes_selected_users_and_does_not_disable_admin(self):
        token = Token.objects.create(user=self.other)
        response = self.client.post(
            reverse("accounts-dashboard:users"),
            {"bulk_action": "deactivate", "selected_users": [str(self.user.pk), str(self.other.pk), str(self.admin.pk)]},
        )
        self.assertEqual(response.status_code, 302)
        self.user.refresh_from_db()
        self.other.refresh_from_db()
        self.admin.refresh_from_db()
        self.assertFalse(self.user.is_active)
        self.assertFalse(self.other.is_active)
        self.assertTrue(self.admin.is_active)
        self.assertTrue(Token.objects.filter(pk=token.pk).exists())
