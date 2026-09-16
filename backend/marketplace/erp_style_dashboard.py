from collections import OrderedDict
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import user_passes_test
from django.db.models import Sum
from django.shortcuts import render
from django.utils import timezone

from .dashboard import dashboard_access_required
from .marketplace_models import Payment, VendorApplication, VendorOrder
from .models import Category, Notification, Order, Product, StorefrontSection, VendorPayout, VendorProfile, Wallet
from services.models import (
    DigitalProduct,
    GameProduct,
    Service,
    ServiceDistribution,
    ServiceOption,
    ServiceTask,
    ServiceTransaction,
    TelecomDenomination,
    TelecomPlan,
)
from services.service_platform_v2 import PACKAGE_SERVICES
from services.settings_models import ServiceSetting


User = get_user_model()


@dashboard_access_required
def erp_style_dashboard(request):
    """Fresh ERP-style administration UI. Read-only dashboard composition; business logic is untouched."""
    now = timezone.now()
    day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    # Core platform figures.
    stats = {
        "products": Product.objects.count(),
        "customers": User.objects.filter(role="customer").count(),
        "stores": VendorProfile.objects.filter(status="active").count(),
        "categories": Category.objects.filter(is_active=True).count(),
        "orders": Order.objects.count(),
        "today_orders": Order.objects.filter(created_at__gte=day_start).count(),
        "today_paid": Order.objects.filter(created_at__gte=day_start, payment_status="paid").aggregate(v=Sum("total"))["v"] or Decimal("0"),
        "wallet_balance": Wallet.objects.aggregate(v=Sum("balance"))["v"] or Decimal("0"),
        "pending_applications": VendorApplication.objects.filter(status="pending").count(),
        "pending_payouts": VendorPayout.objects.filter(status__in=["pending", "approved"]).count(),
        "notifications": Notification.objects.filter(is_read=False).count(),
    }

    # Service operations stay database-driven so the navigation follows the actual catalog.
    service_rows = Service.objects.filter(is_active=True).select_related("category__main_category").order_by(
        "category__main_category__sort_order", "category__sort_order", "sort_order", "id"
    )
    service_tree = OrderedDict()
    for service in service_rows:
        main_name = getattr(getattr(service.category, "main_category", None), "name", "الخدمات")
        cat_name = getattr(service.category, "name", "عام")
        service_tree.setdefault(main_name, OrderedDict()).setdefault(cat_name, []).append(service)

    service_counts = {
        "services": service_rows.count(),
        "settings": ServiceSetting.objects.filter(is_active=True).count(),
        "providers": ServiceTransaction.objects.values("provider").distinct().count() if hasattr(ServiceTransaction, "provider") else 0,
        "distributions": ServiceDistribution.objects.filter(is_active=True).count(),
        "plans": TelecomPlan.objects.filter(is_active=True).count(),
        "denominations": TelecomDenomination.objects.filter(is_active=True).count(),
        "games": GameProduct.objects.filter(is_active=True).count(),
        "digital": DigitalProduct.objects.filter(is_active=True).count(),
        "options": ServiceOption.objects.filter(is_active=True).count(),
    }

    # Package navigation is based on the existing service-platform catalog.
    package_nav = []
    for key, (provider_name, service_code, title) in PACKAGE_SERVICES.items():
        service = service_rows.filter(code=service_code).first()
        if service:
            package_nav.append({"key": key, "name": provider_name, "title": title, "service": service})

    transaction_status = OrderedDict()
    for row in ServiceTransaction.objects.values("status").annotate(total=Sum("amount")).order_by("status"):
        transaction_status[row["status"] or "غير محدد"] = row["total"] or Decimal("0")

    latest_transactions = ServiceTransaction.objects.select_related("service", "customer").order_by("-created_at")[:10]
    latest_orders = Order.objects.select_related("customer").order_by("-created_at")[:8]
    latest_stores = VendorProfile.objects.select_related("owner").order_by("-created_at")[:8]
    low_stock = Product.objects.filter(is_published=True, stock__lte=5).order_by("stock", "name")[:8]
    pending_applications = VendorApplication.objects.select_related("applicant").filter(status="pending").order_by("-created_at")[:6]
    recent_settings = ServiceSetting.objects.select_related("service").filter(is_active=True).order_by("group", "sort_order", "id")[:8]
    recent_tasks = ServiceTask.objects.order_by("-created_at")[:8]

    return render(
        request,
        "admin/erp_style_dashboard.html",
        {
            "now": now,
            "stats": stats,
            "service_tree": service_tree,
            "package_nav": package_nav,
            "service_counts": service_counts,
            "transaction_status": transaction_status,
            "latest_transactions": latest_transactions,
            "latest_orders": latest_orders,
            "latest_stores": latest_stores,
            "low_stock": low_stock,
            "pending_applications": pending_applications,
            "recent_settings": recent_settings,
            "recent_tasks": recent_tasks,
            "payment_summary": {
                "paid": Payment.objects.filter(status="paid").count(),
                "pending": Payment.objects.filter(status="pending").count(),
                "failed": Payment.objects.filter(status="failed").count(),
            },
            "vendor_orders": {
                "pending": VendorOrder.objects.filter(status="pending").count(),
                "processing": VendorOrder.objects.filter(status="processing").count(),
                "shipped": VendorOrder.objects.filter(status="shipped").count(),
                "delivered": VendorOrder.objects.filter(status="delivered").count(),
            },
        },
    )
