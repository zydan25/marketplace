from django.core.management.base import BaseCommand, CommandError

from services.catalog_sync import sync_provider_link
from services.models import ProviderConnection, ProviderLink


class Command(BaseCommand):
    help = "يجلب كتالوجًا موثقًا من المزود ويحدّث الباقات/الألعاب/البطاقات دون حذف البيانات تلقائيًا."

    def add_arguments(self, parser):
        parser.add_argument("--provider", required=True, help="كود المزود")
        parser.add_argument("--link", required=True, help="كود ProviderLink المهيأ للكتالوج")
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument("--prune", action="store_true", help="يعطّل العناصر التي اختفت من الرد فقط؛ لا يحذفها")

    def handle(self, *args, **options):
        provider = ProviderConnection.objects.filter(code=options["provider"], is_active=True).first()
        if not provider:
            raise CommandError("المزود غير موجود أو غير فعال.")
        link = ProviderLink.objects.filter(code=options["link"], provider=provider, is_active=True).first()
        if not link:
            raise CommandError("مسار الكتالوج غير موجود أو غير فعال للمزود المحدد.")
        try:
            result = sync_provider_link(link, dry_run=options["dry_run"], prune=options["prune"])
        except Exception as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(self.style.SUCCESS(
            f"service={result['service']} item_type={result['item_type']} seen={result['seen']} saved={result['saved']} disabled_unpriced={result['disabled_unpriced']} dry_run={result['dry_run']}"
        ))
