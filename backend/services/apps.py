import logging
import os
import sys

from django.apps import AppConfig


logger = logging.getLogger(__name__)


class ServicesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "services"
    verbose_name = "الخدمات"

    def ready(self):
        # Import the extension model during app initialization so Django's
        # registry knows about it even though it lives in a focused module.
        from . import admin_v4
        from .settings_models import ServiceSetting  # noqa: F401

        extra_fields = [
            ("external_code", "الكود الخارجي", "text"),
            ("num", "رقم/فئة المزود", "text"),
            ("type", "نوع الخدمة لدى المزود", "text"),
            ("offerid", "معرف الباقة", "text"),
            ("offerkey", "مفتاح الباقة", "text"),
            ("method", "طريقة العملية", "select"),
            ("solfa", "سلفة", "select"),
            ("rasid", "الرصيد المطلوب", "decimal"),
        ]
        existing_keys = {row[0] for row in admin_v4.FIELD_LIBRARY}
        for row in extra_fields:
            if row[0] not in existing_keys:
                admin_v4.FIELD_LIBRARY.append(row)
                existing_keys.add(row[0])
        admin_v4.FIELD_MAP = {key: (label, typ) for key, label, typ in admin_v4.FIELD_LIBRARY}

        # Never start the background worker while migrations/imports or other
        # Django management tasks are running. This is also controllable by an
        # explicit environment variable for scripts that call django.setup().
        if os.getenv("DISABLE_EMBEDDED_WORKER", "0") == "1":
            return

        management_commands = {
            "check",
            "migrate",
            "makemigrations",
            "showmigrations",
            "shell",
            "dumpdata",
            "loaddata",
            "collectstatic",
            "test",
            "createsuperuser",
            "changepassword",
        }
        command = sys.argv[1] if len(sys.argv) > 1 else ""
        if command in management_commands:
            return

        # Gunicorn runs multiple workers; the embedded thread is protected by
        # a host-level singleton lock so only one worker executes tasks.
        try:
            from .embedded_worker import start_embedded_worker
            start_embedded_worker()
        except Exception:
            logger.exception("Unable to start embedded services worker")
