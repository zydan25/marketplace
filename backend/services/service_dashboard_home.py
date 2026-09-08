from django.contrib.auth.decorators import user_passes_test
from django.db.models import Count, Q
from django.shortcuts import render
from django.utils import timezone

from .admin_v4 import staff_only
from .models import (
    GameProduct,
    MainServiceCategory,
    ProviderConnection,
    ProviderLink,
    Service,
    ServiceCategory,
    ServiceDistribution,
    ServiceTransaction,
    TelecomDenomination,
    TelecomPlan,
)
from .wifi_cards import WifiCard
from .wifi_denominations import WifiDenomination
from .wifi_networks import WifiNetwork


@user_passes_test(staff_only, login_url="/admin/dashboard/login/")
def modern_home(request):
    section = (request.GET.get("section") or "overview").strip()
    if section not in {"overview", "services", "payments", "games", "operations", "providers", "wifi"}:
        section = "overview"

    q = (request.GET.get("q") or "").strip()
    status = (request.GET.get("status") or "").strip()
    main_id = (request.GET.get("main") or "").strip()
    service_id = (request.GET.get("service") or "").strip()
    sort = (request.GET.get("sort") or "newest").strip()

    mains = list(MainServiceCategory.objects.annotate(category_count=Count("categories", distinct=True)).order_by("sort_order", "id"))
    categories = ServiceCategory.objects.select_related("main_category").order_by("main_category__sort_order", "sort_order", "id")
    services = Service.objects.select_related("category__main_category").prefetch_related("fields").order_by("category__main_category__sort_order", "category__sort_order", "sort_order", "id")

    selected_main = MainServiceCategory.objects.filter(pk=main_id).first() if main_id.isdigit() else None
    selected_service = Service.objects.select_related("category__main_category").filter(pk=service_id).first() if service_id.isdigit() else None

    telecom_filter = Q(is_active=True)
    game_filter = Q(is_active=True)
    if selected_main:
        telecom_filter &= Q(service__category__main_category=selected_main)
        game_filter &= Q(service__category__main_category=selected_main)
    if selected_service:
        telecom_filter &= Q(service=selected_service)
        game_filter &= Q(service=selected_service)
    if q:
        telecom_filter &= (Q(name__icontains=q) | Q(external_code__icontains=q) | Q(service__name__icontains=q))
        game_filter &= (Q(name__icontains=q) | Q(external_code__icontains=q) | Q(service__name__icontains=q))

    plans = TelecomPlan.objects.select_related("service__category__main_category").filter(telecom_filter)
    denoms = TelecomDenomination.objects.select_related("service__category__main_category").filter(telecom_filter)
    games = GameProduct.objects.select_related("service__category__main_category").filter(game_filter)

    if sort == "name":
        plans, denoms, games = plans.order_by("name", "id"), denoms.order_by("name", "id"), games.order_by("name", "id")
    elif sort == "price":
        plans, denoms, games = plans.order_by("price", "id"), denoms.order_by("sale_price", "id"), games.order_by("price", "id")
    else:
        plans, denoms, games = plans.order_by("-id"), denoms.order_by("-id"), games.order_by("-id")

    transactions = ServiceTransaction.objects.select_related("service__category__main_category", "customer", "provider_link").order_by("-created_at")
    if q:
        transactions = transactions.filter(Q(mobile__icontains=q) | Q(provider_transaction_id__icontains=q) | Q(provider_transid__icontains=q) | Q(service__name__icontains=q))
    if status:
        transactions = transactions.filter(status=status)

    providers = ProviderConnection.objects.prefetch_related("links").order_by("name")
    provider_links = ProviderLink.objects.select_related("provider").filter(is_active=True).order_by("provider__name", "priority", "id")
    distributions = ServiceDistribution.objects.select_related("service", "provider_link__provider").filter(is_active=True).order_by("service__name", "priority", "id")

    wifi_networks = WifiNetwork.objects.select_related("owner").prefetch_related("denominations__cards").order_by("name")
    wifi_denoms = WifiDenomination.objects.select_related("network").prefetch_related("cards").order_by("network__name", "face_value", "id")
    wifi_cards = WifiCard.objects.select_related("denomination__network").order_by("-id")
    if q:
        wifi_networks = wifi_networks.filter(Q(name__icontains=q) | Q(location__icontains=q))
        wifi_denoms = wifi_denoms.filter(Q(name__icontains=q) | Q(denomination_number__icontains=q) | Q(network__name__icontains=q))
        wifi_cards = wifi_cards.filter(Q(card_number__icontains=q) | Q(denomination__name__icontains=q) | Q(denomination__network__name__icontains=q))

    today = timezone.localdate()
    context = {
        "section": section,
        "q": q,
        "status": status,
        "sort": sort,
        "selected_main": selected_main,
        "selected_service": selected_service,
        "mains": mains,
        "categories": categories[:160],
        "services": services[:160],
        "payments_plans": plans[:180],
        "payments_denoms": denoms[:180],
        "games": games[:180],
        "transactions": transactions[:180],
        "status_choices": ServiceTransaction.Status.choices,
        "providers": providers[:100],
        "provider_links": provider_links[:180],
        "distributions": distributions[:180],
        "wifi_networks": wifi_networks[:120],
        "wifi_denoms": wifi_denoms[:180],
        "wifi_cards": wifi_cards[:220],
        "counts": {
            "mains": MainServiceCategory.objects.count(),
            "categories": ServiceCategory.objects.count(),
            "services": Service.objects.filter(is_active=True).count(),
            "plans": TelecomPlan.objects.filter(is_active=True).count(),
            "denoms": TelecomDenomination.objects.filter(is_active=True).count(),
            "games": GameProduct.objects.filter(is_active=True).count(),
            "transactions": ServiceTransaction.objects.count(),
            "success_today": ServiceTransaction.objects.filter(status=ServiceTransaction.Status.SUCCESS, created_at__date=today).count(),
            "providers": ProviderConnection.objects.filter(is_active=True).count(),
            "wifi_cards": WifiCard.objects.count(),
        },
    }
    return render(request, "services/service_dashboard_home.html", context)
