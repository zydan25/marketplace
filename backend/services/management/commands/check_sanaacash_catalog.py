from django.core.management.base import BaseCommand

from services.management.commands.provision_sanaacash import CATEGORIES, LINKS, MAIN, SERVICES
from services.models import MainServiceCategory, ProviderConnection, ProviderLink, Service, ServiceCategory, ServiceDistribution, ServiceField


class Command(BaseCommand):
    help = "يتحقق من صحة قالب الخدمات وتهيئة Sanaacash/المزودات المتوافقة دون تعديل البيانات."

    def handle(self, *args, **options):
        errors = []
        service_defs = {code: (category_slug, pricing, link_key) for category_slug, _, code, pricing, link_key in SERVICES}

        for main_key, (_, slug) in MAIN.items():
            if not slug:
                errors.append(f"الفئة الرئيسية {main_key} بلا slug")
        for category_main, _, slug in CATEGORIES:
            if category_main not in MAIN:
                errors.append(f"الفئة {slug} تشير إلى فئة رئيسية غير معروفة: {category_main}")

        for category_slug, _, code, pricing, link_key in SERVICES:
            if category_slug not in {slug for _, _, slug in CATEGORIES}:
                errors.append(f"الخدمة {code} تشير إلى فئة غير موجودة: {category_slug}")
            if link_key not in LINKS:
                errors.append(f"الخدمة {code} تشير إلى مسار غير معرف: {link_key}")
            if pricing not in {"fixed", "amount", "item"}:
                errors.append(f"التسعير غير صالح للخدمة {code}: {pricing}")

        required_link_keys = set(LINKS)
        for code, (_, path, fixed, field_map) in LINKS.items():
            if not path:
                errors.append(f"المسار {code} بلا path")
            if not isinstance(fixed, dict) or not isinstance(field_map, dict):
                errors.append(f"تعريف المسار {code} غير صالح")

        expected = {"main": len(MAIN), "categories": len(CATEGORIES), "services": len(SERVICES), "link_templates": len(LINKS)}
        actual = {
            "main": MainServiceCategory.objects.filter(slug__in=[slug for _, slug in MAIN.values()]).count(),
            "categories": ServiceCategory.objects.filter(slug__in=[slug for _, _, slug in CATEGORIES]).count(),
            "services": Service.objects.filter(code__in=[code for _, _, code, _, _ in SERVICES]).count(),
        }
        provider_count = ProviderConnection.objects.count()
        configured_links = ProviderLink.objects.count()
        active_distributions = ServiceDistribution.objects.filter(is_active=True, provider_link__is_active=True, provider_link__provider__is_active=True).count()

        self.stdout.write(f"static main={expected['main']} categories={expected['categories']} services={expected['services']} links={expected['link_templates']}")
        self.stdout.write(f"database main={actual['main']} categories={actual['categories']} services={actual['services']} providers={provider_count} links={configured_links} active-distributions={active_distributions}")

        if provider_count:
            for provider in ProviderConnection.objects.filter(is_active=True):
                active_ops = set(provider.links.filter(is_active=True).values_list("operation", flat=True))
                missing = required_link_keys - active_ops
                if missing:
                    self.stdout.write(self.style.WARNING(f"المزود {provider.name} ينقصه {len(missing)} مسار قياسي؛ هذا مسموح إذا كان مزودًا جزئيًا."))

        if actual["main"] and actual["main"] != expected["main"]:
            errors.append("عدد الفئات الرئيسية المزروعة لا يطابق القالب")
        if actual["categories"] and actual["categories"] != expected["categories"]:
            errors.append("عدد فئات الخدمات المزروعة لا يطابق القالب")
        if actual["services"] and actual["services"] != expected["services"]:
            errors.append("عدد الخدمات المزروعة لا يطابق القالب")

        for service in Service.objects.filter(code__in=service_defs):
            _, pricing, _ = service_defs[service.code]
            amount_field = service.fields.filter(key="amount", is_active=True).first()
            if pricing == "amount" and (amount_field is None or not amount_field.required):
                errors.append(f"الخدمة {service.code} تسعيرها بالمبلغ لكن حقل amount غير مطلوب")

        if errors:
            for error in errors:
                self.stderr.write(self.style.ERROR(error))
            raise SystemExit("فشل فحص تهيئة منصة الخدمات.")
        self.stdout.write(self.style.SUCCESS("Service/Sanaacash catalog integrity check passed."))
