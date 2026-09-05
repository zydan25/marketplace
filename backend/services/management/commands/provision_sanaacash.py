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
    ServiceOption,
    TelecomDenomination,
    TelecomPlan,
)
from services.provider import DEFAULT_WEBHOOK_PATH
from services.catalog_data import CATEGORIES, LINKS, MAIN, SABA_DENOMINATIONS, SABA_OFFERS, SBAY_TABLE, SERVICES, ADENET_TABLE, WHY_TABLE, YOU_DENOMINATIONS, YOU_OFFERS, YEMEN_MOBILE_OFFERS


MOBILE_9 = {"yem-balance", "yem-denomination", "yem-offer", "yem-bill-offer", "yem-offer-bill", "yem-query-balance", "yem-query-offers", "saba-denomination", "saba-offer", "sbay-offer", "sbay-denomination", "saba-units", "you-balance", "you-denomination", "you-offer", "yem4g-package", "yem4g-balance", "yem4g-change", "games_cards"}
MOBILE_8 = {"why-bill", "why-balance", "why-package", "post-adsl", "post-line", "post-query"}


def _ensure_main_category(key, values):
    name, slug, icon = values
    obj = MainServiceCategory.objects.filter(slug=slug).first() or MainServiceCategory.objects.filter(name=name).first()
    if obj is None:
        return MainServiceCategory.objects.create(name=name, slug=slug, icon=icon, is_active=True)
    changed = False
    for attr, value in (("name", name), ("slug", slug), ("icon", icon), ("is_active", True)):
        if getattr(obj, attr) != value:
            setattr(obj, attr, value)
            changed = True
    if changed:
        obj.save(update_fields=["name", "slug", "icon", "is_active"])
    return obj


def ensure_field(service, key, label, field_type="text", required=True, *, choices=None, validation=None, default=None, secret=False, sort_order=10):
    ServiceField.objects.update_or_create(
        service=service,
        key=key,
        defaults={
            "label": label,
            "field_type": field_type,
            "required": required,
            "secret": secret,
            "choices": choices or [],
            "validation": validation or {},
            "default_value": default,
            "sort_order": sort_order,
            "is_active": True,
        },
    )


def _service_fields(service, code, link_key):
    if code in MOBILE_9:
        ensure_field(service, "mobile", "رقم الهاتف/المستفيد", validation={"min_length": 9, "max_length": 9})
    elif code in MOBILE_8:
        ensure_field(service, "mobile", "رقم الهاتف/الاشتراك", validation={"min_length": 8, "max_length": 8})
    else:
        ensure_field(service, "mobile", "رقم الهاتف", required=False)

    amount_services = {"yem-balance", "saba-units", "you-balance", "why-balance", "yem4g-balance", "post-adsl", "post-line", "saba-gomla", "mtn-gomla", "mobile-gomla", "electric-bill", "water-bill"}
    if code in amount_services:
        ensure_field(service, "amount", "المبلغ", "decimal", True, validation={"min": "0.01"}, sort_order=20)

    if service.pricing_mode == Service.PricingModes.ITEM:
        ensure_field(service, "external_code", "كود الباقة/المنتج لدى المزود", required=False, sort_order=80)

    if code in {"yem-bill-offer", "yem-offer-bill"}:
        ensure_field(service, "method", "طريقة الباقة", "select", True, choices=["New", "Renew", "Remove"], sort_order=20)
    if code == "yem-offer-bill":
        ensure_field(service, "solfa", "سلفة", "select", True, choices=["Y", "N"], default="N", sort_order=30)
    if code in {"you-balance", "you-denomination"}:
        ensure_field(service, "type", "نوع الخط", "select", True, choices=["prepaid", "postpaid"], default="prepaid", sort_order=30)
    if code in {"you-denomination", "you-offer", "saba-denomination", "saba-offer", "sbay-offer", "sbay-denomination", "adenet-bill", "adenet-query", "why-bill", "why-package"}:
        ensure_field(service, "num", "رقم/فئة المزود", "text", True, sort_order=20)
    if code == "why-balance":
        ensure_field(service, "num", "الكمية/الفئة", "text", True, sort_order=30)
    if code == "why-package":
        ensure_field(service, "packageid", "رقم الباقة", "text", True, sort_order=30)
    if code in {"electric-query", "electric-bill", "water-query", "water-bill"}:
        ensure_field(service, "customer_id", "رقم المشترك للعداد", required=True, sort_order=20)
        ensure_field(service, "placeid", "رقم المنطقة", required=True, sort_order=30)
    if link_key == "games_cards":
        ensure_field(service, "uniqcode", "كود الفئة الموحد", required=True, sort_order=20)
        ensure_field(service, "playerid", "رقم اللاعب", required=True, sort_order=30)
        ensure_field(service, "playername", "اسم اللاعب", required=False, sort_order=40)
        ensure_field(service, "zoneid", "Zone ID", required=False, sort_order=50)
        ensure_field(service, "email", "البريد الإلكتروني", "email", required=False, sort_order=60)
    if link_key in {"yem4g_package", "yem4g_change"}:
        ensure_field(service, "amount", "قيمة العملية", "decimal", True, validation={"min": "0.01"}, sort_order=20)
    if code == "yem4g-query":
        ensure_field(service, "mobile", "رقم يمن فورجي", validation={"min_length": 9, "max_length": 9})
    if code in {"why-package", "adenet-bill"}:
        ensure_field(service, "external_code", "كود المنتج/الباقة", required=False, sort_order=40)


def _set_service_request_schema(service, code, kind):
    service.request_schema = {
        "type": "object",
        "service_code": code,
        "fields": [f.key for f in service.fields.filter(is_active=True).order_by("sort_order", "id")],
        "async": True,
    }
    service.response_schema = {
        "resultCode": "string",
        "resultDesc": "string",
        "provider_response": "object",
    }
    if kind in {"query", "catalog"}:
        service.metadata = {**service.metadata, "no_wallet_charge": True}
    service.save(update_fields=["request_schema", "response_schema", "metadata", "updated_at"])


def provision():
    mains = {key: _ensure_main_category(key, values) for key, values in MAIN.items()}
    categories = {}
    for main_key, name, slug in CATEGORIES:
        category, _ = ServiceCategory.objects.update_or_create(
            main_category=mains[main_key],
            parent=None,
            slug=slug,
            defaults={"name": name, "is_active": True},
        )
        categories[slug] = category

    services = {}
    for code, name, category_slug, kind, pricing, link_key, requires_balance in SERVICES:
        service, _ = Service.objects.update_or_create(
            code=code,
            defaults={
                "category": categories[category_slug],
                "name": name,
                "slug": slugify(code, allow_unicode=True),
                "description": f"عقد API Sanaacash: {link_key}",
                "service_kind": kind,
                "requires_balance": requires_balance,
                "pricing_mode": pricing,
                "price": Decimal("0.00"),
                "min_amount": Decimal("200") if code == "you-balance" else None,
                "max_amount": Decimal("100000") if code == "you-balance" else None,
                "currency": "YER",
                "is_active": True,
            },
        )
        services[code] = service
        _service_fields(service, code, link_key)
        _set_service_request_schema(service, code, kind)

    return mains, categories, services


def provision_links(connection, services):
    links = {}
    for code, (name, path, method, encoding, fixed_params, field_map, status_path, status_params) in LINKS.items():
        link, _ = ProviderLink.objects.update_or_create(
            code=f"{connection.code}-{code}",
            defaults={
                "provider": connection,
                "name": name,
                "operation": code,
                "path_template": path,
                "http_method": method,
                "request_encoding": encoding,
                "fixed_params": fixed_params,
                "field_map": field_map,
                "success_codes": ["0"],
                "pending_codes": ["-2"],
                "status_path_template": status_path,
                "status_params": status_params,
                "priority": 100,
                "is_active": True,
                "metadata": {"source": "api 1 (59).pdf", "webhook_path": DEFAULT_WEBHOOK_PATH},
            },
        )
        links[code] = link
    for code, _, _, _, _, link_key, _ in SERVICES:
        ServiceDistribution.objects.update_or_create(
            service=services[code],
            provider_link=links[link_key],
            defaults={"priority": 100, "is_active": True, "conditions": {}},
        )
    return links


def _upsert_plan(service, *, external_code, name, price, provider_num="", payment_type="", line_type="", metadata=None):
    TelecomPlan.objects.update_or_create(
        service=service,
        external_code=external_code,
        defaults={
            "name": name,
            "price": Decimal(str(price)),
            "payment_type": payment_type,
            "line_type": line_type,
            "metadata": {"provider_num": str(provider_num), **(metadata or {})},
            "is_active": True,
        },
    )


def _upsert_denom(service, *, external_code, name, face_value, sale_price, metadata=None):
    TelecomDenomination.objects.update_or_create(
        service=service,
        external_code=str(external_code),
        defaults={
            "name": name,
            "face_value": Decimal(str(face_value)),
            "sale_price": Decimal(str(sale_price)),
            "metadata": {"provider_num": str(external_code), **(metadata or {})},
            "is_active": True,
        },
    )


def _upsert_option(service, *, name, external_code="", provider_num="", price=0, metadata=None):
    ServiceOption.objects.update_or_create(
        service=service,
        external_code=str(external_code),
        provider_num=str(provider_num),
        name=name,
        defaults={
            "price": Decimal(str(price)),
            "currency": "YER",
            "metadata": metadata or {},
            "is_active": True,
        },
    )


def seed_catalog(services):
    bill_offer = services["yem-bill-offer"]
    combined_offer = services["yem-offer-bill"]
    catalog_offer = services["yem-offer"]
    for code, price, name, payment_type, line_type in YEMEN_MOBILE_OFFERS:
        metadata = {"provider_offer_code": code, "catalog_source": "api 1 (59).pdf"}
        _upsert_plan(bill_offer, external_code=code, name=name, price=price, payment_type=payment_type, line_type=line_type, metadata=metadata)
        _upsert_plan(combined_offer, external_code=code, name=name, price=price, payment_type=payment_type, line_type=line_type, metadata=metadata)
        _upsert_plan(catalog_offer, external_code=code, name=name, price=0, payment_type=payment_type, line_type=line_type, metadata={**metadata, "catalog_only": True, "requires_balance": False})

    for number, face, sale in YOU_DENOMINATIONS:
        _upsert_denom(services["you-denomination"], external_code=number, name=f"فئة يو {number}", face_value=face, sale_price=sale)
    for num, name, price, code, free_item, pay_type in YOU_OFFERS:
        _upsert_plan(services["you-offer"], external_code=code or num, name=name, price=price, provider_num=num, payment_type=pay_type, metadata={"requires_balance": not free_item, "catalog_number": num})

    for number, face, sale in SABA_DENOMINATIONS:
        _upsert_denom(services["saba-denomination"], external_code=number, name=f"فئة سبأفون {number}", face_value=face, sale_price=sale)
    for num, name, price, code in SABA_OFFERS:
        _upsert_plan(services["saba-offer"], external_code=code, name=name, price=price, provider_num=num)

    # The PDF explicitly says these numbering tables are provided separately.
    for row in SBAY_TABLE:
        _upsert_option(services["sbay-offer"], name=str(row[1] if len(row) > 1 else row[0]), provider_num=str(row[0]))
    for row in ADENET_TABLE:
        _upsert_option(services["adenet-bill"], name=str(row[1] if len(row) > 1 else row[0]), provider_num=str(row[0]))
    for row in WHY_TABLE:
        _upsert_option(services["why-package"], name=str(row[1] if len(row) > 1 else row[0]), provider_num=str(row[0]))


def create_or_update_sanaacash_provider(*, code, name, userid="", domain_name="", username="", password="", note="", base_url="https://sanaacash.yrbso.net/api/yr/"):
    provider, _ = ProviderConnection.objects.update_or_create(
        code=code,
        defaults={
            "name": name,
            "connection_type": ProviderConnection.Types.SANAACASH,
            "base_url": base_url,
            "userid": userid,
            "domain_name": domain_name,
            "username": username,
            "is_active": True,
        },
    )
    metadata = dict(provider.metadata or {})
    metadata.update({"note": note.strip(), "contract_source": "api 1 (59).pdf"})
    provider.metadata = metadata
    if password:
        provider.set_password(password)
    fields = ["base_url", "userid", "domain_name", "username", "metadata", "is_active", "updated_at"]
    if password:
        fields.append("password_encrypted")
    provider.save(update_fields=fields)
    _, _, services = provision()
    provision_links(provider, services)
    seed_catalog(services)
    return provider


class Command(BaseCommand):
    help = "تهيئة عقد الخدمات الكامل من ملف Sanaacash API والكتالوجات المتوفرة فيه."

    def add_arguments(self, parser):
        parser.add_argument("--provider-code", default="sanaacash-1")
        parser.add_argument("--provider-name", default="صنعاء كاش - الربطية الأولى")
        parser.add_argument("--base-url", default="https://sanaacash.yrbso.net/api/yr/")
        parser.add_argument("--userid", default="")
        parser.add_argument("--domain-name", default="")
        parser.add_argument("--username", default="")
        parser.add_argument("--password", default="")
        parser.add_argument("--dry-run", action="store_true")

    @transaction.atomic
    def handle(self, *args, **options):
        if options["dry_run"]:
            self.stdout.write(self.style.WARNING(f"Dry run: {len(MAIN)} فئات رئيسية، {len(CATEGORIES)} فئات، {len(SERVICES)} خدمة، {len(LINKS)} مسار API."))
            return
        provider = create_or_update_sanaacash_provider(
            code=options["provider_code"],
            name=options["provider_name"],
            userid=options["userid"],
            domain_name=options["domain_name"],
            username=options["username"],
            password=options["password"],
            base_url=options["base_url"],
        )
        count_plans = TelecomPlan.objects.count()
        count_denoms = TelecomDenomination.objects.count()
        self.stdout.write(self.style.SUCCESS(f"تمت تهيئة {provider.name}: {len(SERVICES)} خدمة و{len(LINKS)} مسار، مع {count_plans} باقة و{count_denoms} فئة في الكتالوج."))
