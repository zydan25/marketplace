from decimal import Decimal
from functools import wraps

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import Permission
from django.db.models import Sum
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.utils import timezone

from .marketplace_models import Payment, VendorApplication, VendorLedgerEntry, VendorOrder
from .models import Category, Notification, Order, Product, StorefrontSection, User, VendorPayout, VendorProfile, Wallet


ADMIN_DASHBOARD_LOGIN = "/admin/dashboard/login/"
ADMIN_DASHBOARD_HOME = "/admin/dashboard/"


def dashboard_access_required(view):
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            next_url = request.get_full_path()
            separator = "&" if "?" in ADMIN_DASHBOARD_LOGIN else "?"
            return redirect(f"{ADMIN_DASHBOARD_LOGIN}?next={next_url}")
        if not (request.user.is_staff or getattr(request.user, "role", None) == "admin"):
            return HttpResponse("ليس لديك صلاحية الوصول إلى لوحة الإدارة.", status=403)
        return view(request, *args, **kwargs)
    return wrapped


def dashboard_login(request):
    if request.user.is_authenticated and (request.user.is_staff or getattr(request.user, "role", None) == "admin"):
        return redirect(ADMIN_DASHBOARD_HOME)
    error = None
    if request.method == "POST":
        phone = str(request.POST.get("phone", "")).strip()
        password = str(request.POST.get("password", ""))
        user = User.objects.filter(phone=phone).first() if phone else None
        authenticated = authenticate(request, username=phone, password=password) if user else None
        if authenticated and authenticated.is_active and (authenticated.is_staff or authenticated.role == "admin"):
            login(request, authenticated)
            if not authenticated.is_staff:
                authenticated.is_staff = True
                authenticated.save(update_fields=["is_staff"])
            perms = Permission.objects.filter(content_type__app_label="marketplace")
            authenticated.user_permissions.set(perms)
            return redirect(ADMIN_DASHBOARD_HOME)
        error = "بيانات الدخول غير صحيحة أو لا يملك الحساب صلاحية الإدارة."
    return render(request, "admin/dashboard_login.html", {"error": error})


def dashboard_logout(request):
    logout(request)
    return redirect(ADMIN_DASHBOARD_LOGIN)


def _dashboard_context():
    now = timezone.now()
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    active_vendors = VendorProfile.objects.filter(status="active").count()
    pending_vendors = VendorApplication.objects.filter(status="pending").count()
    today_orders = Order.objects.filter(created_at__gte=start).count()
    today_revenue = Order.objects.filter(created_at__gte=start, payment_status="paid").aggregate(v=Sum("total"))["v"] or Decimal("0")
    pending_payouts = VendorPayout.objects.filter(status__in=["pending", "approved"]).aggregate(v=Sum("amount"))["v"] or Decimal("0")
    low_stock = Product.objects.filter(is_published=True, stock__lte=5).select_related("vendor").order_by("stock", "name")[:8]
    recent_orders = Order.objects.select_related("customer").order_by("-created_at")[:10]
    recent_vendors = VendorProfile.objects.select_related("owner").order_by("-created_at")[:8]
    applications = VendorApplication.objects.select_related("applicant").filter(status="pending").order_by("-created_at")[:8]
    return {
        "now": now,
        "stats": {
            "customers": User.objects.filter(role="customer").count(),
            "vendors": active_vendors,
            "pending_vendors": pending_vendors,
            "products": Product.objects.count(),
            "published_products": Product.objects.filter(is_published=True).count(),
            "orders": Order.objects.count(),
            "today_orders": today_orders,
            "today_revenue": today_revenue,
            "wallet_balance": Wallet.objects.aggregate(v=Sum("balance"))["v"] or Decimal("0"),
            "pending_payouts": pending_payouts,
            "categories": Category.objects.filter(is_active=True).count(),
            "storefront_sections": StorefrontSection.objects.filter(is_visible=True).count(),
            "unread_notifications": Notification.objects.filter(is_read=False).count(),
        },
        "low_stock": low_stock,
        "recent_orders": recent_orders,
        "recent_vendors": recent_vendors,
        "applications": applications,
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
        "ledger": VendorLedgerEntry.objects.order_by("-created_at")[:8],
    }


@dashboard_access_required
def dashboard(request):
    return render(request, "admin/dashboard.html", _dashboard_context())


@dashboard_access_required
def dashboard_manifest(request):
    return JsonResponse({
        "name": "سوقيك — مركز إدارة المنصة",
        "short_name": "سوقيك Admin",
        "lang": "ar",
        "dir": "rtl",
        "start_url": ADMIN_DASHBOARD_HOME,
        "scope": "/admin/",
        "display": "standalone",
        "background_color": "#f4f7fb",
        "theme_color": "#111827",
        "icons": [{"src": "/admin/dashboard/icon.svg", "sizes": "any", "type": "image/svg+xml", "purpose": "any maskable"}],
    })


def dashboard_worker(request):
    js = """
const CACHE='shabik-admin-v2';
self.addEventListener('install',e=>e.waitUntil(caches.open(CACHE).then(c=>c.addAll(['/admin/dashboard/','/admin/dashboard/icon.svg'])).then(()=>self.skipWaiting())));
self.addEventListener('activate',e=>e.waitUntil(self.clients.claim()));
self.addEventListener('fetch',e=>{if(e.request.method!=='GET')return;e.respondWith(fetch(e.request).then(r=>{const copy=r.clone();caches.open(CACHE).then(c=>c.put(e.request,copy));return r}).catch(()=>caches.match(e.request)))});
"""
    return HttpResponse(js, content_type="application/javascript")


def dashboard_icon(request):
    svg = """<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 512 512'><rect width='512' height='512' rx='110' fill='#111827'/><path d='M117 156h278v55H117zm32 88h214v130H149zm44 37v50h126v-50z' fill='white'/></svg>"""
    return HttpResponse(svg, content_type="image/svg+xml")
