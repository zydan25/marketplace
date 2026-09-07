import logging

from django.apps import AppConfig


logger = logging.getLogger(__name__)


class ServicesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "services"
    verbose_name = "الخدمات"

    def ready(self):
        from . import admin_v4

        # Keep the legacy service editor's field library available without
        # querying the database during Django application initialization.
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

        # Catalog initialization is intentionally explicit via:
        #   python manage.py sync_api_catalog
        # This keeps migrations, tests and worker startup free of database I/O.
