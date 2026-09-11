from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.text import slugify

from services.catalog_base import SERVICES
from services.catalog_yemen_contract import canonical_yemen_mobile_offer_code
from services.catalog_data import YEMEN_MOBILE_OFFERS
from services.models import (
    MainServiceCategory,
    ProviderConnection,
    ProviderLink,
    Service,
    ServiceCategory,
    ServiceDistribution,
    ServiceField,
    TelecomPlan,
    TelecomPlanType,
)
from services.settings_models import ServiceSetting


CANONICAL_SETTINGS = [
    ("yemen_mobile", "yemen_mobile_recharge", "تسديد رصيد يمن موبايل", "yem-balance"),
    ("yemen_mobile", "yemen_mobile_balance_query", "استعلام رصيد يمن موبايل", "yem-query-balance"),
    ("yemen_mobile", "yemen_mobile_offers_query", "استعلام باقات يمن موبايل", "yem-query-offers"),
    ("yemen_mobile", "yemen_mobile_packages", "باقات يمن موبايل", "yem-offer"),
    ("sabafon_north", "sabafon_recharge", "تسديد رصيد سبأفون", "saba-denomination"),
    ("sabafon_north", "sabafon_packages", "باقات سبأفون", "saba-offer"),
    ("sabafon_north", "sabafon_units", "وحدات سبأفون", "saba-units"),
    ("sabafon_south", "sabafon_south_recharge", "شحن سبأفون الجنوب", "sbay-denomination"),
    ("sabafon_south", "sabafon_south_packages", "باقات سبأفون الجنوب", "sbay-offer"),
    ("you", "you_balance", "تسديد رصيد يو", "you-balance"),
    ("you", "you_recharge", "فئات شحن يو", "you-denomination"),
    ("you", "you_packages", "باقات يو", "you-offer"),
    ("wai", "wai_bill", "تسديد واي", "why-bill"),
    ("wai", "wai_balance", "تسديد رصيد واي", "why-balance"),
    ("wai", "wai_packages", "باقات واي", "why-package"),
    ("yemen4g", "yemen4g_query", "استعلام يمن فورجي", "yem4g-query"),
    ("yemen4g", "yemen4g_balance", "تسديد رصيد يمن فورجي", "yem4g-balance"),
    ("yemen4g", "yemen4g_packages", "باقات يمن فورجي", "yem4g-package"),
    ("yemen4g", "yemen4g_change", "تغيير باقة يمن فورجي", "yem4g-change"),
    ("yemen_net", "yemen_net_query", "استعلام يمن نت", "post-query"),
    ("yemen_net", "yemen_net_adsl", "تسديد يمن نت ADSL", "post-adsl"),
    ("yemen_net", "yemen_net_line", "تسديد خط يمن نت", "post-line"),
    ("adenet", "adenet_query", "استعلام عدن نت", "adenet-query"),
    ("adenet", "adenet_bill", "تسديد عدن نت", "adenet-bill"),
    ("electricity", "electricity_query", "استعلام الكهرباء", "electric-query"),
    ("electricity", "electricity_bill", "تسديد الكهرباء", "electric-bill"),
    ("water", "water_query", "استعلام الماء", "water-query"),
    ("water", "water_bill", "تسديد الماء", "water-bill"),
]

LEGACY_YEMEN_CODES = {"yem-denomination", "yem-bill-offer", "yem-offer-bill"}


def _canonical_code(value):
    return canonical_yemen_mobile_offer_code(value)


def _main(slug, name, sort_order):
    obj, _ = MainServiceCategory.objects.update_or_create(
        slug=slug,
        defaults={"name": name, "icon": "receipt", "sort_order": sort_order, "is_active": True},
    )
    return obj


def _category(main, slug, name, sort_order):
    obj, _ = ServiceCategory.objects.update_or_create(
        main_category=main,
        parent=None,
        slug=slug,
        defaults={"name": name, "sort_order": sort_order, "is_active": True},
    )
    return obj


def _ensure_field(service, key, label, field_type="text", *, required=True, choices=None, default=None, sort_order=10):
    ServiceField.objects.update_or_create(
        service=service,
        key=key,
        defaults={
            "label": label,
            "field_type": field_type,
            "required": required,
            "choices": choices or [],
            "default_value": default,
            "sort_order": sort_order,
            "is_active": True,
        },
    )


def _ensure_service_catalog(categories):
    created = []
    for code, name, category_code, kind, pricing, _link_key, requires_balance in SERVICES:
        category = categories.get(category_code)
        if category is None:
            continue
        service, was_created = Service.objects.get_or_create(
            code=code,
            defaults={
                "category": category,
                "name": name,
                "slug": slugify(name, allow_unicode=True),
                "description": name,
                "service_kind": kind,
                "pricing_mode": pricing,
                "requires_balance": bool(requires_balance),
                "currency": "YER",
                "metadata": {"provisioned_by": "provision_services_v2"},
                "is_active": True,
            },
        )
        updates = []
        if service.category_id != category.id:
            service.category = category
            updates.append("category")
        if not service.name:
            service.name = name
            updates.append("name")
        if not service.slug:
            service.slug = slugify(name, allow_unicode=True)
            updates.append("slug")
        if service.service_kind != kind:
            service.service_kind = kind
            updates.append("service_kind")
        if service.pricing_mode != pricing:
            service.pricing_mode = pricing
            updates.append("pricing_mode")
        if service.requires_balance != bool(requires_balance):
            service.requires_balance = bool(requires_balance)
            updates.append("requires_balance")
        if not service.is_active:
            service.is_active = True
            updates.append("is_active")
        if updates:
            # Service has no updated_at field; save only concrete fields that changed.
            service.save(update_fields=updates)
        if was_created:
            created.append(code)
    return created


def _ensure_link(provider, code, *, path, field_map, fixed_params=None):
    link, _ = ProviderLink.objects.update_or_create(
        code=f"{provider.code}-{code}",
        defaults={
            "provider": provider,
            "name": code,
            "operation": code,
            "path_template": path,
            "http_method": "GET",
            "request_encoding": "query",
            "fixed_params": fixed_params or {},
            "field_map": field_map,
            "success_codes": ["0"],
            "pending_codes": ["-2"],
            "status_path_template": "info",
            "status_params": {"action": "status"},
            "priority": 100,
            "is_active": True,
            "metadata": {"source": "api 1 (59).pdf", "canonical": True},
        },
    )
    return link


def _attach(service, link, priority=100):
    ServiceDistribution.objects.update_or_create(
        service=service,
        provider_link=link,
        defaults={"priority": priority, "is_active": True, "conditions": {}},
    )


def _merge_yemen_mobile_plans(target):
    source_codes = {"yem-offer", "yem-bill-offer", "yem-offer-bill"}
    rows = list(
        TelecomPlan.objects.filter(service__code__in=source_codes)
        .select_related("service")
        .order_by("service__code", "id")
    )
    for row in rows:
        code = _canonical_code(row.external_code)
        existing = TelecomPlan.objects.filter(service=target, external_code=code).first()
        metadata = dict(row.metadata or {})
        metadata["provider_offer_code"] = code
        metadata["canonical_service"] = "yem-offer"
        data = {
            "name": row.name,
            "price": row.price,
            "quota": row.quota,
            "quota_unit": row.quota_unit,
            "validity_days": row.validity_days,
            "payment_type": row.payment_type,
            "line_type": row.line_type,
            "metadata": metadata,
            "sort_order": row.sort_order,
            "is_active": row.is_active,
        }
        if existing is None:
            TelecomPlan.objects.create(service=target, external_code=code, **data)
        else:
            for key, value in data.items():
                setattr(existing, key, value)
            existing.save()
    Service.objects.filter(code__in=LEGACY_YEMEN_CODES).update(is_active=False)


def _seed_yemen_mobile_catalog(service):
    for index, (code, price, name, payment_type, line_type) in enumerate(YEMEN_MOBILE_OFFERS):
        code = _canonical_code(code)
        TelecomPlan.objects.update_or_create(
            service=service,
            external_code=code,
            defaults={
                "name": name,
                "price": Decimal(str(price)),
                "payment_type": payment_type,
                "line_type": line_type,
                "sort_order": index,
                "is_active": True,
                "metadata": {
                    "provider_offer_code": code,
                    "catalog_source": "api 1 (59).pdf",
                    "canonical_service": "yem-offer",
                    "purchaseable": True,
                    "provider_operation": "offeryem",
                },
            },
        )

    roots = {}
    for code, name in [("3g", "باقات 3G"), ("4g", "باقات 4G"), ("other", "باقات أخرى")]:
        roots[code], _ = TelecomPlanType.objects.update_or_create(
            service=service,
            code=code,
            defaults={"name": name, "description": "تصنيف رئيسي للباقات", "parent": None, "is_active": True},
        )
        roots[code].plans.clear()

    plans = TelecomPlan.objects.filter(service=service, is_active=True)
    groups = {"3g": [], "4g": [], "other": []}
    for plan in plans:
        text = (plan.name or "").lower()
        if "4g" in text or "فورجي" in text:
            groups["4g"].append(plan)
        elif "3g" in text or "3(g)" in text:
            groups["3g"].append(plan)
        else:
            groups["other"].append(plan)
    for key, items in groups.items():
        roots[key].plans.add(*items)


def _settings_from_services():
    for group, key, name, code in CANONICAL_SETTINGS:
        service = Service.objects.filter(code=code, is_active=True).first()
        ServiceSetting.objects.update_or_create(
            key=key,
            defaults={
                "name": name,
                "group": group,
                "description": f"الخدمة الثابتة التي يستخدمها تطبيق العميل لـ{name}.",
                "setting_type": ServiceSetting.Types.SERVICE,
                "service": service,
                "value": None,
                "is_system": True,
                "is_active": True,
                "sort_order": 10,
            },
        )

    candidates = ["yem-query-loan", "yem-query-solfa", "yem-solfa-query"]
    loan_service = Service.objects.filter(code__in=candidates, is_active=True).first()
    ServiceSetting.objects.update_or_create(
        key="yemen_mobile_loan_query",
        defaults={
            "name": "استعلام سلفة يمن موبايل",
            "group": "yemen_mobile",
            "description": "إعداد سلفة يمن موبايل؛ يربط تلقائيًا إذا كانت خدمة السلفة موجودة في قاعدة النظام.",
            "setting_type": ServiceSetting.Types.SERVICE,
            "service": loan_service,
            "value": None,
            "is_system": True,
            "is_active": True,
            "sort_order": 40,
        },
    )

    game_services = Service.objects.filter(category__main_category__slug__in=["games", "software"], is_active=True).select_related("category")
    for service in game_services:
        group = "games" if service.category.main_category.slug == "games" else "digital_cards"
        ServiceSetting.objects.update_or_create(
            key=f"{group}_{service.code}",
            defaults={
                "name": service.name,
                "group": group,
                "description": "خدمة ثابتة يرسل فيها type = service.code ضمن عقد الألعاب والبطاقات.",
                "setting_type": ServiceSetting.Types.SERVICE,
                "service": service,
                "is_system": True,
                "is_active": True,
                "sort_order": 100,
            },
        )
    ServiceSetting.objects.filter(is_system=True, service__is_active=False).update(is_active=False)


def provision(*, provider_code="sanaacash-1", provider_name="صنعاء كاش - الربطية الأولى", base_url="https://sanaacash.yrbso.net/api/yr/"):
    payments = _main("payments", "التسديدات", 10)
    games = _main("games", "الألعاب", 20)
    digital = _main("software", "البرامج والبطاقات", 30)
    categories = {
        "yemen-mobile": _category(payments, "yemen-mobile", "يمن موبايل", 10),
        "sabafon": _category(payments, "sabafon", "سبأفون", 20),
        "you": _category(payments, "you", "يو", 30),
        "why": _category(payments, "why", "واي", 40),
        "yemen-4g": _category(payments, "yemen-4g", "يمن فورجي", 50),
        "yemen-net": _category(payments, "yemen-net", "يمن نت", 60),
        "adenet": _category(payments, "adenet", "عدن نت", 70),
        "electricity": _category(payments, "electricity", "الكهرباء", 80),
        "water": _category(payments, "water", "الماء", 90),
    }

    for key, name in [
        ("games", "الألعاب"),
        ("software", "البرامج والبطاقات"),
        ("telecom", "الاتصالات"),
    ]:
        main = games if key == "games" else digital if key == "software" else payments
        categories[f"{key}-root"] = _category(main, key, name, 100 + len(categories))

    with transaction.atomic():
        _ensure_service_catalog(categories)
        canonical = Service.objects.get(code="yem-offer")
        canonical.name = "باقات يمن موبايل"
        canonical.slug = "yemen-mobile-packages"
        canonical.service_kind = Service.ServiceKinds.PURCHASE
        canonical.pricing_mode = Service.PricingModes.ITEM
        canonical.requires_balance = True
        metadata = dict(canonical.metadata or {})
        metadata.update({
            "canonical_service": True,
            "catalog_enabled": True,
            "free_actions": ["Remove"],
            "provider_family": "yemen_mobile",
        })
        canonical.metadata = metadata
        canonical.save(update_fields=["name", "slug", "service_kind", "pricing_mode", "requires_balance", "metadata"])

        _merge_yemen_mobile_plans(canonical)
        _seed_yemen_mobile_catalog(canonical)

        for key, service_code, path, field_map, fixed in [
            ("yemen_mobile_packages", "yem-offer", "offeryem", {"mobile": "mobile", "offerkey": "external_code", "method": "method", "solfa": "solfa"}, {"action": "billoffer"}),
        ]:
            provider, _ = ProviderConnection.objects.update_or_create(
                code=provider_code,
                defaults={
                    "name": provider_name,
                    "connection_type": ProviderConnection.Types.SANAACASH,
                    "base_url": base_url,
                    "is_active": True,
                },
            )
            link = _ensure_link(provider, key, path=path, field_map=field_map, fixed_params=fixed)
            _attach(Service.objects.get(code=service_code), link)

        _settings_from_services()

    return True


class Command(BaseCommand):
    help = "Provision canonical Services V2 catalog, package services, provider links and settings."

    def add_arguments(self, parser):
        parser.add_argument("--provider-code", default="sanaacash-1")
        parser.add_argument("--provider-name", default="صنعاء كاش - الربطية الأولى")
        parser.add_argument("--base-url", default="https://sanaacash.yrbso.net/api/yr/")

    def handle(self, *args, **options):
        result = provision(
            provider_code=options["provider_code"],
            provider_name=options["provider_name"],
            base_url=options["base_url"],
        )
        if result:
            self.stdout.write(self.style.SUCCESS("Services V2 provisioning completed successfully."))
