from django.core.management.base import BaseCommand
from django.db import transaction

from services.catalog_games import GAMES_AND_CARDS
from services.management.commands.provision_sanaacash import provision, seed_catalog
from services.models import Service, TelecomPlan, TelecomPlanType


PAYMENT_TYPE_LABELS = {
    "prepaid": "دفع مسبق",
    "postpaid": "فوترة",
    "paid": "مدفوع",
}


class Command(BaseCommand):
    help = "تهيئة كتالوج الخدمات من عقد API والبيانات المهيأة، مع تطبيع أنواع الباقات."

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

        type_count = 0
        plan_services = Service.objects.filter(is_active=True, telecom_plans__is_active=True).distinct()
        for service in plan_services:
            groups = {}
            for plan in TelecomPlan.objects.filter(service=service, is_active=True).order_by("sort_order", "id"):
                payment = (plan.payment_type or "other").strip().lower() or "other"
                line = (plan.line_type or "all").strip().lower() or "all"
                code = f"{payment}:{line}"[:80]
                groups.setdefault(code, []).append(plan)

            for sort_order, (code, plans) in enumerate(groups.items()):
                payment = (plans[0].payment_type or "other").strip().lower() or "other"
                line = (plans[0].line_type or "all").strip()
                label = PAYMENT_TYPE_LABELS.get(payment, "نوع باقة آخر")
                if line and line.lower() != "all":
                    label = f"{label} - {line}"
                plan_type, _ = TelecomPlanType.objects.update_or_create(
                    service=service,
                    code=code,
                    defaults={
                        "name": label,
                        "description": line,
                        "sort_order": sort_order,
                        "is_active": True,
                    },
                )
                plan_type.plans.set(plans)
                type_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"تمت تهيئة {len(services)} خدمة، ووضع وسم المصدر على {tagged} خدمة، وتطبيع {type_count} نوع باقة."
            )
        )
        self.stdout.write(
            "بيانات المنتج والأسعار التي لا يعرّفها عقد API تبقى من الكتالوج/النسخة الاحتياطية؛ لا يتم اختلاق خدمات مثل Netflix أو Shahid أو Canva."
        )
