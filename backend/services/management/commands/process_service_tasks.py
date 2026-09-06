import logging
import signal
import time

from django.core.management.base import BaseCommand

from services.executor import process_task


logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "يشغّل قائمة خدمات الخلفية باستمرار، مع تعافي من أخطاء المهمة وعدم إسقاط العامل كاملًا."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=1, help="عدد المهام في الدورة الواحدة")
        parser.add_argument("--loop", action="store_true", help="استمر في العمل كعامل خلفي")
        parser.add_argument("--sleep", type=float, default=1.0, help="ثواني الانتظار عند خلو القائمة")
        parser.add_argument("--error-sleep", type=float, default=2.0, help="ثواني الانتظار بعد خطأ غير متوقع")

    def handle(self, *args, **options):
        limit = max(1, options["limit"])
        sleep_seconds = max(0.1, options["sleep"])
        error_sleep = max(0.5, options["error_sleep"])
        stop = {"requested": False}

        def _stop(_signum, _frame):
            stop["requested"] = True

        signal.signal(signal.SIGTERM, _stop)
        signal.signal(signal.SIGINT, _stop)

        while True:
            if stop["requested"]:
                self.stdout.write(self.style.WARNING("تم طلب إيقاف عامل الخدمات بأمان."))
                return

            processed = 0
            for _ in range(limit):
                if stop["requested"]:
                    return
                try:
                    task = process_task()
                except Exception as exc:  # noqa: BLE001 - worker must survive one bad task
                    logger.exception("Service worker task failed unexpectedly")
                    self.stderr.write(self.style.ERROR(f"خطأ غير متوقع في عامل الخدمات: {exc}"))
                    if not options["loop"]:
                        raise
                    time.sleep(error_sleep)
                    break
                if task is None:
                    break
                processed += 1
                self.stdout.write(self.style.SUCCESS(f"تمت معالجة المهمة #{task.pk}: {task.status}"))

            if not options["loop"]:
                break
            if processed == 0:
                time.sleep(sleep_seconds)
