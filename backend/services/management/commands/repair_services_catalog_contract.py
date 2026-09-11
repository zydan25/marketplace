from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from services.models import ProviderConnection, ProviderLink, Service, ServiceDistribution, ServiceField
from services.settings_models import ServiceSetting
from services.yemen_mobile_catalog_sync import sync_yemen_mobile_catalog


class Command(BaseCommand):
    help = "Repair canonical Yemen Mobile catalog and Yemen Net query service split after provisioning."

    @transaction.atomic
    def handle(self, *args, **options):
        yemen = Service.objects.filter(code="yem-offer", is_active=True).first()
        if not yemen:
            raise CommandError("الخدمة yem-offer غير موجودة. شغّل provision_services_v2 أولاً.")

        yemen.name = "باقات يمن موبايل"
        yemen.slug = "yemen-mobile-packages"
        yemen.service_kind = Service.ServiceKinds.PURCHASE
        yemen.pricing_mode = Service.PricingModes.ITEM
        yemen.requires_balance = True
        metadata = dict(yemen.metadata or {})
        metadata.update({
            "canonical_service": True,
            "catalog_enabled": True,
            "free_actions": ["Remove"],
            "provider_family": "yemen_mobile",
            "catalog_source": "api 1 (59).pdf",
            "catalog_authority": "Sanaacash API PDF",
        })
        yemen.metadata = metadata
        yemen.save(update_fields=["name", "slug", "service_kind", "pricing_mode", "requires_balance", "metadata"])

        ServiceField.objects.update_or_create(
            service=yemen,
            key="mobile",
            defaults={"label": "رقم الهاتف", "field_type": "phone", "required": True, "sort_order": 1, "is_active": True},
        )
        ServiceField.objects.update_or_create(
            service=yemen,
            key="method",
            defaults={
                "label": "العملية",
                "field_type": "select",
                "required": True,
                "choices": ["New", "Renew", "Remove"],
                "default_value": "New",
                "sort_order": 2,
                "is_active": True,
            },
        )
        ServiceField.objects.update_or_create(
            service=yemen,
            key="solfa",
            defaults={
                "label": "استخدام السلفة",
                "field_type": "select",
                "required": True,
                "choices": ["Y", "N"],
                "default_value": "N",
                "sort_order": 3,
                "is_active": True,
            },
        )

        result = sync_yemen_mobile_catalog(yemen)

        provider = ProviderConnection.objects.filter(code="sanaacash-1", is_active=True).first()
        if provider:
            link, _ = ProviderLink.objects.update_or_create(
                code="sanaacash-1-yemen_mobile_packages",
                defaults={
                    "provider": provider,
                    "name": "yemen_mobile_packages",
                    "operation": "yemen_mobile_packages",
                    "path_template": "offeryem",
                    "http_method": "GET",
                    "request_encoding": "query",
                    "fixed_params": {"action": "billoffer"},
                    "field_map": {"mobile": "mobile", "offerkey": "external_code", "method": "method", "solfa": "solfa"},
                    "success_codes": ["0"],
                    "pending_codes": ["-2"],
                    "status_path_template": "info",
                    "status_params": {"action": "status"},
                    "priority": 1,
                    "is_active": True,
                    "metadata": {"source": "api 1 (59).pdf", "canonical": True},
                },
            )
            ServiceDistribution.objects.filter(service=yemen).update(is_active=False)
            ServiceDistribution.objects.update_or_create(
                service=yemen,
                provider_link=link,
                defaults={"priority": 1, "is_active": True, "conditions": {}},
            )

        Service.objects.filter(code__in={"yem-denomination", "yem-bill-offer", "yem-offer-bill"}).update(is_active=False)

        post_query = Service.objects.filter(code="post-query").select_related("category").first()
        if post_query:
            targets = (
                ("post-query-adsl", "استعلام يمن نت ADSL", "yemen-net-adsl-query", "yemen_net_adsl_query", "adsl", 20),
                ("post-query-line", "استعلام هاتف ثابت يمن نت", "yemen-net-line-query", "yemen_net_line_query", "line", 30),
            )
            for code, name, slug, setting_key, service_type, sort_order in targets:
                service, _ = Service.objects.update_or_create(
                    code=code,
                    defaults={
                        "category": post_query.category,
                        "name": name,
                        "slug": slug,
                        "description": f"{name}. الاستعلام يستخدم /post?action=query؛ type={service_type} محفوظ محليًا لتحديد تجربة العميل.",
                        "service_kind": Service.ServiceKinds.QUERY,
                        "pricing_mode": Service.PricingModes.FIXED,
                        "requires_balance": False,
                        "currency": "YER",
                        "metadata": {
                            "canonical": True,
                            "provider_family": "yemen_post",
                            "provider_service_type": service_type,
                            "query_endpoint_has_type_parameter": False,
                        },
                        "is_active": True,
                    },
                )
                ServiceField.objects.update_or_create(
                    service=service,
                    key="account_type",
                    defaults={
                        "label": "نوع الحساب",
                        "field_type": "select",
                        "required": False,
                        "default_value": service_type,
                        "choices": [{"value": service_type, "label": "ADSL" if service_type == "adsl" else "هاتف ثابت"}],
                        "validation": {"server_generated": True, "readonly": True},
                        "sort_order": 1,
                        "is_active": True,
                    },
                )
                ServiceSetting.objects.update_or_create(
                    key=setting_key,
                    defaults={
                        "name": name,
                        "group": "yemen_net",
                        "description": service.description,
                        "setting_type": ServiceSetting.Types.SERVICE,
                        "service": service,
                        "value": None,
                        "is_system": True,
                        "is_active": True,
                        "sort_order": sort_order,
                    },
                )
            post_query.is_active = False
            legacy_meta = dict(post_query.metadata or {})
            legacy_meta.update({"deprecated": True, "replacement_services": ["post-query-adsl", "post-query-line"]})
            post_query.metadata = legacy_meta
            post_query.save(update_fields=["is_active", "metadata"])
            ServiceSetting.objects.filter(key="yemen_net_query").update(is_active=False)

        self.stdout.write(self.style.SUCCESS(
            "Catalog contract repair completed: "
            f"Yemen Mobile plans={result['created_plans']}, source rows={result['expected_source_rows']}, zero-price={result['zero_price']}. "
            "Yemen Net query split=ADSL/fixed-line."
        ))
