from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import GameProduct, MainServiceCategory, Service, ServiceCategory, TelecomDenomination, TelecomPlan, WifiDenomination, WifiNetwork


class UnifiedDashboardRulesTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(username="svc-admin", password="test-password", is_staff=True)
        self.client.force_login(self.user)
        payments = MainServiceCategory.objects.create(name="التسديدات", slug="payments")
        games = MainServiceCategory.objects.create(name="الألعاب", slug="games")
        self.yem = ServiceCategory.objects.create(main_category=payments, name="يمن موبايل", slug="yemen-mobile")
        self.you = ServiceCategory.objects.create(main_category=payments, name="يو", slug="you")
        self.games_cat = ServiceCategory.objects.create(main_category=games, name="الألعاب", slug="games")
        self.yem_service = Service.objects.create(category=self.yem, name="يمن فئات", slug="yem-denomination", code="yem-denomination")
        self.you_service = Service.objects.create(category=self.you, name="يو فئات", slug="you-denomination", code="you-denomination")
        self.game_service = Service.objects.create(category=self.games_cat, name="فري فاير", slug="freefire", code="freefire")

    def test_cannot_put_yemen_denomination_on_you_service(self):
        response = self.client.post(reverse("admin-services-resources"), {
            "action": "telecom_denom",
            "scope": "yemen-mobile",
            "service": self.you_service.pk,
            "name": "فئة خاطئة",
            "external_code": "bad",
            "face_value": "100",
            "sale_price": "101",
        })
        self.assertEqual(response.status_code, 302)
        self.assertFalse(TelecomDenomination.objects.exists())

    def test_game_product_belongs_to_game_service(self):
        response = self.client.post(reverse("admin-services-resources"), {
            "action": "game",
            "scope": "games",
            "service": self.game_service.pk,
            "name": "100 جوهرة",
            "external_code": "ff100",
            "price": "500",
            "currency": "YER",
        })
        self.assertEqual(response.status_code, 302)
        product = GameProduct.objects.get()
        self.assertEqual(product.service, self.game_service)
        self.assertEqual(product.price, Decimal("500"))


class WifiRuleTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.admin = user_model.objects.create_user(username="wifi-admin", password="test-password", is_staff=True)
        self.client.force_login(self.admin)

    def test_denomination_number_is_generated_and_card_pin_is_optional(self):
        network = WifiNetwork.objects.create(owner=self.admin, name="TestNet", location="Sanaa")
        response = self.client.post(reverse("admin-services-wifi-management"), {
            "action": "wifi_denomination",
            "network": network.pk,
            "name": "100 ميجا",
            "face_value": "100",
            "sale_price": "120",
        })
        self.assertEqual(response.status_code, 302)
        denomination = WifiDenomination.objects.get()
        self.assertTrue(denomination.denomination_number)

        response = self.client.post(reverse("admin-services-wifi-management"), {
            "action": "wifi_card",
            "denomination": denomination.pk,
            "card_number": "user-only",
        })
        self.assertEqual(response.status_code, 302)
        card = denomination.cards.get()
        self.assertEqual(card.pin, "")
