from collections import defaultdict

from django.core.management.base import BaseCommand
from django.db import transaction

from services.management.commands.provision_sanaacash import provision, seed_catalog
from services.models import GameProduct, Service
from services.catalog_games import GAMES_AND_CARDS


class Command(BaseCommand):
    help = "تهيئة كتالوج الخدمات كاملاً من عقد API والبيانات المهيأة، دون بيانات اعتماد المزود."

    @transaction.atomic
    def handle(self, *args, **options):
        _, _, services = provision()
        seed_catalog(services)
        for code in GAMES_AND_CARDS:
            service = services.get(code)
            if service is not None:
                service.metadata = {**(service.metadata or {}), "api_catalog": True, "catalog_code": code}
                service.save(update_fields=["metadata"])
        self.stdout.write(self.style.SUCCESS(f"تمت تهيئة {len(services)} خدمة من عقد API."))
        self.stdout.write("ملاحظة: ملف API يحدد أكواد خدمات الألعاب والبطاقات وحقول الطلب، أما وحدات/أسعار المنتجات التفصيلية للألعاب فتأتي من كتالوج المنتجات/النسخة الاحتياطية ولا يتم اختلاقها.")
