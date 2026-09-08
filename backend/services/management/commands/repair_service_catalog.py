from django.core.management.base import BaseCommand
from django.db import transaction

from services.catalog_repair import repair_hierarchy
from services.management.commands.provision_sanaacash import provision, seed_catalog


class Command(BaseCommand):
    help = "يبني فروع الخدمات والباقات والألعاب والبرامج ويربط أنواع الباقات دون حذف البيانات القديمة."

    @transaction.atomic
    def handle(self, *args, **options):
        _, _, services = provision()
        seed_catalog(services)
        stats = repair_hierarchy()
        self.stdout.write(
            self.style.SUCCESS(
                f"اكتمل إصلاح هيكل الكتالوج: {len(services)} خدمة، {stats['plan_types']} نوع باقة."
            )
        )
