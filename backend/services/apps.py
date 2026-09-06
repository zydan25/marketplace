from django.apps import AppConfig


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
