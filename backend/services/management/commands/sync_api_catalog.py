from django.core.management.base import BaseCommand
from django.db import transaction

from services.catalog_games import GAMES_AND_CARDS
from services.catalog_repair import repair_hierarchy
from services.management.commands.provision_sanaacash import provision, provision_links, seed_catalog
from services.models import ProviderConnection


class Command(BaseCommand):
    help = "تهيئة كتالوج الخدمات من عقد API، إصلاح فروع الخدمات والباقات، وربط مسارات المزود الفعالة."

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
        for provider in ProviderConnection.objects.filter(is_active=True):
            _, _, current_services = provision()
            links = provision_links(provider, current_services)
            route_count += len(links)

        stats = repair_hierarchy()
        self.stdout.write(
            self.style.SUCCESS(
                f"تمت تهيئة {len(services)} خدمة، ووسم {tagged} خدمة API، وتجهيز {route_count} مسار مزود، وإصلاح {stats['plan_types']} نوع باقة."
            )
        )
        self.stdout.write(
            "تم الحفاظ على خدمات وعناصر الكتالوج/النسخة الاحتياطية دون اختلاق خدمات غير موجودة في عقد API."
        )
