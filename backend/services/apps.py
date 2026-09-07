import logging

from django.apps import AppConfig


logger = logging.getLogger(__name__)


class ServicesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "services"
    verbose_name = "الخدمات"

    def ready(self):
        from . import admin_v4

        # Provider fields remain available to the service editor. Runtime API
        # validation no longer depends on monkeypatches performed here.
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

        # Idempotent catalog bootstrap. It is deliberately guarded by a
        # table-existence check so migrations/tests are not blocked before the
        # services tables exist. Set SERVICE_CATALOG_BOOTSTRAP=0 to disable.
        if getattr(self, "_catalog_bootstrap_started", False):
            return
        self._catalog_bootstrap_started = True
        try:
            from .catalog_bootstrap import bootstrap_service_catalog
            bootstrap_service_catalog()
        except Exception:  # pragma: no cover - defensive startup guard
            logger.exception("Unable to initialize service catalog bootstrap")
