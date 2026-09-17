import json
from functools import wraps

from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Count, Q, Sum
from django.db.models.deletion import ProtectedError
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from catalog.forms import ProductForm
from catalog.models import Category, Product, ProductVariant
from finance.models import CurrencyRate, VendorCityShipping, VendorLedgerEntry, VendorPayout
from marketplace.models import OrderItem
from orders.models import Order, Payment
from vendors.forms import VendorProfileForm
from vendors.models import VendorApplication, VendorProfile
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
    qs = VendorProfile.objects.select_related("owner").annotate(product_count=Count("products", distinct=True), order_count=Count("vendor_orders", distinct=True))
    q = request.GET.get("q", "").strip(); status = request.GET.get("status", "").strip(); sort = request.GET.get("sort", "newest").strip()
    if q:
        qs = qs.filter(Q(store_name__icontains=q) | Q(slug__icontains=q) | Q(phone__icontains=q) | Q(owner__phone__icontains=q) | Q(owner__email__icontains=q) | Q(owner__first_name__icontains=q) | Q(owner__last_name__icontains=q))
    if status in {"active", "pending", "suspended"}: qs = qs.filter(status=status)
    if sort == "name": qs = qs.order_by("store_name")
    elif sort == "products": qs = qs.order_by("-product_count", "store_name")
    elif sort == "orders": qs = qs.order_by("-order_count", "store_name")
    else: sort = "newest"; qs = qs.order_by("-created_at")
    return {"page": Paginator(qs, 12).get_page(request.GET.get("page")), "q": q, "status": status, "sort": sort,
            "stats": {"total": VendorProfile.objects.count(), "active": VendorProfile.objects.filter(status="active").count(), "pending": VendorProfile.objects.filter(status="pending").count(), "suspended": VendorProfile.objects.filter(status="suspended").count()},
            "form": form or VendorProfileForm(initial={"status": "active", "commission_percent": 10}), "edit_vendor": edit_vendor, "form_open": form_open}


def _json_list(form, instance, name):
    if getattr(form, "is_bound", False):
        raw = form.data.get(name, "")
        try: value = json.loads(raw) if raw else []
        except (TypeError, ValueError): value = []
        return value if isinstance(value, list) else []
    if instance is not None:
        value = getattr(instance, name, [])
        return value if isinstance(value, list) else []
    return []


def _product_context(request, form=None, edit_product=None, form_open=False):
    qs = Product.objects.select_related("vendor").prefetch_related("categories")
    q = request.GET.get("q", "").strip(); status = request.GET.get("status", "").strip(); stock = request.GET.get("stock", "").strip()
    if q: qs = qs.filter(Q(name__icontains=q) | Q(sku__icontains=q) | Q(brand__icontains=q) | Q(material__icontains=q))
    if status == "published": qs = qs.filter(is_published=True)
    elif status == "hidden": qs = qs.filter(is_published=False)
    elif status == "trending": qs = qs.filter(is_trending=True)
    if stock == "low": qs = qs.filter(stock__gt=0, stock__lte=5)
    elif stock == "out": qs = qs.filter(stock__lte=0)
    page = Paginator(qs.order_by("-updated_at", "-id"), 18).get_page(request.GET.get("page"))
    form = form or ProductForm()
    brands = list(Product.objects.exclude(brand="").exclude(brand__isnull=True).values_list("brand", flat=True).distinct().order_by("brand")[:80])
    materials = list(Product.objects.exclude(material="").exclude(material__isnull=True).values_list("material", flat=True).distinct().order_by("material")[:80])
    colors, sizes = [], []
    for value in Product.objects.values_list("colors", flat=True).iterator():
        if isinstance(value, list): colors.extend(str(v) for v in value if v)
    for value in Product.objects.values_list("sizes", flat=True).iterator():
        if isinstance(value, list): sizes.extend(str(v) for v in value if v)
    colors = list(dict.fromkeys(colors))[:80]; sizes = list(dict.fromkeys(sizes))[:60]
    sales = OrderItem.objects.filter(product=edit_product).aggregate(quantity=Sum("quantity"), revenue=Sum("vendor_total")) if edit_product else {}
    return {"page": page, "filters": {"q": q, "status": status, "stock": stock},
            "stats": {"total": Product.objects.count(), "published": Product.objects.filter(is_published=True).count(), "low_stock": Product.objects.filter(stock__gt=0, stock__lte=5).count(), "out_of_stock": Product.objects.filter(stock__lte=0).count()},
            "vendors": VendorProfile.objects.filter(status="active").order_by("store_name"), "categories": Category.objects.filter(is_active=True).order_by("sort_order", "name"),
            "brand_options": brands, "material_options": materials, "color_options": colors, "size_options": sizes,
            "selected_colors": _json_list(form, edit_product, "colors"), "selected_sizes": _json_list(form, edit_product, "sizes"), "selected_hashtags": _json_list(form, edit_product, "hashtags"),
            "form": form, "edit_product": edit_product, "form_open": form_open,
            "product_report": {"units_sold": sales.get("quantity") or 0, "revenue": sales.get("revenue") or 0, "orders": OrderItem.objects.filter(product=edit_product).values("order_id").distinct().count() if edit_product else 0, "rating": edit_product.rating if edit_product else 0, "reviews": edit_product.reviews_count if edit_product else 0, "stock": edit_product.available_stock if edit_product else 0}}


def _control_section_context(request, section):
    """Build real, query-backed data for the new ERP inner screens."""
    if section == "applications":
        base = VendorApplication.objects.all()
        q = request.GET.get("q", "").strip(); status = request.GET.get("status", "").strip()
        if q:
            base = base.filter(Q(store_name__icontains=q) | Q(phone__icontains=q) | Q(applicant__phone__icontains=q) | Q(applicant__email__icontains=q))
        if status in {"pending", "approved", "rejected"}: base = base.filter(status=status)
        page = Paginator(base.select_related("applicant", "reviewed_by").order_by("-created_at"), 14).get_page(request.GET.get("page"))
        all_apps = VendorApplication.objects.all()
        return {"q": q, "status": status, "page": page, "stats": {"total": all_apps.count(), "pending": all_apps.filter(status="pending").count(), "approved": all_apps.filter(status="approved").count(), "rejected": all_apps.filter(status="rejected").count()}}

    if section == "categories":
        qs = Category.objects.select_related("parent").annotate(product_count=Count("products", distinct=True), child_count=Count("children", distinct=True))
        q = request.GET.get("q", "").strip(); state = request.GET.get("state", "").strip()
        if q: qs = qs.filter(Q(name__icontains=q) | Q(slug__icontains=q))
        if state == "active": qs = qs.filter(is_active=True)
        elif state == "inactive": qs = qs.filter(is_active=False)
        page = Paginator(qs.order_by("sort_order", "name"), 18).get_page(request.GET.get("page"))
        all_categories = Category.objects.all()
        return {"q": q, "state": state, "page": page, "stats": {"total": all_categories.count(), "active": all_categories.filter(is_active=True).count(), "inactive": all_categories.filter(is_active=False).count(), "with_products": all_categories.filter(products__isnull=False).distinct().count()}}

    if section == "variants":
        qs = ProductVariant.objects.select_related("product", "product__vendor")
        q = request.GET.get("q", "").strip(); stock_state = request.GET.get("stock", "").strip(); state = request.GET.get("state", "").strip()
        if q: qs = qs.filter(Q(sku__icontains=q) | Q(color__icontains=q) | Q(size__icontains=q) | Q(product__name__icontains=q) | Q(product__vendor__store_name__icontains=q))
        if state == "active": qs = qs.filter(is_active=True)
        elif state == "inactive": qs = qs.filter(is_active=False)
        if stock_state == "out": qs = qs.filter(stock=0)
        elif stock_state == "low": qs = qs.filter(stock__gt=0, stock__lte=5)
        elif stock_state == "healthy": qs = qs.filter(stock__gt=5)
        page = Paginator(qs.order_by("-updated_at", "-id"), 18).get_page(request.GET.get("page"))
        all_variants = ProductVariant.objects.all()
        return {"q": q, "stock_state": stock_state, "state": state, "page": page, "stats": {"total": all_variants.count(), "active": all_variants.filter(is_active=True).count(), "low_stock": all_variants.filter(stock__gt=0, stock__lte=5).count(), "out_of_stock": all_variants.filter(stock=0).count()}}

    if section == "orders":
        qs = Order.objects.select_related("customer")
        q = request.GET.get("q", "").strip(); status = request.GET.get("status", "").strip(); payment = request.GET.get("payment", "").strip()
        if q: qs = qs.filter(Q(order_number__icontains=q) | Q(customer__phone__icontains=q) | Q(customer__email__icontains=q))
        if status: qs = qs.filter(status=status)
        if payment: qs = qs.filter(payment_status=payment)
        page = Paginator(qs.order_by("-created_at", "-id"), 16).get_page(request.GET.get("page"))
        all_orders = Order.objects.all()
        return {"q": q, "status": status, "payment": payment, "page": page, "stats": {"total": all_orders.count(), "pending": all_orders.filter(status="pending").count(), "processing": all_orders.filter(status="processing").count(), "delivered": all_orders.filter(status="delivered").count(), "sales": all_orders.filter(payment_status="paid").aggregate(v=Sum("total"))["v"] or 0}}

    if section == "payments":
        qs = Payment.objects.select_related("order", "order__customer")
        q = request.GET.get("q", "").strip(); status = request.GET.get("status", "").strip(); method = request.GET.get("method", "").strip()
        if q: qs = qs.filter(Q(transaction_id__icontains=q) | Q(provider__icontains=q) | Q(order__order_number__icontains=q) | Q(order__customer__phone__icontains=q))
        if status: qs = qs.filter(status=status)
        if method: qs = qs.filter(method=method)
        page = Paginator(qs.order_by("-created_at", "-id"), 16).get_page(request.GET.get("page"))
        all_payments = Payment.objects.all()
        return {"q": q, "status": status, "method": method, "page": page, "stats": {"total": all_payments.count(), "paid": all_payments.filter(status="paid").count(), "pending": all_payments.filter(status="pending").count(), "failed": all_payments.filter(status="failed").count(), "volume": all_payments.filter(status="paid").aggregate(v=Sum("amount"))["v"] or 0}}

    if section == "finance":
        ledger = VendorLedgerEntry.objects.select_related("vendor", "vendor_order").order_by("-created_at", "-id")
        q = request.GET.get("q", "").strip(); entry_type = request.GET.get("type", "").strip()
        if q: ledger = ledger.filter(Q(reference__icontains=q) | Q(vendor__store_name__icontains=q))
        if entry_type: ledger = ledger.filter(entry_type=entry_type)
        ledger_page = Paginator(ledger, 12).get_page(request.GET.get("page"))
        payouts = VendorPayout.objects.select_related("vendor").order_by("-created_at", "-id")[:12]
        ledger_all = VendorLedgerEntry.objects.all(); payout_all = VendorPayout.objects.all()
        currencies = CurrencyRate.objects.filter(is_active=True).order_by("base_currency", "target_currency")[:12]
        shipping = VendorCityShipping.objects.select_related("vendor", "city").filter(is_active=True).order_by("-updated_at", "id")[:10]
        return {"q": q, "entry_type": entry_type, "ledger_page": ledger_page, "payouts": payouts, "currencies": currencies, "shipping": shipping,
                "stats": {"ledger_entries": ledger_all.count(), "sales": ledger_all.filter(entry_type="sale").aggregate(v=Sum("amount"))["v"] or 0, "commission": ledger_all.filter(entry_type="commission").aggregate(v=Sum("amount"))["v"] or 0, "pending_payouts": payout_all.filter(status__in=["pending", "approved"]).aggregate(v=Sum("amount"))["v"] or 0}}

    return {}


def render_control_partial(request, section, context=None):
    context = context or {}
    if section == "stores":
        base = _store_context(request)
        edit_id = request.GET.get("edit", "").strip()
        if edit_id:
            try:
                edit_vendor = get_object_or_404(VendorProfile.objects.select_related("owner"), pk=int(edit_id))
                base.update({"form": VendorProfileForm(instance=edit_vendor), "edit_vendor": edit_vendor, "form_open": True})
            except (TypeError, ValueError):
                pass
        return render(request, "admin/control/inner/stores.html", {**base, **context})
    if section == "products":
        base = _product_context(request)
        edit_id = request.GET.get("edit", "").strip()
        if edit_id:
            try:
                edit_product = get_object_or_404(Product.objects.select_related("vendor"), pk=int(edit_id))
                base.update({"form": ProductForm(instance=edit_product), "edit_product": edit_product, "form_open": True})
            except (TypeError, ValueError):
                pass
        return render(request, "admin/control/inner/products.html", {**base, **context})
    titles = {"applications": "طلبات المتاجر", "categories": "التصنيفات", "variants": "المتغيرات والمخزون", "orders": "الطلبات والمبيعات", "payments": "المدفوعات", "finance": "الشحن والمالية"}
    return render(request, "admin/control/inner/coming_soon.html", {"title": titles.get(section, section), "section": section, **_control_section_context(request, section), **context})


@control_access_required
@require_http_methods(["GET", "POST"])
def control_stores(request):
    edit_vendor = None; form = None; form_open = False
    if request.method == "POST":
        vendor_id = request.POST.get("vendor_id", "").strip(); edit_vendor = get_object_or_404(VendorProfile, pk=vendor_id) if vendor_id else None
        form = VendorProfileForm(request.POST, request.FILES, instance=edit_vendor); form_open = True
        if form.is_valid():
            vendor = form.save(); messages.success(request, f"تم حفظ المتجر «{vendor.store_name}».")
            return render_control_partial(request, "stores") if is_ajax(request) else redirect(CONTROL_STORES)
    elif is_ajax(request):
        edit_id = request.GET.get("edit", "").strip()
        if edit_id: edit_vendor = get_object_or_404(VendorProfile.objects.select_related("owner"), pk=edit_id); form = VendorProfileForm(instance=edit_vendor); form_open = True
        else: form = VendorProfileForm(initial={"status": "active", "commission_percent": 10})
    else:
        edit_id = request.GET.get("edit", "").strip()
        if edit_id:
            return redirect(f"{CONTROL_HOME}?screen=stores&edit={edit_id}")
        return redirect(f"{CONTROL_HOME}?screen=stores")
    return render_control_partial(request, "stores", {"form": form, "edit_vendor": edit_vendor, "form_open": form_open})


@control_access_required
@require_http_methods(["POST"])
def control_store_status(request, vendor_id, status):
    vendor = get_object_or_404(VendorProfile, pk=vendor_id)
    if status not in {"active", "pending", "suspended"}: return HttpResponse("حالة غير صالحة", status=400)
    set_vendor_status(vendor, status); messages.success(request, f"تم تحديث حالة متجر «{vendor.store_name}».")
    return render_control_partial(request, "stores") if is_ajax(request) else redirect(CONTROL_STORES)


@control_access_required
@require_http_methods(["POST"])
def control_store_delete(request, vendor_id):
    vendor = get_object_or_404(VendorProfile, pk=vendor_id)
    if vendor.products.exists() or vendor.vendor_orders.exists() or vendor.order_items.exists(): messages.error(request, "لا يمكن حذف متجر مرتبط بمنتجات أو طلبات. استخدم الإيقاف بدل الحذف.")
    else:
        name = vendor.store_name
        try: vendor.delete(); messages.success(request, f"تم حذف المتجر «{name}».")
        except ProtectedError: messages.error(request, "تعذر حذف المتجر بسبب ارتباط محمي في النظام.")
    return render_control_partial(request, "stores") if is_ajax(request) else redirect(CONTROL_STORES)


@control_access_required
@require_http_methods(["GET"])
def control_store_report(request, vendor_id):
    vendor = get_object_or_404(VendorProfile.objects.select_related("owner"), pk=vendor_id); orders = vendor.vendor_orders.all(); sales = orders.aggregate(gross=Sum("total"), commission=Sum("commission"), net=Sum("vendor_net")); products = vendor.products.annotate(sales_units=Sum("order_items__quantity"), sales_revenue=Sum("order_items__vendor_total")).order_by("-sales_units", "name")[:10]
    return render(request, "admin/control/inner/store_report.html", {"vendor": vendor, "report": {"products": vendor.products.count(), "active_products": vendor.products.filter(is_published=True).count(), "orders": orders.count(), "gross": sales["gross"] or 0, "commission": sales["commission"] or 0, "net": sales["net"] or 0}, "top_products": products})


@control_access_required
@require_http_methods(["GET", "POST"])
def control_products(request):
    edit_product = None; form = None; form_open = False
    if request.method == "POST":
        product_id = request.POST.get("product_id", "").strip(); edit_product = get_object_or_404(Product, pk=product_id) if product_id else None
        data = request.POST.copy()
        data["colors"] = json.dumps(request.POST.getlist("selected_colors"), ensure_ascii=False)
        data["sizes"] = json.dumps(request.POST.getlist("selected_sizes"), ensure_ascii=False)
        raw_tags = request.POST.get("hashtags", "")
        data["hashtags"] = json.dumps([x.strip() for x in raw_tags.replace("،", ",").split(",") if x.strip()], ensure_ascii=False)
        form = ProductForm(data, request.FILES, instance=edit_product); form_open = True
        if form.is_valid():
            product = form.save(); messages.success(request, f"تم حفظ المنتج «{product.name}».")
            return render_control_partial(request, "products") if is_ajax(request) else redirect(CONTROL_PRODUCTS)
    elif is_ajax(request):
        edit_id = request.GET.get("edit", "").strip()
        if edit_id: edit_product = get_object_or_404(Product.objects.select_related("vendor"), pk=edit_id); form = ProductForm(instance=edit_product); form_open = True
        else: form = ProductForm()
    else:
        edit_id = request.GET.get("edit", "").strip()
        if edit_id:
            return redirect(f"{CONTROL_HOME}?screen=products&edit={edit_id}")
        return redirect(f"{CONTROL_HOME}?screen=products")
    return render_control_partial(request, "products", {"form": form, "edit_product": edit_product, "form_open": form_open})


@control_access_required
@require_http_methods(["POST"])
def control_product_delete(request, product_id):
    product = get_object_or_404(Product, pk=product_id); name = product.name
    try: product.delete(); messages.success(request, f"تم حذف المنتج «{name}».")
    except ProtectedError: messages.error(request, "لا يمكن حذف المنتج لوجود طلبات مرتبطة به.")
    return render_control_partial(request, "products") if is_ajax(request) else redirect(CONTROL_PRODUCTS)


@control_access_required
@require_http_methods(["GET"])
def control_product_report(request, product_id):
    product = get_object_or_404(Product.objects.select_related("vendor").prefetch_related("categories"), pk=product_id); sales = OrderItem.objects.filter(product=product).aggregate(quantity=Sum("quantity"), revenue=Sum("vendor_total"))
    return render(request, "admin/control/inner/product_report.html", {"product": product, "report": {"units_sold": sales["quantity"] or 0, "revenue": sales["revenue"] or 0, "orders": OrderItem.objects.filter(product=product).values("order_id").distinct().count(), "stock": product.available_stock, "rating": product.rating, "reviews": product.reviews_count, "published": product.is_published}})


@control_access_required
@require_http_methods(["GET"])
def control_placeholder(request, section):
    if section not in CONTROL_PLACEHOLDER_SECTIONS: return HttpResponse("Not found", status=404)
    if is_ajax(request): return render_control_partial(request, section)
    return redirect(f"{CONTROL_HOME}?screen={section}")
