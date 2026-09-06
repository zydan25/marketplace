from django.core.management.base import BaseCommand

from services.models import ProviderConnection, ProviderLink, Service, ServiceDistribution


class Command(BaseCommand):
    help = "يدقق ربط الخدمات في قاعدة البيانات الحالية ويمنع نشر خدمة مدفوعة بلا مزود/مسار فعال."

    def add_arguments(self, parser):
        parser.add_argument("--strict", action="store_true", help="اعتبر أي خدمة مدفوعة بلا توزيع فعال خطأً قاتلًا")
        parser.add_argument("--provider", default="", help="فحص مزود واحد بالكود")

    def handle(self, *args, **options):
        errors = []
        providers = ProviderConnection.objects.filter(is_active=True)
        if options["provider"]:
            providers = providers.filter(code=options["provider"])
            if not providers.exists():
                errors.append(f"المزود {options['provider']} غير موجود أو غير فعال.")

        for provider in providers.prefetch_related("links"):
            links = list(provider.links.filter(is_active=True))
            if not links:
                errors.append(f"المزود {provider.code}: لا توجد ProviderLink فعالة.")
                continue
            for link in links:
                if not link.path_template.strip():
                    errors.append(f"{provider.code}/{link.code}: path_template فارغ.")
                if not link.http_method or not link.request_encoding:
                    errors.append(f"{provider.code}/{link.code}: طريقة الطلب أو الترميز ناقص.")
                if provider.connection_type == ProviderConnection.Types.SANAACASH:
                    if not provider.userid or not provider.username or not provider.password_encrypted:
                        errors.append(f"{provider.code}: بيانات اعتماد Sanaacash ناقصة.")
                catalog = (link.metadata or {}).get("catalog") or {}
                if catalog.get("enabled"):
                    if not catalog.get("service_code"):
                        errors.append(f"{provider.code}/{link.code}: catalog.service_code مفقود.")
                    if not catalog.get("item_type"):
                        errors.append(f"{provider.code}/{link.code}: catalog.item_type مفقود.")

        active_paid = Service.objects.filter(service_kind=Service.ServiceKinds.PURCHASE, requires_balance=True, is_active=True)
        missing = []
        for service in active_paid:
            route_exists = ServiceDistribution.objects.filter(
                service=service,
                is_active=True,
                provider_link__is_active=True,
                provider_link__provider__is_active=True,
            ).exists()
            if not route_exists:
                missing.append(service.code)
        if missing and options["strict"]:
            errors.append("خدمات مدفوعة بلا ربطية فعالة: " + ", ".join(sorted(missing)))
        elif missing:
            for code in missing:
                self.stdout.write(self.style.WARNING(f"WARNING: {code} بلا ربطية فعالة"))

        self.stdout.write(f"active_providers={providers.count()} active_paid_services={active_paid.count()} missing_routes={len(missing)} errors={len(errors)}")
        if errors:
            for error in errors:
                self.stderr.write(self.style.ERROR(error))
            raise SystemExit("Production route audit failed.")
        self.stdout.write(self.style.SUCCESS("Production provider-route audit passed."))
