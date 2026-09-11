from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.text import slugify

from services.models import Service, ServiceField
from services.settings_models import ServiceSetting


TARGETS = (
    {
        "code": "post-query-adsl",
        "name": "استعلام يمن نت ADSL",
        "slug": "yemen-net-adsl-query",
        "setting_key": "yemen_net_adsl_query",
        "description": "استعلام حساب يمن نت ADSL. عقد المزود الحالي يستخدم /post?action=query ولا يقبل type في الاستعلام؛ التفريق هنا محلي في الخدمة المختارة.",
        "service_type": "adsl",
    },
    {
        "code": "post-query-line",
        "name": "استعلام هاتف ثابت يمن نت",
        "slug": "yemen-net-line-query",
        "setting_key": "yemen_net_line_query",
        "description": "استعلام حساب الهاتف الثابت يمن نت. عقد المزود الحالي يستخدم /post?action=query ولا يقبل type في الاستعلام؛ التفريق هنا محلي في الخدمة المختارة.",
        "service_type": "line",
    },
)


class Command(BaseCommand):
    help = "Create separate local Yemen Net ADSL and fixed-line query services/settings."

    @transaction.atomic
    def handle(self, *args, **options):
        legacy = Service.objects.filter(code="post-query").select_related("category").first()
        if not legacy:
            raise self.CommandError("الخدمة post-query غير موجودة؛ شغّل provision_services_v2 أولاً.")

        category = legacy.category
        created = []
        for target in TARGETS:
            service, was_created = Service.objects.get_or_create(
                code=target["code"],
                defaults={
                    "category": category,
                    "name": target["name"],
                    "slug": target["slug"],
                    "description": target["description"],
                    "service_kind": Service.ServiceKinds.QUERY,
                    "pricing_mode": Service.PricingModes.FIXED,
                    "requires_balance": False,
                    "currency": "YER",
                    "metadata": {
                        "canonical": True,
                        "provider_family": "yemen_post",
                        "provider_service_type": target["service_type"],
                        "query_endpoint_has_type_parameter": False,
                    },
                    "is_active": True,
                },
            )
            service.category = category
            service.name = target["name"]
            service.slug = target["slug"]
            service.description = target["description"]
            service.service_kind = Service.ServiceKinds.QUERY
            service.pricing_mode = Service.PricingModes.FIXED
            service.requires_balance = False
            metadata = dict(service.metadata or {})
            metadata.update({
                "canonical": True,
                "provider_family": "yemen_post",
                "provider_service_type": target["service_type"],
                "query_endpoint_has_type_parameter": False,
            })
            service.metadata = metadata
            service.is_active = True
            service.save()

            ServiceField.objects.update_or_create(
                service=service,
                key="account_type",
                defaults={
                    "label": "نوع الحساب",
                    "field_type": "select",
                    "required": False,
                    "default_value": target["service_type"],
                    "choices": [{"value": target["service_type"], "label": "ADSL" if target["service_type"] == "adsl" else "هاتف ثابت"}],
                    "validation": {"server_generated": True, "readonly": True},
                    "sort_order": 1,
                    "is_active": True,
                },
            )

            ServiceSetting.objects.update_or_create(
                key=target["setting_key"],
                defaults={
                    "name": target["name"],
                    "group": "yemen_net",
                    "description": target["description"],
                    "setting_type": ServiceSetting.Types.SERVICE,
                    "service": service,
                    "value": None,
                    "is_system": True,
                    "is_active": True,
                    "sort_order": 20 if target["service_type"] == "adsl" else 30,
                },
            )
            if was_created:
                created.append(target["code"])

        # Prevent the old ambiguous query Service from being selected by new clients.
        if legacy.code == "post-query":
            legacy.is_active = False
            legacy_metadata = dict(legacy.metadata or {})
            legacy_metadata["deprecated"] = True
            legacy_metadata["replacement_services"] = [t["code"] for t in TARGETS]
            legacy.metadata = legacy_metadata
            legacy.save(update_fields=["is_active", "metadata"])
            ServiceSetting.objects.filter(key="yemen_net_query").update(is_active=False)

        self.stdout.write(self.style.SUCCESS(
            "Yemen Net query repair completed. Created/updated: " + ", ".join(t["code"] for t in TARGETS)
            + (f". New: {', '.join(created)}" if created else "")
        ))
