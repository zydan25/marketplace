from django.core.management.base import BaseCommand, CommandError

from services.catalog_base import SERVICES
from services.catalog_games import GAMES_AND_CARDS
from services.catalog_operators import SABA_DENOMINATIONS, SABA_OFFERS, YOU_DENOMINATIONS, YOU_OFFERS
from services.catalog_yemen_contract import YEMEN_MOBILE_OFFERS
from services.models import GameProduct, Service, TelecomDenomination, TelecomPlan


class Command(BaseCommand):
    help = "تحقق صارم من وجود كتالوج عقد API داخل قاعدة البيانات دون حذف بيانات legacy."

    def add_arguments(self, parser):
        parser.add_argument("--fail", action="store_true", help="إرجاع خطأ عند وجود نقص")

    def handle(self, *args, **options):
        expected_codes = {code for code, *_ in SERVICES}
        actual_codes = set(Service.objects.values_list("code", flat=True))
        missing_services = sorted(expected_codes - actual_codes)
        inactive_services = sorted(expected_codes & actual_codes & set(Service.objects.filter(is_active=False).values_list("code", flat=True)))

        missing_games = sorted(set(GAMES_AND_CARDS) - actual_codes)
        active_games = list(Service.objects.filter(code__in=GAMES_AND_CARDS, is_active=True).values_list("code", flat=True))
        game_product_count = GameProduct.objects.filter(service__code__in=GAMES_AND_CARDS, is_active=True).count()

        yem_service = Service.objects.filter(code="yem-bill-offer").first()
        yem_plan_count = TelecomPlan.objects.filter(service__code="yem-bill-offer", is_active=True).count()
        expected_yem_plan_count = len(YEMEN_MOBILE_OFFERS)

        you_denom_count = TelecomDenomination.objects.filter(service__code="you-denomination", is_active=True).count()
        saba_denom_count = TelecomDenomination.objects.filter(service__code="saba-denomination", is_active=True).count()
        you_offer_count = TelecomPlan.objects.filter(service__code="you-offer", is_active=True).count()
        saba_offer_count = TelecomPlan.objects.filter(service__code="saba-offer", is_active=True).count()

        checks = {
            "services": (len(expected_codes), len(expected_codes) - len(missing_services)),
            "games_and_cards_services": (len(GAMES_AND_CARDS), len(active_games)),
            "yemen_mobile_plans": (expected_yem_plan_count, yem_plan_count),
            "you_denominations": (len(YOU_DENOMINATIONS), you_denom_count),
            "you_offers": (len(YOU_OFFERS), you_offer_count),
            "saba_denominations": (len(SABA_DENOMINATIONS), saba_denom_count),
            "saba_offers": (len(SABA_OFFERS), saba_offer_count),
        }

        self.stdout.write("=== Service catalog verification ===")
        for label, (expected, actual) in checks.items():
            status = "OK" if actual >= expected else "MISSING"
            self.stdout.write(f"{status:8} {label}: expected>={expected}, actual={actual}")
        self.stdout.write(f"ACTIVE GAME/CARD PRODUCTS: {game_product_count}")

        if missing_services:
            self.stdout.write(self.style.ERROR("Missing services: " + ", ".join(missing_services)))
        if inactive_services:
            self.stdout.write(self.style.WARNING("Inactive API services: " + ", ".join(inactive_services)))
        if missing_games:
            self.stdout.write(self.style.ERROR("Missing game/card service codes: " + ", ".join(missing_games)))

        failing = [label for label, (expected, actual) in checks.items() if actual < expected]
        if (missing_services or missing_games or failing) and options["fail"]:
            raise CommandError("فشل تحقق كتالوج الخدمات: " + ", ".join(failing or ["service definitions"]))
        if failing:
            self.stdout.write(self.style.WARNING("Catalog verification completed with missing rows."))
        else:
            self.stdout.write(self.style.SUCCESS("Catalog service/plan definition checks passed."))
