from functools import wraps

from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from catalog.forms import ProductForm
from catalog.models import Category, Product
from vendors.forms import VendorProfileForm
from vendors.models import VendorProfile
from vendors.services import set_vendor_status


CONTROL_HOME = "/admin/dashboard/control/"
CONTROL_STORES = f"{CONTROL_HOME}stores/"
CONTROL_PRODUCTS = f"{CONTROL_HOME}products/"
CONTROL_PLACEHOLDER_SECTIONS = {"applications", "categories", "variants", "orders", "payments", "finance"}


def control_access_required(view):
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        user = request.user
        if not user.is_authenticated:
            return redirect(f"/admin/dashboard/login/?next={request.get_full_path()}")
        if not (user.is_staff or getattr(user, "role", None) == "admin"):
            return HttpResponse("ليس لديك صلاحية الوصول إلى لوحة الإدارة الجديدة.", status=403)
        return view(request, *args, **kwargs)

    return wrapped


def is_ajax(request):
    return request.headers.get("X-Requested-With") == "XMLHttpRequest"


def _store_context(request, form=None, edit_vendor=None, form_open=False):
    qs = VendorProfile.objects.select_related("owner").annotate(
        product_count=Count("products", distinct=True),
        order_count=Count("vendor_orders", distinct=True),
    )
    q = request.GET.get("q", "").strip()
    status = request.GET.get("status", "").strip()
    sort = request.GET.get("sort", "newest").strip()

    if q:
        qs = qs.filter(
            Q(store_name__icontains=q)
            | Q(slug__icontains=q)
            | Q(phone__icontains=q)
            | Q(owner__phone__icontains=q)
            | Q(owner__email__icontains=q)
            | Q(owner__first_name__icontains=q)
            | Q(owner__last_name__icontains=q)
        )
    if status in {"active", "pending", "suspended"}:
        qs = qs.filter(status=status)
    if sort == "name":
        qs = qs.order_by("store_name")
    elif sort == "products":
        qs = qs.order_by("-product_count", "store_name")
    elif sort == "orders":
        qs = qs.order_by("-order_count", "store_name")
    else:
        sort = "newest"
        qs = qs.order_by("-created_at")

    page = Paginator(qs, 15).get_page(request.GET.get("page"))
    if form is None:
        form = VendorProfileForm(initial={"status": "active", "commission_percent": 10})

    return {"page": page, "q": q, "status": status, "sort": sort,
            "stats": {"total": VendorProfile.objects.count(), "active": VendorProfile.objects.filter(status="active").count(),
                       "pending": VendorProfile.objects.filter(status="pending").count(), "suspended": VendorProfile.objects.filter(status="suspended").count()},
            "form": form, "edit_vendor": edit_vendor, "form_open": form_open}


def _product_context(request, form=None, edit_product=None, form_open=False):
    qs = Product.objects.select_related("vendor").prefetch_related("categories")
    q = request.GET.get("q", "").strip(); status = request.GET.get("status", "").strip(); stock = request.GET.get("stock", "").strip()
    if q: qs = qs.filter(Q(name__icontains=q) | Q(sku__icontains=q))
    if status == "published": qs = qs.filter(is_published=True)
    elif status == "hidden": qs = qs.filter(is_published=False)
    elif status == "trending": qs = qs.filter(is_trending=True)
    if stock == "low": qs = qs.filter(stock__gt=0, stock__lte=5)
    elif stock == "out": qs = qs.filter(stock__lte=0)
    page = Paginator(qs.order_by("-updated_at", "-id"), 20).get_page(request.GET.get("page"))
    if form is None: form = ProductForm()
    return {"page": page, "filters": {"q": q, "status": status, "stock": stock},
            "stats": {"total": Product.objects.count(), "published": Product.objects.filter(is_published=True).count(),
                       "hidden": Product.objects.filter(is_published=False).count(), "low_stock": Product.objects.filter(stock__gt=0, stock__lte=5).count(),
                       "out_of_stock": Product.objects.filter(stock__lte=0).count()},
            "vendors": VendorProfile.objects.filter(status="active").order_by("store_name"),
            "categories": Category.objects.filter(is_active=True).order_by("sort_order", "name"),
            "form": form, "edit_product": edit_product, "form_open": form_open}


def render_control_partial(request, section, context=None):
    context = context or {}
    if section == "stores":
        return render(request, "admin/control/inner/stores.html", {**_store_context(request), **context})
    if section == "products":
        return render(request, "admin/control/inner/products.html", {**_product_context(request), **context})
    titles = {"applications": "طلبات المتاجر", "categories": "التصنيفات", "variants": "المتغيرات والمخزون", "orders": "الطلبات والمبيعات", "payments": "المدفوعات", "finance": "الشحن والمالية"}
    return render(request, "admin/control/inner/coming_soon.html", {"title": titles.get(section, section), "section": section})


@control_access_required
@require_http_methods(["GET", "POST"])
def control_stores(request):
    edit_vendor = None; form = None; form_open = False
    if request.method == "POST":
        vendor_id = request.POST.get("vendor_id", "").strip()
        edit_vendor = get_object_or_404(VendorProfile, pk=vendor_id) if vendor_id else None
        form = VendorProfileForm(request.POST, request.FILES, instance=edit_vendor)
        form_open = True
        if form.is_valid():
            vendor = form.save(); messages.success(request, f"تم حفظ المتجر «{vendor.store_name}».")
            return render_control_partial(request, "stores") if is_ajax(request) else redirect(CONTROL_STORES)
    else:
        if not is_ajax(request):
            return redirect(f"{CONTROL_HOME}?screen=stores")
        edit_id = request.GET.get("edit", "").strip()
        if edit_id:
            edit_vendor = get_object_or_404(VendorProfile.objects.select_related("owner"), pk=edit_id)
            form = VendorProfileForm(instance=edit_vendor); form_open = True
        else:
            form = VendorProfileForm(initial={"status": "active", "commission_percent": 10})
    return render_control_partial(request, "stores", {"form": form, "edit_vendor": edit_vendor, "form_open": form_open})


@control_access_required
@require_http_methods(["POST"])
def control_store_status(request, vendor_id, status):
    vendor = get_object_or_404(VendorProfile, pk=vendor_id)
    if status not in {"active", "pending", "suspended"}: return HttpResponse("حالة غير صالحة", status=400)
    set_vendor_status(vendor, status); messages.success(request, f"تم تحديث حالة متجر «{vendor.store_name}».")
    return render_control_partial(request, "stores") if is_ajax(request) else redirect(CONTROL_STORES)


@control_access_required
@require_http_methods(["GET", "POST"])
def control_products(request):
    edit_product = None; form = None; form_open = False
    if request.method == "POST":
        product_id = request.POST.get("product_id", "").strip()
        edit_product = get_object_or_404(Product, pk=product_id) if product_id else None
        form = ProductForm(request.POST, request.FILES, instance=edit_product); form_open = True
        if form.is_valid():
            product = form.save(); messages.success(request, f"تم حفظ المنتج «{product.name}».")
            return render_control_partial(request, "products") if is_ajax(request) else redirect(CONTROL_PRODUCTS)
    else:
        if not is_ajax(request):
            return redirect(f"{CONTROL_HOME}?screen=products")
        edit_id = request.GET.get("edit", "").strip()
        if edit_id:
            edit_product = get_object_or_404(Product.objects.select_related("vendor"), pk=edit_id)
            form = ProductForm(instance=edit_product); form_open = True
        else:
            form = ProductForm()
    return render_control_partial(request, "products", {"form": form, "edit_product": edit_product, "form_open": form_open})


@control_access_required
@require_http_methods(["GET"])
def control_placeholder(request, section):
    if section not in CONTROL_PLACEHOLDER_SECTIONS: return HttpResponse("Not found", status=404)
    if is_ajax(request): return render_control_partial(request, section)
    return redirect(f"{CONTROL_HOME}?screen={section}")
