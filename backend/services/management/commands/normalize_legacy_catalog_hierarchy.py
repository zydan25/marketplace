from django.core.management.base import BaseCommand
from django.utils.text import slugify

from services.models import MainServiceCategory, Service, ServiceCategory


class Command(BaseCommand):
    help = "يفصل الخدمات المستوردة من النسخة القديمة إلى ألعاب وبرامج وبطاقات بشكل هرمي."

    def handle(self, *args, **options):
        games_main, _ = MainServiceCategory.objects.get_or_create(
            slug="games",
            defaults={"name": "الألعاب", "icon": "gamepad", "is_active": True},
        )
        programs_main, _ = MainServiceCategory.objects.get_or_create(
            slug="programs",
            defaults={"name": "البرامج والتطبيقات", "icon": "apps", "is_active": True},
        )
        games_category, _ = ServiceCategory.objects.get_or_create(
            main_category=games_main,
            parent=None,
            slug="games",
            defaults={"name": "الألعاب", "is_active": True},
        )
        programs_category, _ = ServiceCategory.objects.get_or_create(
            main_category=programs_main,
            parent=None,
            slug="programs",
            defaults={"name": "البرامج والتطبيقات", "is_active": True},
        )

        moved_games = moved_programs = 0
        for service in Service.objects.filter(metadata__legacy_group_ids__isnull=False).select_related("category"):
            meta = service.metadata or {}
            ids = meta.get("legacy_group_ids") or []
            if not ids:
                continue
            is_program = "#برنامج#" in service.name or "برنامج" in service.name
            target = programs_category if is_program else games_category
            if service.category_id != target.id:
                service.category = target
                service.save(update_fields=["category", "updated_at"])
            service.metadata = {**meta, "catalog_hierarchy": "programs" if is_program else "games"}
            service.save(update_fields=["metadata", "updated_at"])
            if is_program:
                moved_programs += 1
            else:
                moved_games += 1

        self.stdout.write(self.style.SUCCESS(
            f"تم تنظيم الكتالوج: {moved_games} خدمة ألعاب و{moved_programs} خدمة برامج."
        ))
