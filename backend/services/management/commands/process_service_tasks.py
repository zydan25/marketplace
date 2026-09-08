import time

from django.core.management.base import BaseCommand

from services.executor import process_task


class Command(BaseCommand):
    help = "يشغّل قائمة خدمات الخلفية بالتسلسل، من أقدم مهمة مستحقة إلى الأحدث."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=1, help="عدد المهام في التشغيل الواحد")
        parser.add_argument("--loop", action="store_true", help="استمر في العمل كعامل خلفي")
        parser.add_argument("--sleep", type=float, default=1.0, help="ثواني الانتظار عند خلو القائمة")

    def handle(self, *args, **options):
        limit = max(1, options["limit"])
        while True:
            processed = 0
            for _ in range(limit):
                task = process_task()
                if task is None:
                    break
                processed += 1
                self.stdout.write(self.style.SUCCESS(f"تمت معالجة المهمة #{task.pk}: {task.status}"))
            if not options["loop"]:
                break
            if processed == 0:
                time.sleep(max(0.1, options["sleep"]))
