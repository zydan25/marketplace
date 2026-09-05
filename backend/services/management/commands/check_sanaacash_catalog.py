from django.core.management.base import BaseCommand
from django.db import connection

from services.management.commands.provision_sanaacash import LINKS, SERVICES, CATEGORIES
from services.models import ProviderConnection, ProviderLink, Service, ServiceCategory, ServiceDistribution, MainServiceCategory


class Command(BaseCommand):
    help = "يتحقق من اكتمال قالب Sanaacash والعلاقات الأساسية دون تعديل البيانات."

    def handle(self, *args, **options):
        expected = {
            "main": len({key for key, _ in [(k, v) for k, v in []]}),
            "categories": len(CATEGORIES),
            "services": len(SERVICES),
            "links": len(LINKS),
        }
        actual = {
            "main": MainServiceCategory.objects.filter(slug__in=["التسديدات", "الألعاب", "البرامج-والبطاقات"]).count(),
            "categories": ServiceCategory.objects.filter(slug__in=[slug for _, _, slug in CATEGORIES]).count(),
            "services": Service.objects.filter(code__in=[code for _, _, code, _, _ in SERVICES]).count(),
            "links": ProviderLink.objects.filter(operation__in=LINKS.keys()).count(),
        }
        self.stdout.write(f"expected categories={expected['categories']} services={expected['services']} links-template={expected['links']}")
        self.stdout.write(f"actual categories={actual['categories']} services={actual['services']} provider-links={actual['links']}")
        if actual["categories"] != expected["categories"] or actual["services"] != expected["services"]:
            raise SystemExit("Sanaacash catalog is incomplete; run provision_sanaacash first.")
        self.stdout.write(self.style.SUCCESS("Sanaacash catalog integrity check passed."))
