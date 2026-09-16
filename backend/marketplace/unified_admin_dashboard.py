from decimal import Decimal

from django.contrib.auth.decorators import user_passes_test
from django.db.models import Count, Q, Sum
from django.shortcuts import render
from django.utils import timezone

from accounting.models import Account, JournalEntry, WithdrawalRequest
from catalog.models import Category, Product, ProductVariant
from communication.models import Conversation, Notification
from finance.models import VendorPayout, Wallet
from orders.models import Order, Payment, Shipment, VendorOrder
from promotions.models import Coupon, Loan
from services.models import (
    MainServiceCategory,
    Service,
    ServiceCategory,
    ServiceDistribution,
    ServiceTask,
    ServiceTransaction,
    TelecomDenomination,
    TelecomPlan,
    GameProduct,
    DigitalProduct,
    ServiceOption,
)
from services.settings_models import ServiceSetting
from vendors.models import VendorApplication, VendorProfile


def staff_only(user):
    return bool(user.is_authenticated and (user.is_staff or getattr(user, "role", None) == "admin"))


def _service_tree():
    mains = MainServiceCategory.objects.filter(is_active=True).prefetch_related(
        "categories__services",
    ).order_by("sort_order", "id")
    tree = []
    for main in mains:
        categories = []
        for category in main.categories.filter(is_active=True).order_by("sort_order", "id"):
            services = list(category.services.filter(is_active=True).order_by("sort_order", "id"))
            if services:
                categories.append({"category": category, "services": services})
        if categories:
            tree.append({"main": main, "categories": categories})
    return tree


def _service_counts():
    qs = Service.objects.filter(is_active=True)
    return {
        "all": qs.count(),
        "purchase": qs.filter(service_kind=Service.ServiceKinds.PURCHASE).count(),
        "query": qs.filter(service_kind=Service.ServiceKinds.QUERY).count(),
        "catalog": qs.filter(service_kind=Service.ServiceKinds.CATALOG).count(),
        "with_balance": qs.filter(requires_balance=True).count(),
        "distributions": ServiceDistribution.objects.filter(is_active=True).count(),
        "settings": ServiceSetting.objects.filter(is_active=True).count(),
        "plans": TelecomPlan.objects.filter(is_active=True).count(),
        "denoms": TelecomDenomination.objects.filter(is_active=True).count(),
        "games": GameProduct.objects.filter(is_active=True).count(),
        "digital": DigitalProduct.objects.filter(is_active=True).count(),
        "options": ServiceOption.objects.filter(is_active=True).count(),
    }


def _money(value):
    return Decimal(value or 0)


@user_passes_test(staff_only, login_url="/admin/dashboard/login/")
def unified_admin_dashboard(request):
    now = timezone.now()
    day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    services = _service_counts()
    transaction_qs = ServiceTransaction.objects.all()
    task_qs = ServiceTask.objects.all()

    stats = {
        "customers": request.user.__class__.objects.filter(role="customer").count(),
        "stores": VendorProfile.objects.count(),
        "active_stores": VendorProfile.objects.filter(status="active").count(),
        "pending_store_applications": VendorApplication.objects.filter(status="pending").count(),
        "products": Product.objects.count(),
        "published_products": Product.objects.filter(is_published=True).count(),
        "categories": Category.objects.filter(is_active=True).count(),
        "variants": ProductVariant.objects.filter(is_active=True).count(),
        "orders": Order.objects.count(),
        "today_orders": Order.objects.filter(created_at__gte=day_start).count(),
        "paid_payments": Payment.objects.filter(status="paid").count(),
        "today_paid": Payment.objects.filter(status="paid", paid_at__gte=day_start).aggregate(v=Sum("amount"))["v"] or Decimal("0"),
        "vendor_orders": VendorOrder.objects.count(),
        "shipments_pending": Shipment.objects.filter(status__in=["pending", "ready", "in_transit"]).count(),
        "wallets": Wallet.objects.filter(is_active=True).count(),
        "accounts": Account.objects.filter(is_active=True).count(),
        "journals": JournalEntry.objects.filter(status=JournalEntry.Status.POSTED).count(),
        "pending_withdrawals": WithdrawalRequest.objects.filter(status=WithdrawalRequest.Status.PENDING).count(),
        "pending_payouts": VendorPayout.objects.filter(status__in=["pending", "approved"]).aggregate(v=Sum("amount"))["v"] or Decimal("0"),
        "unread_notifications": Notification.objects.filter(is_read=False).count(),
        "open_conversations": Conversation.objects.filter(is_closed=False).count(),
        "coupons": Coupon.objects.filter(is_active=True).count(),
        "loans_pending": Loan.objects.filter(status="pending").count(),
    }

    service_status = {
        "accepted": transaction_qs.filter(status=ServiceTransaction.Status.ACCEPTED).count(),
        "queued": transaction_qs.filter(status=ServiceTransaction.Status.QUEUED).count(),
        "processing": transaction_qs.filter(status=ServiceTransaction.Status.PROCESSING).count(),
        "pending_provider": transaction_qs.filter(status=ServiceTransaction.Status.PENDING_PROVIDER).count(),
        "manual_review": transaction_qs.filter(status=ServiceTransaction.Status.MANUAL_REVIEW).count(),
        "success": transaction_qs.filter(status=ServiceTransaction.Status.SUCCESS).count(),
        "failed": transaction_qs.filter(status=ServiceTransaction.Status.FAILED).count(),
        "refunded": transaction_qs.filter(status=ServiceTransaction.Status.REFUNDED).count(),
        "tasks_queued": task_qs.filter(status=ServiceTask.Statuses.QUEUED).count(),
        "tasks_running": task_qs.filter(status=ServiceTask.Statuses.RUNNING).count(),
        "tasks_retry": task_qs.filter(status=ServiceTask.Statuses.RETRY).count(),
        "tasks_failed": task_qs.filter(status=ServiceTask.Statuses.FAILED).count(),
    }

    context = {
        "now": now,
        "user": request.user,
        "stats": stats,
        "services": services,
        "service_tree": _service_tree(),
        "service_status": service_status,
        "recent_orders": Order.objects.select_related("customer").order_by("-created_at")[:8],
        "recent_transactions": ServiceTransaction.objects.select_related("customer", "service").order_by("-created_at")[:10],
        "recent_stores": VendorProfile.objects.select_related("owner").order_by("-created_at")[:6],
        "pending_applications": VendorApplication.objects.select_related("applicant").filter(status="pending").order_by("-created_at")[:6],
        "low_stock": Product.objects.filter(is_published=True, stock__lte=5).select_related("vendor").order_by("stock", "name")[:8],
        "service_settings": ServiceSetting.objects.filter(is_active=True).select_related("service").order_by("group", "sort_order", "id")[:12],
        "active_distributions": ServiceDistribution.objects.filter(is_active=True).select_related("service", "provider_link__provider").order_by("service_id", "priority")[:12],
    }
    return render(request, "admin/unified_dashboard.html", context)
