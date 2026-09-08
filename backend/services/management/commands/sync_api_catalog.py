from django.core.management.base import BaseCommand
from django.db import transaction

from services.catalog_games import GAMES_AND_CARDS
from services.catalog_repair import repair_hierarchy
from services.management.commands.provision_sanaacash import provision, provision_links, seed_catalog
from services.models import ProviderConnection


class Command(BaseCommand):
    help = "تهيئة كتالوج الخدمات من عقد API، إصلاح فروع الخدمات والباقات والألعاب، وربط مسارات المزود الفعالة."

    @transaction.atomic
    def handle(self, *args, **options):
        _, _, services = provision()
        seed_catalog(services)

        tagged = 0
        for code in GAMES_AND_CARDS:
            service = services.get(code)
            if service is None:
                continue
            service.metadata = {
                **(service.metadata or {}),
                "api_catalog": True,
                "catalog_code": code,
                "catalog_source": "api 1 (59).pdf",
            }
            service.save(update_fields=["metadata"])
            tagged += 1

        route_count = 0
        sanaacash_providers = ProviderConnection.objects.filter(
            is_active=True,
            connection_type=ProviderConnection.Types.SANAACASH,
        )
        for provider in sanaacash_providers:
            links = provision_links(provider, services)
            route_count += len(links)

        stats = repair_hierarchy()
        self.stdout.write(
            self.style.SUCCESS(
                f"تمت تهيئة {len(services)} خدمة، ووسم {tagged} خدمة API، وتجهيز {route_count} مسار مزود، وإصلاح {stats['plan_types']} نوع باقة."
            )
        )
        self.stdout.write(
            "تم الحفاظ على الكتالوج التاريخي دون اختلاق خدمات أو برامج غير موثقة في عقد API."
        )
