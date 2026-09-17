from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Count, Q, Sum
from django.db.models.deletion import ProtectedError
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .dashboard import dashboard_access_required
from vendors.forms import VendorProfileForm
from vendors.models import VendorApplication, VendorProfile
from vendors.services import set_vendor_status
from catalog.forms import CategoryForm, ProductForm
from catalog.models import Category, Product, ProductVariant
from orders.models import Order, Payment
from finance.models import VendorPayout, Wallet


STORE_STATUSES = {"active", "pending", "suspended"}


def _stores_context(request, form=None, edit_vendor=None, form_mode="create"):
    queryset = (
        VendorProfile.objects.select_related("owner")
        .annotate(
            product_count=Count("products", distinct=True),
            order_count=Count("vendor_orders", distinct=True),
        )
    )

    q = request.GET.get("q", "").strip()
    status = request.GET.get("status", "").strip()
    sort = request.GET.get("sort", "newest").strip()

    if q:
        queryset = queryset.filter(
            Q(store_name__icontains=q)
            | Q(slug__icontains=q)
            | Q(phone__icontains=q)
            | Q(owner__phone__icontains=q)
            | Q(owner__email__icontains=q)
            | Q(owner__first_name__icontains=q)
            | Q(owner__last_name__icontains=q)
        )
    if status in STORE_STATUSES:
        queryset = queryset.filter(status=status)

    if sort == "name":
        queryset = queryset.order_by("store_name")
    elif sort == "products":
        queryset = queryset.order_by("-product_count", "store_name")
    elif sort == "orders":
        queryset = queryset.order_by("-order_count", "store_name")
    else:
        sort = "newest"
        queryset = queryset.order_by("-created_at")

    paginator = Paginator(queryset, 15)
    page = paginator.get_page(request.GET.get("page"))

    stats = {
        "total": VendorProfile.objects.count(),
        "active": VendorProfile.objects.filter(status="active").count(),
        "pending": VendorProfile.objects.filter(status="pending").count(),
        "suspended": VendorProfile.objects.filter(status="suspended").count(),
    }

    return {
        "page": page,
        "q": q,
        "status": status,
        "sort": sort,
        "stats": stats,
        "form": form,
        "edit_vendor": edit_vendor,
        "form_mode": form_mode,
        "store_form_open": bool(form and (edit_vendor or getattr(form, "errors", None))),
    }


@dashboard_access_required
def stores(request):
    edit_vendor_id = request.GET.get("edit")
    edit_vendor = None
    form = None
    form_mode = "create"

    if request.method == "POST":
        vendor_id = request.POST.get("vendor_id") or ""
        if vendor_id:
            edit_vendor = get_object_or_404(VendorProfile, pk=vendor_id)
            form_mode = "edit"
            form = VendorProfileForm(request.POST, request.FILES, instance=edit_vendor)
        else:
            form = VendorProfileForm(request.POST, request.FILES)

        if form.is_valid():
            vendor = form.save()
            messages.success(request, f"تم حفظ المتجر «{vendor.store_name}» بنجاح.")
            return redirect("admin-control-stores")

        form_mode = "edit" if edit_vendor else "create"
    elif edit_vendor_id:
        edit_vendor = get_object_or_404(VendorProfile.objects.select_related("owner"), pk=edit_vendor_id)
        form_mode = "edit"
        form = VendorProfileForm(instance=edit_vendor)
    else:
        form = VendorProfileForm(initial={"status": "active", "commission_percent": 10})

    return render(request, "admin/control/stores.html", _stores_context(request, form, edit_vendor, form_mode))


@dashboard_access_required
@require_POST
def store_status(request, vendor_id, status):
    if status not in STORE_STATUSES:
        return redirect("admin-control-stores")
    vendor = get_object_or_404(VendorProfile, pk=vendor_id)
    set_vendor_status(vendor, status)
    messages.success(request, f"تم تغيير حالة متجر «{vendor.store_name}» إلى {vendor.get_status_display()}.")
    return redirect(request.POST.get("next") or "admin-control-stores")


@dashboard_access_required
@require_POST
def store_delete(request, vendor_id):
    vendor = get_object_or_404(VendorProfile, pk=vendor_id)
    has_products = vendor.products.exists()
    has_orders = vendor.vendor_orders.exists() or vendor.order_items.exists()

    if has_products or has_orders:
        messages.error(request, "لا يمكن حذف متجر مرتبط بمنتجات أو طلبات. استخدم «إيقاف المتجر» للحفاظ على السجل والارتباطات.")
        return redirect(request.POST.get("next") or "admin-control-stores")

    name = vendor.store_name
    try:
        vendor.delete()
    except ProtectedError:
        messages.error(request, "تعذر حذف المتجر بسبب ارتباطات محمية في النظام. تم الإبقاء عليه دون تغيير.")
    else:
        messages.success(request, f"تم حذف المتجر «{name}».")
    return redirect(request.POST.get("next") or "admin-control-stores")


def _product_context(request, form=None, edit_product=None, form_mode="create"):
    qs = Product.objects.select_related("vendor").prefetch_related("categories")
    q = request.GET.get("q", "").strip()
    status = request.GET.get("status", "").strip()
    stock = request.GET.get("stock", "").strip()
    vendor_id = request.GET.get("vendor", "").strip()
    if q:
        qs = qs.filter(Q(name__icontains=q) | Q(sku__icontains=q) | Q(description__icontains=q))
    if status == "published":
        qs = qs.filter(is_published=True)
    elif status == "hidden":
        qs = qs.filter(is_published=False)
    elif status == "trending":
        qs = qs.filter(is_trending=True)
    if stock == "out":
        qs = qs.filter(stock__lte=0)
    elif stock == "low":
        qs = qs.filter(stock__gt=0, stock__lte=5)
    if vendor_id.isdigit():
        qs = qs.filter(vendor_id=int(vendor_id))
    page = Paginator(qs.order_by("-updated_at", "-id"), 20).get_page(request.GET.get("page"))
    all_products = Product.objects.all()
    return {
        "page": page,
        "products": page.object_list,
        "vendors": VendorProfile.objects.order_by("store_name"),
        "categories": Category.objects.filter(is_active=True).order_by("sort_order", "name"),
        "filters": {"q": q, "status": status, "stock": stock, "vendor": vendor_id},
        "stats": {
            "total": all_products.count(),
            "published": all_products.filter(is_published=True).count(),
            "hidden": all_products.filter(is_published=False).count(),
            "low_stock": all_products.filter(stock__gt=0, stock__lte=5).count(),
            "out_of_stock": all_products.filter(stock__lte=0).count(),
        },
        "form": form,
        "edit_product": edit_product,
        "form_mode": form_mode,
        "product_form_open": bool(form and (edit_product or getattr(form, "errors", None))),
    }


@dashboard_access_required
def products(request):
    edit_product = None
    form = None
    form_mode = "create"
    edit_product_id = request.GET.get("edit")
    if request.method == "POST":
        product_id = request.POST.get("product_id") or ""
        if product_id:
            edit_product = get_object_or_404(Product, pk=product_id)
            form_mode = "edit"
            form = ProductForm(request.POST, request.FILES, instance=edit_product)
        else:
            form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            product = form.save()
            messages.success(request, f"تم حفظ المنتج «{product.name}».")
            return redirect("admin-control-products")
        form_mode = "edit" if edit_product else "create"
    elif edit_product_id:
        edit_product = get_object_or_404(Product, pk=edit_product_id)
        form_mode = "edit"
        form = ProductForm(instance=edit_product)
    else:
        form = ProductForm()
    return render(request, "admin/control/products.html", _product_context(request, form, edit_product, form_mode))


@dashboard_access_required
def categories(request):
    edit_category = None
    form = None
    form_mode = "create"
    edit_id = request.GET.get("edit")
    if request.method == "POST":
        category_id = request.POST.get("category_id") or ""
        if category_id:
            edit_category = get_object_or_404(Category, pk=category_id)
            form_mode = "edit"
            form = CategoryForm(request.POST, request.FILES, instance=edit_category)
        else:
            form = CategoryForm(request.POST, request.FILES)
        if form.is_valid():
            category = form.save()
            messages.success(request, f"تم حفظ التصنيف «{category.name}».")
            return redirect("admin-control-categories")
        form_mode = "edit" if edit_category else "create"
    elif edit_id:
        edit_category = get_object_or_404(Category, pk=edit_id)
        form_mode = "edit"
        form = CategoryForm(instance=edit_category)
    else:
        form = CategoryForm()
    q = request.GET.get("q", "").strip()
    qs = Category.objects.select_related("parent").annotate(product_count=Count("products", distinct=True)).order_by("sort_order", "name", "id")
    if q:
        qs = qs.filter(name__icontains=q)
    page = Paginator(qs, 30).get_page(request.GET.get("page"))
    return render(request, "admin/control/categories.html", {
        "page": page,
        "q": q,
        "form": form,
        "edit_category": edit_category,
        "form_mode": form_mode,
        "category_form_open": bool(form and (edit_category or getattr(form, "errors", None))),
        "stats": {
            "total": Category.objects.count(),
            "active": Category.objects.filter(is_active=True).count(),
            "products": Product.objects.count(),
        },
    })


@dashboard_access_required
def variants(request):
    q = request.GET.get("q", "").strip()
    qs = ProductVariant.objects.select_related("product", "product__vendor").order_by("-updated_at", "-id")
    if q:
        qs = qs.filter(Q(sku__icontains=q) | Q(product__name__icontains=q) | Q(color__icontains=q) | Q(size__icontains=q))
    page = Paginator(qs, 30).get_page(request.GET.get("page"))
    return render(request, "admin/control/variants.html", {
        "page": page,
        "q": q,
        "stats": {
            "total": ProductVariant.objects.count(),
            "active": ProductVariant.objects.filter(is_active=True).count(),
            "stock": ProductVariant.objects.aggregate(v=Sum("stock"))["v"] or 0,
        },
    })


@dashboard_access_required
def applications(request):
    q = request.GET.get("q", "").strip()
    status = request.GET.get("status", "pending").strip()
    qs = VendorApplication.objects.select_related("applicant").order_by("-created_at")
    if q:
        qs = qs.filter(Q(store_name__icontains=q) | Q(phone__icontains=q) | Q(applicant__phone__icontains=q))
    if status in {"pending", "approved", "rejected"}:
        qs = qs.filter(status=status)
    page = Paginator(qs, 20).get_page(request.GET.get("page"))
    return render(request, "admin/control/module_list.html", {
        "module": "طلبات المتاجر", "eyebrow": "STORE APPLICATIONS", "icon": "!", "page": page,
        "columns": [("store_name", "المتجر"), ("phone", "الهاتف"), ("status", "الحالة"), ("created_at", "التاريخ")],
        "empty": "لا توجد طلبات تجار بهذا الفلتر.",
        "stats": [("قيد المراجعة", VendorApplication.objects.filter(status="pending").count()), ("مقبول", VendorApplication.objects.filter(status="approved").count()), ("مرفوض", VendorApplication.objects.filter(status="rejected").count())],
    })


@dashboard_access_required
def orders(request):
    q = request.GET.get("q", "").strip()
    status = request.GET.get("status", "").strip()
    qs = Order.objects.select_related("customer").order_by("-created_at")
    if q:
        qs = qs.filter(Q(order_number__icontains=q) | Q(customer__phone__icontains=q) | Q(customer__email__icontains=q))
    if status:
        qs = qs.filter(status=status)
    page = Paginator(qs, 25).get_page(request.GET.get("page"))
    return render(request, "admin/control/orders.html", {"page": page, "q": q, "status": status, "statuses": Order.Status.choices,
        "stats": {"total": Order.objects.count(), "pending": Order.objects.filter(status="pending").count(), "processing": Order.objects.filter(status="processing").count(), "delivered": Order.objects.filter(status="delivered").count()}})


@dashboard_access_required
def payments(request):
    qs = Payment.objects.select_related("order", "order__customer").order_by("-created_at")
    q = request.GET.get("q", "").strip()
    if q:
        qs = qs.filter(Q(transaction_id__icontains=q) | Q(order__order_number__icontains=q) | Q(provider__icontains=q))
    page = Paginator(qs, 25).get_page(request.GET.get("page"))
    return render(request, "admin/control/module_list.html", {"module": "المدفوعات", "eyebrow": "PAYMENTS", "icon": "$", "page": page,
        "columns": [("transaction_id", "المعاملة"), ("order", "الطلب"), ("amount", "المبلغ"), ("status", "الحالة"), ("created_at", "التاريخ")],
        "empty": "لا توجد مدفوعات.", "stats": [("الإجمالي", Payment.objects.count()), ("مدفوع", Payment.objects.filter(status="paid").count()), ("معلّق", Payment.objects.filter(status="pending").count())]})


@dashboard_access_required
def finance(request):
    return render(request, "admin/control/finance.html", {
        "wallet_balance": Wallet.objects.aggregate(v=Sum("balance"))["v"] or 0,
        "wallets": Wallet.objects.count(),
        "pending_payouts": VendorPayout.objects.filter(status__in=["pending", "approved"]).count(),
        "payout_total": VendorPayout.objects.filter(status__in=["pending", "approved"]).aggregate(v=Sum("amount"))["v"] or 0,
        "paid_payouts": VendorPayout.objects.filter(status="paid").aggregate(v=Sum("amount"))["v"] or 0,
    })
