from django.core.management.base import BaseCommand

from services.management.commands.provision_sanaacash import CATEGORIES, LINKS, MAIN, SERVICES
from services.models import MainServiceCategory, ProviderLink, Service, ServiceCategory


class Command(BaseCommand):
    help = "يتحقق من اكتمال قالب Sanaacash والعلاقات الأساسية دون تعديل البيانات."

    def handle(self, *args, **options):
        expected = {"main": len(MAIN), "categories": len(CATEGORIES), "services": len(SERVICES), "link_templates": len(LINKS)}
        actual = {
            "main": MainServiceCategory.objects.filter(slug__in=[slug for _, slug in MAIN.values()]).count(),
            "categories": ServiceCategory.objects.filter(slug__in=[slug for _, _, slug in CATEGORIES]).count(),
            "services": Service.objects.filter(code__in=[code for _, _, code, _, _ in SERVICES]).count(),
            "link_templates": len(LINKS),
        }
        self.stdout.write(f"expected main={expected['main']} categories={expected['categories']} services={expected['services']} links-template={expected['link_templates']}")
        self.stdout.write(f"actual main={actual['main']} categories={actual['categories']} services={actual['services']}")
        if actual["main"] != expected["main"] or actual["categories"] != expected["categories"] or actual["services"] != expected["services"]:
            raise SystemExit("Sanaacash catalog is incomplete; run provision_sanaacash first.")
        self.stdout.write(self.style.SUCCESS("Sanaacash catalog integrity check passed."))
