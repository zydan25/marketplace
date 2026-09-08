from collections import defaultdict

from django.db import transaction
from django.utils.text import slugify

from .models import MainServiceCategory, Service, ServiceCategory, TelecomPlan, TelecomPlanType


PROVIDER_ICONS = {
    "yemen-mobile": "yemen_mobile",
    "sabafon": "sim_card",
    "you": "you",
    "why": "wifi",
    "yemen-4g": "4g_mobiledata",
    "yemen-net": "router",
    "adenet": "router",
    "electricity": "bolt",
    "water": "water_drop",
    "wholesale": "warehouse",
}

BRANCHES = {
    "query": ("الاستعلام", "search"),
    "balance": ("الرصيد", "account_balance_wallet"),
    "denom": ("الفئات", "sell"),
    "offer": ("الباقات", "inventory_2"),
    "bill": ("التسديد", "receipt_long"),
    "wholesale": ("الجملة", "warehouse"),
    "other": ("الخدمات", "apps"),
}

QUERY_CODES = {
    "yem-query-balance", "yem-query-offers", "yem4g-query", "post-query",
    "adenet-query", "electric-query", "water-query",
}


def _branch_key(code):
    code = str(code or "").lower()
    if code in QUERY_CODES or "query" in code:
        return "query"
    if "gomla" in code:
        return "wholesale"
    if "denomination" in code or "units" in code:
        return "denom"
    if "offer" in code or "package" in code:
        return "offer"
    if "balance" in code:
        return "balance"
    if "bill" in code:
        return "bill"
    return "other"


def _ensure_child(main, parent, slug, name, icon="apps", order=0):
    obj, _ = ServiceCategory.objects.update_or_create(
        main_category=main,
        parent=parent,
        slug=slug,
        defaults={"name": name, "icon": icon, "sort_order": order, "is_active": True},
    )
    return obj


def _repair_payment_hierarchy(main):
    for category in main.categories.filter(parent=None, is_active=True).order_by("sort_order", "id"):
        if category.slug not in PROVIDER_ICONS:
            continue
        category.icon = PROVIDER_ICONS[category.slug]
        category.save(update_fields=["icon"])
        branches = {}
        for index, key in enumerate(("balance", "denom", "offer", "query", "bill", "wholesale", "other"), start=1):
            name, icon = BRANCHES[key]
            branches[key] = _ensure_child(
                main,
                category,
                slug=f"{category.slug}-{key}",
                name=name,
                icon=icon,
                order=index * 10,
            )
        services = list(category.services.filter(is_active=True).order_by("sort_order", "id"))
        for service in services:
            branch = branches[_branch_key(service.code)]
            service.category = branch
            service.icon = BRANCHES[_branch_key(service.code)][1]
            service.save(update_fields=["category", "icon"])


def _repair_games(main, category_slug, *, is_digital=False):
    root = main.categories.filter(parent=None, slug=category_slug, is_active=True).first()
    if root is None:
        return
    root.icon = "apps" if is_digital else "gamepad"
    root.save(update_fields=["icon"])
    services = list(root.services.filter(is_active=True).order_by("sort_order", "id"))
    for index, service in enumerate(services, start=1):
        child = _ensure_child(
            main,
            root,
            slug=slugify(service.code, allow_unicode=True)[:160] or f"service-{service.id}",
            name=service.name,
            icon=service.icon or ("apps" if is_digital else "gamepad"),
            order=index * 10,
        )
        service.category = child
        service.icon = child.icon
        service.save(update_fields=["category", "icon"])


def _repair_plan_types():
    created_or_updated = 0
    services = Service.objects.filter(is_active=True, telecom_plans__is_active=True).distinct()
    for service in services:
        groups = defaultdict(list)
        plans = TelecomPlan.objects.filter(service=service, is_active=True).order_by("sort_order", "id")
        for plan in plans:
            payment = (plan.payment_type or "other").strip().lower() or "other"
            line = (plan.line_type or "all").strip().lower() or "all"
            groups[(payment, line)].append(plan)
        for sort_order, ((payment, line), grouped_plans) in enumerate(groups.items(), start=1):
            payment_label = {
                "prepaid": "دفع مسبق",
                "postpaid": "فوترة",
                "paid": "مدفوع",
            }.get(payment, "نوع آخر")
            line_label = "شريحة" if line in {"sim", "شريحة"} else "برمجة" if line in {"programming", "برمجة"} else ("الكل" if line == "all" else line)
            label = payment_label if line_label == "الكل" else f"{payment_label} - {line_label}"
            code = f"{payment}:{line}"[:80]
            obj, _ = TelecomPlanType.objects.update_or_create(
                service=service,
                code=code,
                defaults={
                    "name": label,
                    "description": line_label,
                    "sort_order": sort_order,
                    "is_active": True,
                },
            )
            obj.plans.set(grouped_plans)
            created_or_updated += 1
    return created_or_updated


@transaction.atomic
def repair_hierarchy():
    payments = MainServiceCategory.objects.filter(slug="payments", is_active=True).first()
    games = MainServiceCategory.objects.filter(slug="games", is_active=True).first()
    digital = MainServiceCategory.objects.filter(slug="software", is_active=True).first()

    if payments:
        _repair_payment_hierarchy(payments)
    if games:
        _repair_games(games, "games", is_digital=False)
    if digital:
        _repair_games(digital, "digital-cards", is_digital=True)

    return {"plan_types": _repair_plan_types()}
