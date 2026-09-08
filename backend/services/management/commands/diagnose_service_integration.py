from django.core.management.base import BaseCommand

from services.models import ProviderConnection, Service, ServiceDistribution, ServiceTask, ServiceTransaction


class Command(BaseCommand):
    help = "يفحص أسباب فشل الاستعلامات والتسديدات ومسارات المزود والعامل الخلفي دون تنفيذ عملية للعميل."

    def add_arguments(self, parser):
        parser.add_argument("--verbose", action="store_true")

    def handle(self, *args, **options):
        errors = []
        providers = list(ProviderConnection.objects.filter(is_active=True))
        self.stdout.write(f"مزودون فعالون: {len(providers)}")
        for provider in providers:
            credential_state = all((provider.base_url, provider.userid, provider.username, provider.password_encrypted))
            self.stdout.write(f"- {provider.name}: base_url={provider.base_url!r}, credentials={'OK' if credential_state else 'MISSING'}, links={provider.links.filter(is_active=True).count()}")
            if not credential_state:
                errors.append(f"بيانات مزود ناقصة: {provider.name}")
            if not str(provider.base_url).startswith("https://"):
                errors.append(f"رابط المزود يجب أن يكون HTTPS في الإنتاج: {provider.name}")

        services = Service.objects.filter(is_active=True)
        no_route = []
        for service in services:
            if service.service_kind == Service.ServiceKinds.PURCHASE or service.service_kind == Service.ServiceKinds.QUERY:
                routed = ServiceDistribution.objects.filter(
                    service=service,
                    is_active=True,
                    provider_link__is_active=True,
                    provider_link__provider__is_active=True,
                ).exists()
                if not routed:
                    no_route.append(service.code)
        self.stdout.write(f"خدمات بلا ربطية فعالة: {len(no_route)}")
        if options["verbose"]:
            for code in no_route:
                self.stdout.write(self.style.WARNING(f"  NO_ROUTE: {code}"))

        queued = ServiceTask.objects.filter(status__in=[ServiceTask.Statuses.QUEUED, ServiceTask.Statuses.RETRY]).count()
        running = ServiceTask.objects.filter(status=ServiceTask.Statuses.RUNNING).count()
        pending = ServiceTransaction.objects.filter(status__in=[ServiceTransaction.Status.PENDING_PROVIDER, ServiceTransaction.Status.MANUAL_REVIEW]).count()
        self.stdout.write(f"مهام انتظار/إعادة: {queued} | قيد التشغيل: {running} | عمليات تحتاج متابعة: {pending}")
        self.stdout.write("العامل المطلوب للإنتاج: python manage.py process_service_tasks --loop")
        if queued and running == 0:
            errors.append("هناك مهام في الانتظار ولا يظهر عامل مشغّل؛ شغّل marketplace-services-worker.service")

        if no_route:
            errors.append(f"توجد {len(no_route)} خدمة بلا ServiceDistribution فعالة")

        if errors:
            self.stdout.write(self.style.ERROR("أسباب محتملة تحتاج إصلاح:"))
            for error in errors:
                self.stdout.write(self.style.ERROR(f"- {error}"))
            raise SystemExit(2)
        self.stdout.write(self.style.SUCCESS("فحص الربط الأساسي سليم؛ فشل عملية بعينها يحتاج قراءة ServiceTransaction/ServiceRequestLog واستجابة المزود."))
