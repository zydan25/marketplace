from decimal import Decimal

from django.core.management.base import BaseCommand

from services.models import DigitalProduct, GameProduct, Service, ServiceOption, TelecomDenomination, TelecomPlan


ITEM_MODELS = {
    "ServiceOption": ServiceOption,
    "TelecomDenomination": TelecomDenomination,
    "TelecomPlan": TelecomPlan,
    "GameProduct": GameProduct,
    "DigitalProduct": DigitalProduct,
}


class Command(BaseCommand):
    help = "يفحص كتالوج الخدمات للتأكد من عدم وجود عنصر مدفوع قابل للتنفيذ بلا سعر موثق."

    def add_arguments(self, parser):
        parser.add_argument("--fail", action="store_true")

    def handle(self, *args, **options):
        errors = []
        purchase_codes = set(
            Service.objects.filter(service_kind=Service.ServiceKinds.PURCHASE, requires_balance=True, is_active=True)
            .values_list("id", flat=True)
        )
        for model_name, model in ITEM_MODELS.items():
            for item in model.objects.filter(is_active=True, service_id__in=purchase_codes).select_related("service").iterator():
                meta = getattr(item, "metadata", {}) or {}
                if meta.get("purchaseable", True) is False:
                    continue
                requires_balance = meta.get("requires_balance", True)
                if requires_balance is False:
                    continue
                raw_price = getattr(item, "sale_price", getattr(item, "price", 0))
                try:
                    price = Decimal(str(raw_price))
                except Exception:
                    price = Decimal("0")
                if price <= 0:
                    errors.append(f"{model_name}#{item.pk} service={item.service.code}: purchaseable with non-positive price")

        self.stdout.write(f"purchase_services={len(purchase_codes)} errors={len(errors)}")
        for error in errors:
            self.stderr.write(self.style.ERROR(error))
        if errors and options["fail"]:
            raise SystemExit("Service catalog audit failed.")
        self.stdout.write(self.style.SUCCESS("Service catalog audit completed."))
