from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.text import slugify

from services.models import MainServiceCategory, ProviderConnection, ProviderLink, Service, ServiceCategory, ServiceDistribution, ServiceField


MAIN = {
    "payments": ("التسديدات", "التسديدات"),
    "games": ("الألعاب", "الألعاب"),
    "digital": ("البرامج والبطاقات", "البرامج-والبطاقات"),
}

CATEGORIES = [
    ("payments", "يمن موبايل", "yemen-mobile"),
    ("payments", "سبأفون", "sabafon"),
    ("payments", "يو", "you"),
    ("payments", "واي", "why"),
    ("payments", "يمن فورجي", "yemen-4g"),
    ("payments", "يمن نت", "yemen-net"),
    ("payments", "عدن نت", "adenet"),
    ("payments", "الكهرباء", "electricity"),
    ("payments", "الماء", "water"),
    ("payments", "الخدمات الجماعية", "wholesale"),
    ("games", "الألعاب", "games"),
    ("digital", "البطاقات الرقمية", "digital-cards"),
]

SERVICES = [
    ("yemen-mobile", "Yemen Mobile - رصيد", "yem-balance", "amount", "yem_bill_balance"),
    ("yemen-mobile", "Yemen Mobile - فئات", "yem-denomination", "item", "yem_denomination"),
    ("yemen-mobile", "Yemen Mobile - باقات", "yem-offer", "item", "yem_offer"),
    ("yemen-mobile", "Yemen Mobile - تفعيل باقة", "yem-bill-offer", "item", "yem_bill_offer"),
    ("yemen-mobile", "Yemen Mobile - تسديد وتفعيل", "yem-offer-bill", "item", "yem_offer_bill"),
    ("sabafon", "سبأفون - فئات", "saba-denomination", "item", "saba_denomination"),
    ("sabafon", "سبأفون - باقات", "saba-offer", "item", "saba_offer"),
    ("sabafon", "سبأفون الجنوب - باقات", "sbay-offer", "item", "sbay_offer"),
    ("sabafon", "سبأفون الجنوب - شحن", "sbay-denomination", "item", "sbay_denominations"),
    ("sabafon", "سبأفون - وحدات", "saba-units", "amount", "saba_units"),
    ("you", "يو - رصيد مفتوح", "you-balance", "amount", "you_balance"),
    ("you", "يو - فئات شحن", "you-denomination", "item", "you_denominations"),
    ("you", "يو - باقات", "you-offer", "item", "you_offer"),
    ("why", "واي - تسديد", "why-bill", "amount", "why_bill"),
    ("why", "واي - رصيد", "why-balance", "amount", "why_balance"),
    ("why", "واي - باقات", "why-package", "item", "why_package"),
    ("yemen-4g", "يمن فورجي - باقة", "yem4g-package", "item", "yem4g_bill"),
    ("yemen-4g", "يمن فورجي - رصيد", "yem4g-balance", "amount", "yem4g_bill"),
    ("yemen-4g", "يمن فورجي - تغيير باقة", "yem4g-change", "item", "yem4g_bill"),
    ("yemen-4g", "يمن فورجي - استعلام", "yem4g-query", "amount", "yem4g_query"),
    ("yemen-net", "يمن نت - ADSL", "post-adsl", "amount", "post_bill_adsl"),
    ("yemen-net", "يمن نت - خط", "post-line", "amount", "post_bill_line"),
    ("yemen-net", "يمن نت - استعلام", "post-query", "amount", "post_query"),
    ("adenet", "عدن نت - تسديد", "adenet-bill", "item", "adenet_bill"),
    ("adenet", "عدن نت - استعلام", "adenet-query", "item", "adenet_query"),
    ("electricity", "الكهرباء - استعلام", "electric-query", "item", "electric_query"),
    ("electricity", "الكهرباء - تسديد", "electric-bill", "item", "electric_bill"),
    ("water", "الماء - استعلام", "water-query", "item", "water_query"),
    ("water", "الماء - تسديد", "water-bill", "item", "water_bill"),
    ("wholesale", "سبأفون جملة", "saba-gomla", "amount", "saba_gomla"),
    ("wholesale", "MTN جملة", "mtn-gomla", "amount", "mtn_gomla"),
    ("wholesale", "يمن موبايل جملة", "mobile-gomla", "amount", "mobile_gomla"),
    ("games", "بوبجي PUBG Mobile", "pubg", "item", "games_cards"),
    ("games", "فري فاير Free Fire", "freefire", "item", "games_cards"),
    ("games", "Mobile Legends", "legends", "item", "games_cards"),
    ("games", "Lord's Mobile", "loardstelmble", "item", "games_cards"),
    ("games", "Clash Royale", "clashroial", "item", "games_cards"),
    ("games", "Genshin Impact", "genshmbacket", "item", "games_cards"),
    ("games", "Clash of Clans", "clashofclanz", "item", "games_cards"),
    ("games", "PUBG New State", "newstatepobg", "item", "games_cards"),
    ("games", "Brawl Stars", "praolstars", "item", "games_cards"),
    ("games", "Hay Day جواهر", "hidadijwaher", "item", "games_cards"),
    ("games", "Hay Day عملة ذهبية", "ddihadi", "item", "games_cards"),
    ("games", "Call of Duty", "calloffdyoty", "item", "games_cards"),
    ("games", "Boom Beach", "pompitch", "item", "games_cards"),
    ("digital-cards", "Google Play أمريكي", "googleplayusa", "item", "games_cards"),
    ("digital-cards", "Google Play كوري", "googleplaykorea", "item", "games_cards"),
    ("digital-cards", "Apple Store Gift", "appstore", "item", "games_cards"),
    ("digital-cards", "beIN Connect", "beinconnect", "item", "games_cards"),
    ("digital-cards", "Razer Gold", "razergold", "item", "games_cards"),
    ("digital-cards", "CrossFire", "crossfire", "item", "games_cards"),
    ("digital-cards", "PlayStation أمريكي", "plastationusa", "item", "games_cards"),
    ("digital-cards", "PlayStation سعودي", "plastationsar", "item", "games_cards"),
    ("digital-cards", "Visa Card", "visacard", "item", "games_cards"),
    ("digital-cards", "MasterCard", "mastercard", "item", "games_cards"),
    ("digital-cards", "Likee", "likee", "item", "games_cards"),
    ("digital-cards", "BIGO LIVE", "bigolive", "item", "games_cards"),
]

LINKS = {
    "yem_query": ("Yemen Mobile - Query", "yem?action=query", {"action": "query"}, {"mobile": "mobile"}),
    "yem_bill_balance": ("Yemen Mobile - Bill Balance", "yem?action=bill", {"action": "bill"}, {"mobile": "mobile", "amount": "amount"}),
    "yem_offer_query": ("Yemen Mobile - Query Offers", "yem?action=queryoffer", {"action": "queryoffer"}, {"mobile": "mobile"}),
    "yem_bill_offer": ("Yemen Mobile - Bill Offer", "yem?action=billoffer", {"action": "billoffer"}, {"mobile": "mobile", "offerid": "external_code", "method": "method"}),
    "yem_offer_bill": ("Yemen Mobile - Bill Offer Combined", "offeryem?action=billoffer", {"action": "billoffer"}, {"mobile": "mobile", "offerkey": "external_code", "method": "method", "solfa": "solfa"}),
    "post_bill_adsl": ("Yemen Post - ADSL", "post?action=bill", {"action": "bill", "type": "adsl"}, {"mobile": "mobile", "amount": "amount"}),
    "post_bill_line": ("Yemen Post - Line", "post?action=bill", {"action": "bill", "type": "line"}, {"mobile": "mobile", "amount": "amount"}),
    "post_query": ("Yemen Post - Query", "post?action=query", {"action": "query"}, {"mobile": "mobile"}),
    "why_bill": ("Why - Bill", "why?action=bill", {"action": "bill"}, {"mobile": "mobile", "num": "num"}),
    "why_balance": ("Why - Balance", "why?action=bill", {"action": "bill"}, {"mobile": "mobile", "num": "num", "rasid": "amount"}),
    "why_package": ("Why - Package", "why?action=bill", {"action": "bill"}, {"mobile": "mobile", "num": "num", "packageid": "external_code"}),
    "you_balance": ("You - Balance", "mtn?action=bill", {"action": "bill", "israsid": "1"}, {"mobile": "mobile", "num": "amount", "type": "type"}),
    "you_denominations": ("You - Denominations", "mtn?action=bill", {"action": "bill"}, {"mobile": "mobile", "num": "external_code", "type": "type"}),
    "you_offer": ("You - Offer", "mtnoffer", {}, {"mobile": "mobile", "num": "external_code"}),
    "saba_denomination": ("Sabafon - Denomination", "sabaphone?action=bill", {"action": "bill"}, {"mobile": "mobile", "num": "external_code"}),
    "saba_offer": ("Sabafon - Offer", "sabaoffer", {}, {"mobile": "mobile", "num": "external_code"}),
    "sbay_offer": ("Sabafon South - Offer", "sbayoffer", {}, {"mobile": "mobile", "num": "external_code"}),
    "sbay_denominations": ("Sabafon South - Recharge", "sbay?action=bill", {"action": "bill"}, {"mobile": "mobile", "num": "external_code"}),
    "saba_units": ("Sabafon - Units", "sabaunits", {}, {"mobile": "mobile", "num": "amount"}),
    "adenet_bill": ("Aden Net - Bill", "adenet?action=bill", {"action": "bill"}, {"mobile": "mobile", "num": "external_code"}),
    "adenet_query": ("Aden Net - Query", "adenet?action=query", {"action": "query"}, {"mobile": "mobile", "num": "external_code"}),
    "saba_gomla": ("Sabafon - Wholesale", "sabagomla", {}, {"mobile": "mobile", "num": "amount"}),
    "mtn_gomla": ("MTN - Wholesale", "mtngomla", {}, {"mobile": "mobile", "num": "amount"}),
    "mobile_gomla": ("Yemen Mobile - Wholesale", "mobilegomla", {}, {"mobile": "mobile", "num": "amount"}),
    "games_cards": ("Games and Cards", "gameswcards", {}, {"mobile": "mobile", "type": "external_code", "uniqcode": "uniqcode", "playerid": "playerid", "playername": "playername", "zoneid": "zoneid", "email": "email", "mobile": "mobile"}),
    "yem4g_bill": ("Yemen 4G - Bill", "yem4g", {"action": "bill"}, {"mobile": "mobile", "amount": "amount", "type": "type"}),
    "yem4g_query": ("Yemen 4G - Query", "yem4g", {"action": "query"}, {"mobile": "mobile"}),
    "electric_query": ("Electricity - Query", "electwater", {"action": "query", "act": "elect"}, {"mobile": "mobile", "customer_id": "customer_id", "placeid": "placeid"}),
    "electric_bill": ("Electricity - Bill", "electwater", {"action": "bill", "act": "elect"}, {"mobile": "mobile", "customer_id": "customer_id", "placeid": "placeid", "amount": "amount"}),
    "water_query": ("Water - Query", "electwater", {"action": "query", "act": "water"}, {"mobile": "mobile", "customer_id": "customer_id", "placeid": "placeid"}),
    "water_bill": ("Water - Bill", "electwater", {"action": "bill", "act": "water"}, {"mobile": "mobile", "customer_id": "customer_id", "placeid": "placeid", "amount": "amount"}),
}

BASE_FIELDS = [("mobile", "رقم المستفيد/الاشتراك", "text", True)]


def ensure_field(service, key, label, field_type="text", required=True):
    ServiceField.objects.update_or_create(service=service, key=key, defaults={"label": label, "field_type": field_type, "required": required, "sort_order": 10 if key == "mobile" else 20})


@transaction.atomic
def provision():
    mains = {}
    for key, (name, slug) in MAIN.items():
        mains[key], _ = MainServiceCategory.objects.update_or_create(slug=slug, defaults={"name": name, "is_active": True})
    categories = {}
    for main_key, name, slug in CATEGORIES:
        categories[slug], _ = ServiceCategory.objects.update_or_create(main_category=mains[main_key], slug=slug, parent=None, defaults={"name": name, "is_active": True})
    services = {}
    amount_services = {"you-balance", "why-balance", "yem4g-balance", "yem-balance", "why-bill", "saba-units", "saba-gomla", "mtn-gomla", "mobile-gomla", "post-adsl", "post-line"}
    for category_slug, name, code, pricing, link_key in SERVICES:
        category = categories[category_slug]
        services[code], _ = Service.objects.update_or_create(code=code, defaults={"category": category, "name": name, "slug": slugify(code, allow_unicode=True), "pricing_mode": pricing, "currency": "YER", "is_active": True})
        ensure_field(services[code], "mobile", "رقم المستفيد/الاشتراك")
        if code in amount_services:
            ensure_field(services[code], "amount", "المبلغ", "decimal", True)
        if code in {"you-balance", "yem4g-balance"}:
            ensure_field(services[code], "type", "نوع الخط/الباقة")
        if code == "why-balance":
            ensure_field(services[code], "num", "الكمية", "decimal")
        if code in {"electric-query", "electric-bill", "water-query", "water-bill"}:
            ensure_field(services[code], "customer_id", "رقم المشترك", "text", True)
            ensure_field(services[code], "placeid", "رقم المنطقة", "text", True)
        if link_key == "games_cards":
            for key, label in [("playerid", "رقم اللاعب"), ("playername", "اسم اللاعب"), ("zoneid", "Zone ID"), ("email", "البريد الإلكتروني"), ("uniqcode", "كود الفئة الموحد")]:
                ensure_field(services[code], key, label, "text", key in {"playerid", "uniqcode"})
        if pricing == "item":
            ensure_field(services[code], "external_code", "كود المنتج/الباقة", "text", True)
    return mains, categories, services


def provision_links(connection, services):
    result = {}
    for code, (name, path, fixed, field_map) in LINKS.items():
        link, _ = ProviderLink.objects.update_or_create(code=f"{connection.code}-{code}", defaults={"provider": connection, "name": name, "operation": code, "path_template": path, "http_method": "GET", "fixed_params": fixed, "field_map": field_map, "success_codes": ["0"], "pending_codes": ["-2"], "status_path_template": "info", "status_params": {"action": "status"}, "priority": 100})
        result[code] = link
    for category_slug, name, service_code, pricing, link_key in SERVICES:
        service = services[service_code]
        link = result[link_key]
        ServiceDistribution.objects.update_or_create(service=service, provider_link=link, defaults={"priority": 100, "is_active": True, "conditions": {}})
    return result


class Command(BaseCommand):
    help = "تهيئة كاملة لقالب Sanaacash/Yemen Robot كما هو موثق في ملف الربط. لا تُدخل أي بيانات اعتماد."

    def add_arguments(self, parser):
        parser.add_argument("--provider-code", default="sanaacash-1")
        parser.add_argument("--provider-name", default="صنعاء كاش - الربطية الأولى")
        parser.add_argument("--base-url", default="https://sanaacash.yrbso.net/api/yr/")
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **options):
        if options["dry_run"]:
            self.stdout.write(self.style.WARNING("Dry run: لن يتم تعديل قاعدة البيانات."))
            self.stdout.write(f"سيتم إنشاء {len(CATEGORIES)} فئات و{len(SERVICES)} خدمة و{len(LINKS)} مسار API.")
            return
        with transaction.atomic():
            connection, _ = ProviderConnection.objects.update_or_create(code=options["provider_code"], defaults={"name": options["provider_name"], "connection_type": ProviderConnection.Types.SANAACASH, "base_url": options["base_url"], "is_active": True})
            _, _, services = provision()
            links = provision_links(connection, services)
        self.stdout.write(self.style.SUCCESS(f"تمت تهيئة Sanaacash: {len(services)} خدمة و{len(links)} مسار وربطها بالتوزيع."))
