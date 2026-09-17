import json
from decimal import Decimal

from django.contrib import messages
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Count, Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from catalog.forms import CategoryForm, ProductForm
from catalog.models import Category, Product, ProductVariant
from communication.models import Conversation, Message
from finance.models import CurrencyRate, VendorCityShipping, VendorLedgerEntry, VendorPayout
from orders.models import Order, Payment, VendorOrder
from storefront.forms import DesignThemeForm, StorefrontMediaForm, StorefrontSectionForm
from storefront.models import DesignTheme, StorefrontMedia, StorefrontSection
from vendors.forms import VendorApplicationReviewForm, VendorBranchForm, VendorCategoryForm, VendorProfileForm
from vendors.models import BranchInventory, VendorApplication, VendorBranch, VendorCategory, VendorProfile
from marketplace.dashboard import dashboard_access_required

from . import control_v9 as base

CONTROL_HOME = "/admin/dashboard/control/"
STORES_URL = f"{CONTROL_HOME}stores/"
PRODUCTS_URL = f"{CONTROL_HOME}products/"
ORDERS_URL = f"{CONTROL_HOME}orders/"
CATEGORIES_URL = f"{CONTROL_HOME}categories/"
INVENTORY_URL = f"{CONTROL_HOME}inventory/"
APPLICATIONS_URL = f"{CONTROL_HOME}applications/"
PAYMENTS_URL = f"{CONTROL_HOME}payments/"
FINANCE_URL = f"{CONTROL_HOME}finance/"

_ajax = base._ajax
_product = base._product
_save_variants = base._save_variants
_json = base._json
control_products = base.control_products
product_detail = base.product_detail
control_stores = base.control_stores
order_detail = base.order_detail
order_status = base.order_status
order_customer_message = base.order_customer_message
order_chat_message = base.order_chat_message
order_chat_open = base.order_chat_open
control_orders = base.control_orders


def _product_editor_context(form, product=None):
    global_ids = list(product.categories.values_list("pk", flat=True)) if product else []
    store_ids = list(product.store_categories.values_list("pk", flat=True)) if product else []
    if getattr(form, "is_bound", False):
        global_ids = [int(v) for v in form.data.getlist("categories") if str(v).isdigit()]
        store_ids = [int(v) for v in form.data.getlist("store_categories") if str(v).isdigit()]
    return {
        "form": form,
        "product": product,
        "variants": list(product.variants.all().order_by("id")) if product else [],
        "images": list(product.image_items.all().order_by("sort_order", "id")) if product else [],
        "global_categories": form.fields["categories"].queryset,
        "store_categories": form.fields["store_categories"].queryset,
        "global_category_ids": global_ids,
        "store_category_ids": store_ids,
        "system": {
            "reserved_stock": product.reserved_stock if product else 0,
            "sold_count": product.sold_count if product else 0,
            "reviews_count": product.reviews_count if product else 0,
            "rating": product.rating if product else 0,
        },
    }


@dashboard_access_required
@require_http_methods(["GET", "POST"])
def control_categories(request):
    if request.method == "POST":
        category_id = request.POST.get("category_id", "").strip()
        instance = get_object_or_404(Category, pk=category_id) if category_id.isdigit() else None
        form = CategoryForm(request.POST, request.FILES, instance=instance)
        if form.is_valid():
            obj = form.save()
            messages.success(request, f"تم حفظ الفئة «{obj.name}».")
            if _ajax(request):
                return render(request, "admin/control/inner/categories_v10.html", _categories_context(request))
            return redirect(CATEGORIES_URL)
        return render(request, "admin/control/inner/categories_v10.html", _categories_context(request, form=form))

    delete_id = request.GET.get("delete", "").strip()
    if delete_id.isdigit():
        obj = get_object_or_404(Category, pk=delete_id)
        if obj.children.exists() or obj.products.exists():
            messages.error(request, "لا يمكن حذف الفئة قبل نقل المنتجات والفئات الفرعية. يمكنك تعطيلها بدلًا من حذفها.")
        else:
            obj.delete()
            messages.success(request, "تم حذف الفئة.")
        return redirect(CATEGORIES_URL)

    edit_id = request.GET.get("edit", "").strip()
    form = CategoryForm(instance=get_object_or_404(Category, pk=edit_id)) if edit_id.isdigit() else CategoryForm()
    return render(request, "admin/control/inner/categories_v10.html", _categories_context(request, form=form))


def _category_rows(categories):
    by_parent = {}
    for item in categories:
        by_parent.setdefault(item.parent_id, []).append(item)
    rows = []

    def walk(parent_id, depth):
        for item in by_parent.get(parent_id, []):
            item.tree_depth = depth
            rows.append(item)
            walk(item.pk, depth + 1)

    walk(None, 0)
    return rows


def _categories_context(request, form=None):
    qs = Category.objects.select_related("parent").annotate(
        product_count=Count("products", distinct=True),
        child_count=Count("children", distinct=True),
    )
    q = request.GET.get("q", "").strip()
    active = request.GET.get("active", "").strip()
    if q:
        qs = qs.filter(Q(name__icontains=q) | Q(slug__icontains=q))
    if active == "active":
        qs = qs.filter(is_active=True)
    elif active == "inactive":
        qs = qs.filter(is_active=False)
    all_rows = list(qs.order_by("sort_order", "name", "id"))
    return {
        "rows": _category_rows(all_rows),
        "form": form or CategoryForm(),
        "edit_id": request.GET.get("edit", ""),
        "q": q,
        "active": active,
        "stats": {
            "total": Category.objects.count(),
            "active": Category.objects.filter(is_active=True).count(),
            "roots": Category.objects.filter(parent__isnull=True).count(),
            "products": Product.objects.count(),
        },
    }


@dashboard_access_required
@require_http_methods(["GET", "POST"])
def store_detail(request, vendor_id):
    vendor = get_object_or_404(VendorProfile.objects.select_related("owner"), pk=vendor_id)
    products = list(vendor.products.select_related("vendor").prefetch_related("categories", "store_categories", "variants", "image_items").order_by("-updated_at")[:50])
    orders = list(vendor.vendor_orders.select_related("order", "order__customer").order_by("-created_at")[:50])
    conversations = list(Conversation.objects.filter(vendor=vendor).select_related("customer", "order").prefetch_related("messages__sender").order_by("-updated_at")[:20])
    theme = DesignTheme.objects.filter(vendor=vendor).first()
    sections = list(StorefrontSection.objects.filter(vendor=vendor).order_by("sort_order", "id")[:30])
    media = list(StorefrontMedia.objects.filter(vendor=vendor).order_by("sort_order", "id")[:30])
    store_categories = list(VendorCategory.objects.filter(vendor=vendor).select_related("parent").annotate(product_count=Count("products", distinct=True)).order_by("parent_id", "sort_order", "name"))
    branches = list(VendorBranch.objects.filter(vendor=vendor).order_by("-is_main", "name"))
    inventory = list(BranchInventory.objects.filter(branch__vendor=vendor).select_related("branch", "product", "variant").order_by("branch__name", "product__name")[:100])
    ledger = list(VendorLedgerEntry.objects.filter(vendor=vendor).order_by("-created_at")[:20])
    payouts = list(VendorPayout.objects.filter(vendor=vendor).order_by("-created_at")[:20])
    sales = vendor.vendor_orders.aggregate(gross=Sum("total"), commission=Sum("commission"), net=Sum("vendor_net"))

    edit_category_id = request.GET.get("edit_category", "").strip()
    edit_branch_id = request.GET.get("edit_branch", "").strip()
    edit_section_id = request.GET.get("edit_section", "").strip()
    edit_media_id = request.GET.get("edit_media", "").strip()
    category_instance = get_object_or_404(VendorCategory, pk=edit_category_id, vendor=vendor) if edit_category_id.isdigit() else None
    branch_instance = get_object_or_404(VendorBranch, pk=edit_branch_id, vendor=vendor) if edit_branch_id.isdigit() else None
    section_instance = get_object_or_404(StorefrontSection, pk=edit_section_id, vendor=vendor) if edit_section_id.isdigit() else None
    media_instance = get_object_or_404(StorefrontMedia, pk=edit_media_id, vendor=vendor) if edit_media_id.isdigit() else None
    return render(request, "admin/control/inner/store_detail_v10.html", {
        "vendor": vendor,
        "products": products,
        "orders": orders,
        "conversations": conversations,
        "theme": theme,
        "sections": sections,
        "media": media,
        "store_categories": store_categories,
        "branches": branches,
        "inventory": inventory,
        "ledger": ledger,
        "payouts": payouts,
        "category_form": VendorCategoryForm(instance=category_instance, initial={"vendor": vendor.pk} if not category_instance else None),
        "branch_form": VendorBranchForm(instance=branch_instance, initial={"vendor": vendor.pk} if not branch_instance else None),
        "theme_form": DesignThemeForm(instance=theme),
        "section_form": StorefrontSectionForm(instance=section_instance),
        "media_form": StorefrontMediaForm(instance=media_instance),
        "editing_category": category_instance,
        "editing_branch": branch_instance,
        "editing_section": section_instance,
        "editing_media": media_instance,
        "report": {
            "products": vendor.products.count(),
            "active_products": vendor.products.filter(is_published=True).count(),
            "orders": vendor.vendor_orders.count(),
            "gross": sales["gross"] or 0,
            "commission": sales["commission"] or 0,
            "net": sales["net"] or 0,
            "commission_percent": vendor.commission_percent,
            "branches": vendor.branches.count(),
            "store_categories": vendor.store_categories.count(),
            "inventory_rows": BranchInventory.objects.filter(branch__vendor=vendor).count(),
            "inventory_available": sum(row.available_stock for row in inventory),
        },
        "settings_json": _json(vendor.settings),
        "theme_json": _json({"tokens": theme.tokens, "layout": theme.layout, "sections": theme.sections} if theme else {}),
    })


@dashboard_access_required
@require_http_methods(["POST"])
def store_design_save(request, vendor_id):
    vendor = get_object_or_404(VendorProfile, pk=vendor_id)
    theme = DesignTheme.objects.filter(vendor=vendor).first()
    form = DesignThemeForm(request.POST, instance=theme)
    if form.is_valid():
        obj = form.save(commit=False)
        obj.vendor = vendor
        obj.owner = request.user
        obj.is_global = False
        obj.save()
        messages.success(request, "تم حفظ تصميم المتجر.")
    else:
        messages.error(request, "تعذر حفظ التصميم. تحقق من حقول JSON.")
    return store_detail(request, vendor.pk) if _ajax(request) else redirect(f"{STORES_URL}{vendor.pk}/detail/")


@dashboard_access_required
@require_http_methods(["POST"])
def store_section_save(request, vendor_id):
    vendor = get_object_or_404(VendorProfile, pk=vendor_id)
    section_id = request.POST.get("section_id", "").strip()
    instance = get_object_or_404(StorefrontSection, pk=section_id, vendor=vendor) if section_id.isdigit() else None
    form = StorefrontSectionForm(request.POST, instance=instance)
    if form.is_valid():
        obj = form.save(commit=False)
        obj.vendor = vendor
        obj.owner = request.user
        obj.save()
        messages.success(request, "تم حفظ قسم التصميم.")
    else:
        messages.error(request, "تعذر حفظ قسم التصميم. تحقق من JSON.")
    return store_detail(request, vendor.pk) if _ajax(request) else redirect(f"{STORES_URL}{vendor.pk}/detail/")


@dashboard_access_required
@require_http_methods(["POST"])
def store_section_delete(request, vendor_id, section_id):
    vendor = get_object_or_404(VendorProfile, pk=vendor_id)
    get_object_or_404(StorefrontSection, pk=section_id, vendor=vendor).delete()
    messages.success(request, "تم حذف قسم التصميم.")
    return store_detail(request, vendor.pk) if _ajax(request) else redirect(f"{STORES_URL}{vendor.pk}/detail/")


@dashboard_access_required
@require_http_methods(["POST"])
def store_media_save(request, vendor_id):
    vendor = get_object_or_404(VendorProfile, pk=vendor_id)
    media_id = request.POST.get("media_id", "").strip()
    instance = get_object_or_404(StorefrontMedia, pk=media_id, vendor=vendor) if media_id.isdigit() else None
    form = StorefrontMediaForm(request.POST, request.FILES, instance=instance)
    if form.is_valid():
        obj = form.save(commit=False)
        obj.vendor = vendor
        obj.save()
        messages.success(request, "تم حفظ صورة/وسائط المتجر.")
    else:
        messages.error(request, "تعذر حفظ الوسائط. اختر صورة وأدخل البيانات الصحيحة.")
    return store_detail(request, vendor.pk) if _ajax(request) else redirect(f"{STORES_URL}{vendor.pk}/detail/")


@dashboard_access_required
@require_http_methods(["POST"])
def store_media_delete(request, vendor_id, media_id):
    vendor = get_object_or_404(VendorProfile, pk=vendor_id)
    get_object_or_404(StorefrontMedia, pk=media_id, vendor=vendor).delete()
    messages.success(request, "تم حذف وسائط المتجر.")
    return store_detail(request, vendor.pk) if _ajax(request) else redirect(f"{STORES_URL}{vendor.pk}/detail/")


@dashboard_access_required
@require_http_methods(["POST"])
def store_category_save(request, vendor_id):
    vendor = get_object_or_404(VendorProfile, pk=vendor_id)
    category_id = request.POST.get("category_id", "").strip()
    instance = get_object_or_404(VendorCategory, pk=category_id, vendor=vendor) if category_id.isdigit() else None
    data = request.POST.copy(); data["vendor"] = str(vendor.pk)
    form = VendorCategoryForm(data, request.FILES, instance=instance)
    if form.is_valid():
        obj = form.save()
        messages.success(request, f"تم حفظ فئة المتجر «{obj.name}».")
    else:
        for error_list in form.errors.values():
            for error in error_list: messages.error(request, f"الفئة: {error}")
    return store_detail(request, vendor.pk) if _ajax(request) else redirect(f"{STORES_URL}{vendor.pk}/detail/")


@dashboard_access_required
@require_http_methods(["POST"])
def store_category_delete(request, vendor_id, category_id):
    vendor = get_object_or_404(VendorProfile, pk=vendor_id)
    category = get_object_or_404(VendorCategory, pk=category_id, vendor=vendor)
    if category.children.exists() or category.products.exists():
        messages.error(request, "لا يمكن حذف الفئة وهي مرتبطة بفئات فرعية أو منتجات.")
    else:
        category.delete(); messages.success(request, "تم حذف فئة المتجر.")
    return store_detail(request, vendor.pk) if _ajax(request) else redirect(f"{STORES_URL}{vendor.pk}/detail/")


@dashboard_access_required
@require_http_methods(["POST"])
def store_branch_save(request, vendor_id):
    vendor = get_object_or_404(VendorProfile, pk=vendor_id)
    branch_id = request.POST.get("branch_id", "").strip()
    instance = get_object_or_404(VendorBranch, pk=branch_id, vendor=vendor) if branch_id.isdigit() else None
    data = request.POST.copy(); data["vendor"] = str(vendor.pk)
    form = VendorBranchForm(data, instance=instance)
    if form.is_valid():
        branch = form.save(); messages.success(request, f"تم حفظ الفرع «{branch.name}».")
    else:
        for error_list in form.errors.values():
            for error in error_list: messages.error(request, f"الفرع: {error}")
    return store_detail(request, vendor.pk) if _ajax(request) else redirect(f"{STORES_URL}{vendor.pk}/detail/")


@dashboard_access_required
@require_http_methods(["POST"])
def store_branch_delete(request, vendor_id, branch_id):
    vendor = get_object_or_404(VendorProfile, pk=vendor_id)
    get_object_or_404(VendorBranch, pk=branch_id, vendor=vendor).delete()
    messages.success(request, "تم حذف الفرع.")
    return store_detail(request, vendor.pk) if _ajax(request) else redirect(f"{STORES_URL}{vendor.pk}/detail/")


@dashboard_access_required
@require_http_methods(["GET", "POST"])
def control_inventory(request):
    if request.method == "POST":
        branch_id = request.POST.get("branch_id", "").strip()
        product_id = request.POST.get("product_id", "").strip()
        variant_id = request.POST.get("variant_id", "").strip()
        branch = get_object_or_404(VendorBranch, pk=branch_id)
        product = get_object_or_404(Product, pk=product_id, vendor=branch.vendor)
        variant = get_object_or_404(ProductVariant, pk=variant_id, product=product) if variant_id.isdigit() else None
        try:
            stock = max(0, int(request.POST.get("stock", "0") or 0))
            reserved = max(0, int(request.POST.get("reserved_stock", "0") or 0))
        except (TypeError, ValueError):
            messages.error(request, "المخزون يجب أن يكون رقمًا صحيحًا.")
            return store_detail(request, branch.vendor_id) if _ajax(request) else redirect(INVENTORY_URL)
        row, _ = BranchInventory.objects.get_or_create(branch=branch, product=product, variant=variant)
        row.stock = stock
        row.reserved_stock = min(reserved, stock)
        row.save()
        messages.success(request, "تم تحديث مخزون الفرع.")
        return store_detail(request, branch.vendor_id) if _ajax(request) else redirect(INVENTORY_URL)

    qs = Product.objects.select_related("vendor").prefetch_related("variants", "branch_inventory__branch")
    q = request.GET.get("q", "").strip(); vendor_id = request.GET.get("vendor", "").strip(); state = request.GET.get("state", "").strip()
    if q: qs = qs.filter(Q(name__icontains=q) | Q(sku__icontains=q) | Q(vendor__store_name__icontains=q))
    if vendor_id.isdigit(): qs = qs.filter(vendor_id=vendor_id)
    if state == "out": qs = qs.filter(stock=0)
    elif state == "low": qs = qs.filter(stock__gt=0, stock__lte=5)
    return render(request, "admin/control/inner/inventory_v10.html", {
        "page": Paginator(qs.order_by("stock", "name"), 24).get_page(request.GET.get("page")),
        "q": q,
        "vendor_id": vendor_id,
        "state": state,
        "vendors": VendorProfile.objects.filter(status="active").order_by("store_name"),
    })


@dashboard_access_required
@require_http_methods(["GET"])
def control_applications(request):
    qs = VendorApplication.objects.select_related("applicant", "reviewed_by")
    q = request.GET.get("q", "").strip(); status = request.GET.get("status", "").strip()
    if q:
        qs = qs.filter(Q(store_name__icontains=q) | Q(phone__icontains=q) | Q(applicant__phone__icontains=q) | Q(applicant__email__icontains=q))
    if status in {"pending", "approved", "rejected"}: qs = qs.filter(status=status)
    return render(request, "admin/control/inner/applications_v10.html", {
        "page": Paginator(qs.order_by("-created_at"), 20).get_page(request.GET.get("page")),
        "q": q, "status": status,
        "stats": {"total": VendorApplication.objects.count(), "pending": VendorApplication.objects.filter(status="pending").count(), "approved": VendorApplication.objects.filter(status="approved").count(), "rejected": VendorApplication.objects.filter(status="rejected").count()},
    })


@dashboard_access_required
@require_http_methods(["POST"])
def application_review(request, application_id):
    application = get_object_or_404(VendorApplication, pk=application_id)
    action = request.POST.get("action", "").strip()
    if action not in {"approve", "reject"}:
        messages.error(request, "قرار المراجعة غير صالح.")
        return control_applications(request)
    form = VendorApplicationReviewForm(request.POST, instance=application)
    if form.is_valid():
        obj = form.save(commit=False)
        obj.status = "approved" if action == "approve" else "rejected"
        obj.reviewed_by = request.user
        obj.reviewed_at = timezone.now()
        obj.save()
        messages.success(request, "تم تحديث طلب المتجر.")
    else:
        messages.error(request, "تعذر حفظ ملاحظة المراجعة.")
    return control_applications(request)


@dashboard_access_required
@require_http_methods(["GET"])
def control_payments(request):
    qs = Payment.objects.select_related("order", "order__customer").order_by("-created_at", "-id")
    q = request.GET.get("q", "").strip(); status = request.GET.get("status", "").strip()
    if q: qs = qs.filter(Q(transaction_id__icontains=q) | Q(provider__icontains=q) | Q(order__order_number__icontains=q) | Q(order__customer__phone__icontains=q))
    if status: qs = qs.filter(status=status)
    return render(request, "admin/control/inner/payments_v10.html", {
        "page": Paginator(qs, 24).get_page(request.GET.get("page")), "q": q, "status": status,
        "stats": {"total": Payment.objects.count(), "paid": Payment.objects.filter(status="paid").count(), "pending": Payment.objects.filter(status="pending").count(), "failed": Payment.objects.filter(status="failed").count(), "volume": Payment.objects.filter(status="paid").aggregate(v=Sum("amount"))["v"] or Decimal("0")},
    })


@dashboard_access_required
@require_http_methods(["GET"])
def control_finance(request):
    ledger = VendorLedgerEntry.objects.select_related("vendor", "vendor_order").order_by("-created_at", "-id")
    q = request.GET.get("q", "").strip(); entry_type = request.GET.get("type", "").strip()
    if q: ledger = ledger.filter(Q(reference__icontains=q) | Q(vendor__store_name__icontains=q))
    if entry_type: ledger = ledger.filter(entry_type=entry_type)
    return render(request, "admin/control/inner/finance_v10.html", {
        "ledger_page": Paginator(ledger, 20).get_page(request.GET.get("page")), "q": q, "entry_type": entry_type,
        "payouts": VendorPayout.objects.select_related("vendor").order_by("-created_at")[:30],
        "currencies": CurrencyRate.objects.filter(is_active=True).order_by("base_currency", "target_currency")[:30],
        "shipping": VendorCityShipping.objects.select_related("vendor", "city").filter(is_active=True).order_by("-updated_at")[:30],
        "stats": {
            "sales": VendorLedgerEntry.objects.filter(entry_type="sale").aggregate(v=Sum("amount"))["v"] or Decimal("0"),
            "commission": VendorLedgerEntry.objects.filter(entry_type="commission").aggregate(v=Sum("amount"))["v"] or Decimal("0"),
            "pending_payouts": VendorPayout.objects.filter(status__in=["pending", "approved"]).aggregate(v=Sum("amount"))["v"] or Decimal("0"),
        },
    })


@dashboard_access_required
@require_http_methods(["GET"])
def control_variants(request):
    qs = ProductVariant.objects.select_related("product", "product__vendor").order_by("product__name", "sku")
    q = request.GET.get("q", "").strip()
    if q: qs = qs.filter(Q(sku__icontains=q) | Q(color__icontains=q) | Q(size__icontains=q) | Q(product__name__icontains=q))
    return render(request, "admin/control/inner/variants_v10.html", {"page": Paginator(qs, 30).get_page(request.GET.get("page")), "q": q})
