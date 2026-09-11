from django.core.management.base import BaseCommand
from django.db import transaction

from services.models import Service
from services.yemen_mobile_catalog_sync import sync_yemen_mobile_catalog


class Command(BaseCommand):
    help = "Replace the canonical Yemen Mobile package catalog with the exact Sanaacash API PDF catalog."

    def add_arguments(self, parser):
        parser.add_argument(
            "--service-code",
            default="yem-offer",
            help="Canonical Yemen Mobile package Service code.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        service = Service.objects.get(code=options["service_code"], is_active=True)
        result = sync_yemen_mobile_catalog(service)
        self.stdout.write(
            self.style.SUCCESS(
                "Yemen Mobile API catalog synchronized: "
                f"{result['created_plans']} plans from {result['expected_source_rows']} source rows."
            )
        )
