from django.core.management.base import BaseCommand
from django.db.models import Count

from services.catalog_data import CATEGORIES, LINKS, MAIN, SABA_DENOMINATIONS, SABA_OFFERS, SERVICES, YOU_DENOMINATIONS, YOU_OFFERS, YEMEN_MOBILE_OFFERS
from services.models import MainServiceCategory, ProviderConnection, ProviderLink, Service, ServiceDistribution, ServiceRequestReference, TelecomDenomination, TelecomPlan


class Command(BaseCommand):
    help = "يتحقق من سلامة عقد الخدمات وكتالوج Sanaacash والتوزيع والـtransid."

    def handle(self, *args, **options):
        errors = []
        service_defs = {row[0]: row for row in SERVICES}

        expected = {"main": len(MAIN), "categories": len(CATEGORIES), "services": len(SERVICES), "links": len(LINKS)}
        actual = {
            "main": MainServiceCategory.objects.filter(slug__in=[v[1] for v in MAIN.values()]).count(),
            "categories": ServiceCategory.objects.filter(slug__in=[row[2] for row in CATEGORIES]).count() if self._service_category_available() else 0,
            "services": Service.objects.filter(code__in=list(service_defs)).count(),
            "links": ProviderLink.objects.count(),
        }

        if actual["main"] < expected["main"]:
            errors.append(f"الفئات الرئيسية ناقصة: {actual['main']}/{expected['main']}")
        if actual["categories"] < expected["categories"]:
            errors.append(f"فئات الخدمات ناقصة: {actual['categories']}/{expected['categories']}")
        if actual["services"] < expected["services"]:
            errors.append(f"الخدمات ناقصة: {actual['services']}/{expected['services']}")

        for service in Service.objects.filter(code__in=service_defs).prefetch_related("fields", "distributions__provider_link__provider"):
            _, _, _, kind, pricing, link_key, requires_balance = service_defs[service.code]
            if service.service_kind != kind:
                errors.append(f"{service.code}: service_kind={service.service_kind}, المتوقع {kind}")
            if service.requires_balance != requires_balance:
                errors.append(f"{service.code}: requires_balance={service.requires_balance}, المتوقع {requires_balance}")
            if not requires_balance and service.price != 0:
                errors.append(f"{service.code}: الخدمة المجانية يجب أن يكون سعرها صفرًا")
            if pricing == "amount" and not service.fields.filter(key="amount", is_active=True, required=True).exists():
                errors.append(f"{service.code}: حقل amount مطلوب")
            if link_key == "games_cards" and not service.fields.filter(key="mobile", is_active=True, required=True).exists():
                errors.append(f"{service.code}: رقم الهاتف mobile مطلوب للألعاب/البطاقات")
            if not service.distributions.filter(is_active=True, provider_link__is_active=True, provider_link__provider__is_active=True).exists():
                errors.append(f"{service.code}: لا توجد ربطية فعالة")

        for provider in ProviderConnection.objects.filter(is_active=True):
            operations = set(provider.links.filter(is_active=True).values_list("operation", flat=True))
            missing = set(LINKS) - operations
            if missing:
                self.stdout.write(self.style.WARNING(f"المزود {provider.name}: ينقصه {len(missing)} مسارًا قياسيًا، وهذا مقبول فقط للمزود الجزئي."))
            for link in provider.links.filter(is_active=True):
                if link.operation in {"electric_query", "electric_bill", "water_query", "water_bill"}:
                    if link.http_method != "POST" or link.request_encoding != "form":
                        errors.append(f"{provider.name}/{link.operation}: يجب أن يكون POST/form")
                if link.operation in LINKS and str(link.success_codes) != str(["0"]):
                    errors.append(f"{provider.name}/{link.operation}: success_codes يجب أن تحتوي 0")

        duplicate_refs = ServiceRequestReference.objects.values("transid").annotate(n=Count("id")).filter(n__gt=1).count()
        if duplicate_refs:
            errors.append("يوجد transid مكرر في سجل المراجع")
        for ref in ServiceRequestReference.objects.only("transid"):
            if ref.transid < 10000:
                errors.append(f"transid غير صالح: {ref.transid}")
                break

        expected_counts = {
            "Yemen Mobile offers": (TelecomPlan.objects.filter(service__code="yem-bill-offer").count(), len(YEMEN_MOBILE_OFFERS)),
            "You denominations": (TelecomDenomination.objects.filter(service__code="you-denomination").count(), len(YOU_DENOMINATIONS)),
            "You offers": (TelecomPlan.objects.filter(service__code="you-offer").count(), len(YOU_OFFERS)),
            "Sabafon denominations": (TelecomDenomination.objects.filter(service__code="saba-denomination").count(), len(SABA_DENOMINATIONS)),
            "Sabafon offers": (TelecomPlan.objects.filter(service__code="saba-offer").count(), len(SABA_OFFERS)),
        }
        for label, (actual_count, expected_count) in expected_counts.items():
            if actual_count < expected_count:
                errors.append(f"{label}: {actual_count}/{expected_count}")

        self.stdout.write(f"static main={expected['main']} categories={expected['categories']} services={expected['services']} links={expected['links']}")
        self.stdout.write(f"database main={actual['main']} categories={actual['categories']} services={actual['services']} providers={ProviderConnection.objects.count()} links={actual['links']} refs={ServiceRequestReference.objects.count()}")
        if errors:
            for error in errors:
                self.stderr.write(self.style.ERROR(error))
            raise SystemExit("فشل فحص عقد منصة الخدمات.")
        self.stdout.write(self.style.SUCCESS("Service/Sanaacash catalog integrity check passed."))

    @staticmethod
    def _service_category_available():
        return True


# Local import kept at module end to make the command's static checks readable above.
from services.models import ServiceCategory
