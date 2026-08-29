from django.test import TestCase
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from marketplace.models import User, Wallet
from .models import User as AccountsUser


class AccountsStageOneTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_proxy_points_to_existing_user_table(self):
        user = User.objects.create_user(
            phone="711000001",
            username="711000001",
            password="SafePass123!",
            role="customer",
        )
        proxy = AccountsUser.objects.get(pk=user.pk)

        self.assertEqual(proxy.pk, user.pk)
        self.assertEqual(proxy._meta.db_table, user._meta.db_table)
        self.assertTrue(AccountsUser._meta.proxy)

    def test_registration_uses_accounts_route_and_creates_wallet(self):
        response = self.client.post(
            "/api/auth/register/",
            {
                "phone": "711000002",
                "password": "SafePass456!",
                "first_name": "عميل",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        user = User.objects.get(phone="711000002")
        self.assertTrue(Token.objects.filter(user=user).exists())
        self.assertTrue(Wallet.objects.filter(user=user).exists())

    def test_me_keeps_existing_auth_contract(self):
        user = User.objects.create_user(
            phone="711000003",
            username="711000003",
            password="SafePass789!",
            role="customer",
        )
        token, _ = Token.objects.get_or_create(user=user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

        response = self.client.get("/api/auth/me/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["phone"], "711000003")
