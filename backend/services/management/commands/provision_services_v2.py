from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.text import slugify

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
from services.catalog_data import YEMEN_MOBILE_OFFERS
from services.catalog_yemen_contract import canonical_yemen_mobile_offer_code
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
        "games": _category(games, "games", "الألعاب", 10),
        "digital-cards": _category(digital, "digital-cards", "البطاقات الرقمية", 10),
    }

    provider, _ = ProviderConnection.objects.update_or_create(
        code=provider_code,
        defaults={
            "name": provider_name,
            "connection_type": ProviderConnection.Types.SANAACASH,
            "base_url": base_url,
            "is_active": True,
        },
    )

    with transaction.atomic():
        yem_package = Service.objects.get(code="yem-offer")
        yem_package.category = categories["yemen-mobile"]
        yem_package.name = "باقات يمن موبايل"
        yem_package.slug = "yemen-mobile-packages"
        yem_package.service_kind = Service.ServiceKinds.PURCHASE
        yem_package.pricing_mode = Service.PricingModes.ITEM
        yem_package.requires_balance = True
        yem_package.description = "خدمة واحدة لعرض باقات يمن موبايل وتنفيذ التفعيل أو التجديد أو الحذف وفق عقد المزود."
        metadata = dict(yem_package.metadata or {})
        metadata.update({"canonical_service": True, "catalog_enabled": True, "free_actions": ["Remove"], "provider_family": "yemen_mobile"})
        yem_package.metadata = metadata
        yem_package.is_active = True
        yem_package.save()
        _ensure_field(yem_package, "mobile", "رقم يمن موبايل", required=True, sort_order=10)
        _ensure_field(yem_package, "method", "طريقة العملية", "select", required=True, choices=["New", "Renew", "Remove"], sort_order=20)
        _ensure_field(yem_package, "solfa", "استخدام السلفة", "select", required=True, choices=["Y", "N"], default="N", sort_order=30)
        _merge_yemen_mobile_plans(yem_package)
        _seed_yemen_mobile_catalog(yem_package)

        combined_link = _ensure_link(
            provider,
            "yem_offer_combined",
            path="offeryem",
            fixed_params={"action": "billoffer"},
            field_map={"mobile": "mobile", "offerkey": "external_code", "method": "method", "solfa": "solfa"},
        )
        ServiceDistribution.objects.filter(service=yem_package).update(is_active=False)
        _attach(yem_package, combined_link)

        readable = {
            "yem-balance": "تسديد رصيد يمن موبايل",
            "yem-query-balance": "استعلام رصيد يمن موبايل",
            "yem-query-offers": "استعلام باقات يمن موبايل",
            "saba-denomination": "تسديد رصيد سبأفون",
            "saba-offer": "باقات سبأفون",
            "sbay-denomination": "شحن سبأفون الجنوب",
            "sbay-offer": "باقات سبأفون الجنوب",
            "you-balance": "تسديد رصيد يو",
            "you-denomination": "فئات شحن يو",
            "you-offer": "باقات يو",
            "why-bill": "تسديد واي",
            "why-balance": "تسديد رصيد واي",
            "why-package": "باقات واي",
            "yem4g-query": "استعلام يمن فورجي",
            "yem4g-balance": "تسديد رصيد يمن فورجي",
            "yem4g-package": "باقات يمن فورجي",
            "yem4g-change": "تغيير باقة يمن فورجي",
            "post-query": "استعلام يمن نت",
            "post-adsl": "تسديد يمن نت ADSL",
            "post-line": "تسديد خط يمن نت",
            "adenet-query": "استعلام عدن نت",
            "adenet-bill": "تسديد عدن نت",
            "electric-query": "استعلام الكهرباء",
            "electric-bill": "تسديد الكهرباء",
            "water-query": "استعلام الماء",
            "water-bill": "تسديد الماء",
        }
        category_by_code = {
            "yem-balance": "yemen-mobile", "yem-query-balance": "yemen-mobile", "yem-query-offers": "yemen-mobile",
            "saba-denomination": "sabafon", "saba-offer": "sabafon", "sbay-denomination": "sabafon", "sbay-offer": "sabafon",
            "you-balance": "you", "you-denomination": "you", "you-offer": "you", "why-bill": "why", "why-balance": "why", "why-package": "why",
            "yem4g-query": "yemen-4g", "yem4g-balance": "yemen-4g", "yem4g-package": "yemen-4g", "yem4g-change": "yemen-4g",
            "post-query": "yemen-net", "post-adsl": "yemen-net", "post-line": "yemen-net", "adenet-query": "adenet", "adenet-bill": "adenet",
            "electric-query": "electricity", "electric-bill": "electricity", "water-query": "water", "water-bill": "water",
        }
        for code, name in readable.items():
            service = Service.objects.filter(code=code).first()
            if not service:
                continue
            service.name = name
            if code in category_by_code:
                service.category = categories[category_by_code[code]]
            service.is_active = True
            service.save()

        Service.objects.filter(code__in=LEGACY_YEMEN_CODES).update(is_active=False)
        _settings_from_services()

    return {
        "provider": provider.code,
        "yemen_mobile_packages": yem_package.code,
        "settings": ServiceSetting.objects.filter(is_system=True, is_active=True).count(),
        "yemen_mobile_plans": TelecomPlan.objects.filter(service=yem_package, is_active=True).count(),
    }


class Command(BaseCommand):
    help = "تهيئة منصة الخدمات v2: خدمات ثابتة، خدمة باقات واحدة لكل شبكة، كتالوج وأنواع باقات وإعدادات التطبيق."

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
        self.stdout.write(self.style.SUCCESS("تم تجهيز خدمات v2 بنجاح."))
        for key, value in result.items():
            self.stdout.write(f"{key}: {value}")
