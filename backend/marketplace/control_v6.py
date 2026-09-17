from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Count, Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from catalog.forms import CategoryForm
from catalog.models import Category, Product
from communication.models import Conversation, Message, OrderChat
from finance.models import VendorLedgerEntry, VendorPayout
from orders.models import Order
from storefront.models import DesignTheme, StorefrontMedia, StorefrontSection
from vendors.forms import VendorBranchForm, VendorCategoryForm, VendorProfileForm
from vendors.models import VendorBranch, VendorCategory, VendorProfile

from .control_v5 import (
    control_orders as control_orders_v5,
    control_products as control_products_v5,
    order_detail as order_detail_v5,
    product_detail as product_detail_v5,
)
from .dashboard import dashboard_access_required

CONTROL_HOME = "/admin/dashboard/control/"
CATEGORIES_URL = f"{CONTROL_HOME}categories/"
STORES_URL = f"{CONTROL_HOME}stores/"
PRODUCTS_URL = f"{CONTROL_HOME}products/"
ORDERS_URL = f"{CONTROL_HOME}orders/"


def _ajax(request):
    return request.headers.get("X-Requested-With") == "XMLHttpRequest"


def _json_display(value):
    import json
    return json.dumps(value or {}, ensure_ascii=False, indent=2)


@dashboard_access_required
@require_http_methods(["GET", "POST"])
def control_categories(request):
    edit_id = request.GET.get("edit", "").strip()
    deleting = request.GET.get("delete", "").strip()
    if request.method == "POST":
        category_id = request.POST.get("category_id", "").strip()
        instance = get_object_or_404(Category, pk=category_id) if category_id.isdigit() else None
        form = CategoryForm(request.POST, request.FILES, instance=instance)
        if form.is_valid():
            obj = form.save()
            messages.success(request, f"تم حفظ الفئة «{obj.name}».")
            return render_category_page(request)
        return render(request, "admin/control/inner/categories_v6.html", _categories_context(request, form=form))

    if deleting.isdigit():
        obj = get_object_or_404(Category, pk=deleting)
        if obj.children.exists() or obj.products.exists():
            messages.error(request, "لا يمكن حذف الفئة وهي تحتوي على فئات فرعية أو مرتبطة بمنتجات. عطّلها أو انقل العلاقات أولًا.")
        else:
            obj.delete()
            messages.success(request, "تم حذف الفئة.")
        return render_category_page(request)

    form = CategoryForm(instance=get_object_or_404(Category, pk=edit_id)) if edit_id.isdigit() else CategoryForm()
    return render(request, "admin/control/inner/categories_v6.html", _categories_context(request, form=form))


def _categories_context(request, form=None):
    qs = Category.objects.select_related("parent").annotate(product_count=Count("products", distinct=True), child_count=Count("children", distinct=True))
    q = request.GET.get("q", "").strip()
    active = request.GET.get("active", "").strip()
    if q:
        qs = qs.filter(Q(name__icontains=q) | Q(slug__icontains=q))
    if active == "active":
        qs = qs.filter(is_active=True)
    elif active == "inactive":
        qs = qs.filter(is_active=False)
    return {
        "page": Paginator(qs.order_by("sort_order", "name"), 100).get_page(request.GET.get("page")),
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


def render_category_page(request):
    return render(request, "admin/control/inner/categories_v6.html", _categories_context(request))


@dashboard_access_required
@require_http_methods(["GET", "POST"])
def control_stores(request):
    edit_id = request.GET.get("edit", "").strip()
    if request.method == "POST":
        vendor_id = request.POST.get("vendor_id", "").strip()
        instance = get_object_or_404(VendorProfile.objects.select_related("owner"), pk=vendor_id) if vendor_id.isdigit() else None
        form = VendorProfileForm(request.POST, request.FILES, instance=instance)
        if form.is_valid():
            vendor = form.save()
            messages.success(request, f"تم حفظ متجر «{vendor.store_name}» بكل بياناته.")
            return store_detail(request, vendor.pk) if _ajax(request) else redirect(f"{STORES_URL}{vendor.pk}/detail/")
        return render(request, "admin/control/inner/store_editor_v4.html", {"form": form, "vendor": instance})

    qs = VendorProfile.objects.select_related("owner").annotate(
        product_count=Count("products", distinct=True),
        order_count=Count("vendor_orders", distinct=True),
        branch_count=Count("branches", distinct=True),
        category_count=Count("store_categories", distinct=True),
    )
    q = request.GET.get("q", "").strip()
    status = request.GET.get("status", "").strip()
    sort = request.GET.get("sort", "newest").strip()
    if q:
        qs = qs.filter(Q(store_name__icontains=q) | Q(slug__icontains=q) | Q(phone__icontains=q) | Q(owner__phone__icontains=q) | Q(owner__email__icontains=q))
    if status in {"active", "pending", "suspended"}:
        qs = qs.filter(status=status)
    if sort == "name":
        qs = qs.order_by("store_name")
    elif sort == "products":
        qs = qs.order_by("-product_count", "store_name")
    elif sort == "orders":
        qs = qs.order_by("-order_count", "store_name")
    else:
        qs = qs.order_by("-created_at")

    vendor = get_object_or_404(VendorProfile.objects.select_related("owner"), pk=int(edit_id)) if edit_id.isdigit() else None
    context = {
        "page": Paginator(qs, 16).get_page(request.GET.get("page")),
        "q": q,
        "status": status,
        "sort": sort,
        "stats": {
            "total": VendorProfile.objects.count(),
            "active": VendorProfile.objects.filter(status="active").count(),
            "pending": VendorProfile.objects.filter(status="pending").count(),
            "suspended": VendorProfile.objects.filter(status="suspended").count(),
            "products": Product.objects.count(),
            "orders": Order.objects.count(),
            "branches": VendorBranch.objects.count(),
            "categories": VendorCategory.objects.count(),
        },
        "form": VendorProfileForm(instance=vendor) if vendor else VendorProfileForm(initial={"status": "active", "commission_percent": 10}),
        "vendor": vendor,
        "form_open": bool(vendor),
    }
    if _ajax(request):
        template = "admin/control/inner/store_editor_v4.html" if vendor else "admin/control/inner/stores_v6.html"
    else:
        template = "admin/control/inner/store_editor_v4.html" if vendor else "admin/control/inner/stores_v6.html"
    return render(request, template, context)


@dashboard_access_required
@require_http_methods(["POST"])
def store_category_save(request, vendor_id):
    vendor = get_object_or_404(VendorProfile, pk=vendor_id)
    category_id = request.POST.get("category_id", "").strip()
    instance = get_object_or_404(VendorCategory, pk=category_id, vendor=vendor) if category_id.isdigit() else None
    post = request.POST.copy()
    post["vendor"] = str(vendor.pk)
    form = VendorCategoryForm(post, request.FILES, instance=instance)
    if form.is_valid():
        obj = form.save()
        messages.success(request, f"تم حفظ فئة المتجر «{obj.name}».")
    else:
        for errors in form.errors.values():
            for error in errors:
                messages.error(request, f"الفئة: {error}")
    return redirect(f"{STORES_URL}{vendor.pk}/detail/") if not _ajax(request) else store_detail(request, vendor.pk)


@dashboard_access_required
@require_http_methods(["POST"])
def store_category_delete(request, vendor_id, category_id):
    vendor = get_object_or_404(VendorProfile, pk=vendor_id)
    category = get_object_or_404(VendorCategory, pk=category_id, vendor=vendor)
    if category.children.exists() or category.products.exists():
        messages.error(request, "لا يمكن حذف فئة متجر مرتبطة بمنتجات أو فئات فرعية.")
    else:
        category.delete()
        messages.success(request, "تم حذف فئة المتجر.")
    return redirect(f"{STORES_URL}{vendor.pk}/detail/") if not _ajax(request) else store_detail(request, vendor.pk)


@dashboard_access_required
@require_http_methods(["POST"])
def store_branch_save(request, vendor_id):
    vendor = get_object_or_404(VendorProfile, pk=vendor_id)
    branch_id = request.POST.get("branch_id", "").strip()
    instance = get_object_or_404(VendorBranch, pk=branch_id, vendor=vendor) if branch_id.isdigit() else None
    post = request.POST.copy()
    post["vendor"] = str(vendor.pk)
    form = VendorBranchForm(post, request.FILES, instance=instance)
    if form.is_valid():
        branch = form.save()
        messages.success(request, f"تم حفظ فرع «{branch.name}».")
    else:
        for errors in form.errors.values():
            for error in errors:
                messages.error(request, f"الفرع: {error}")
    return redirect(f"{STORES_URL}{vendor.pk}/detail/") if not _ajax(request) else store_detail(request, vendor.pk)


@dashboard_access_required
@require_http_methods(["POST"])
def store_branch_delete(request, vendor_id, branch_id):
    vendor = get_object_or_404(VendorProfile, pk=vendor_id)
    get_object_or_404(VendorBranch, pk=branch_id, vendor=vendor).delete()
    messages.success(request, "تم حذف الفرع.")
    return redirect(f"{STORES_URL}{vendor.pk}/detail/") if not _ajax(request) else store_detail(request, vendor.pk)


@dashboard_access_required
@require_http_methods(["GET"])
def store_detail(request, vendor_id):
    vendor = get_object_or_404(VendorProfile.objects.select_related("owner"), pk=vendor_id)
    products = list(vendor.products.select_related("vendor").prefetch_related("categories", "store_categories", "variants", "image_items").order_by("-updated_at")[:40])
    orders = list(vendor.vendor_orders.select_related("order", "order__customer").order_by("-created_at")[:40])
    general_conversations = list(Conversation.objects.filter(vendor=vendor).select_related("customer", "order").prefetch_related("messages__sender").order_by("-updated_at")[:20])
    order_chats = list(OrderChat.objects.filter(vendor=vendor).select_related("order", "order__customer", "vendor_order").prefetch_related("messages__sender").order_by("-updated_at")[:20])
    theme = DesignTheme.objects.filter(vendor=vendor).first()
    sections = list(StorefrontSection.objects.filter(vendor=vendor).order_by("sort_order", "id")[:30])
    media = list(StorefrontMedia.objects.filter(vendor=vendor).order_by("sort_order", "id")[:30])
    store_categories = list(VendorCategory.objects.filter(vendor=vendor).select_related("parent").annotate(product_count=Count("products", distinct=True)).order_by("parent_id", "sort_order", "name"))
    branches = list(VendorBranch.objects.filter(vendor=vendor).order_by("-is_main", "name"))
    edit_category_id = request.GET.get("edit_category", "").strip()
    edit_branch_id = request.GET.get("edit_branch", "").strip()
    category_instance = get_object_or_404(VendorCategory, pk=edit_category_id, vendor=vendor) if edit_category_id.isdigit() else None
    branch_instance = get_object_or_404(VendorBranch, pk=edit_branch_id, vendor=vendor) if edit_branch_id.isdigit() else None
    sales = vendor.vendor_orders.aggregate(gross=Sum("total"), commission=Sum("commission"), net=Sum("vendor_net"))
    ledger = list(VendorLedgerEntry.objects.filter(vendor=vendor).order_by("-created_at")[:20])
    payouts = list(VendorPayout.objects.filter(vendor=vendor).order_by("-created_at")[:20])
    return render(request, "admin/control/inner/store_detail_v6.html", {
        "vendor": vendor,
        "products": products,
        "orders": orders,
        "conversations": general_conversations,
        "order_chats": order_chats,
        "theme": theme,
        "sections": sections,
        "media": media,
        "store_categories": store_categories,
        "branches": branches,
        "category_form": VendorCategoryForm(instance=category_instance, initial={"vendor": vendor.pk} if not category_instance else None),
        "branch_form": VendorBranchForm(instance=branch_instance, initial={"vendor": vendor.pk} if not branch_instance else None),
        "editing_category": category_instance,
        "editing_branch": branch_instance,
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
        },
        "settings_json": _json_display(vendor.settings),
        "theme_json": _json_display({"tokens": theme.tokens, "layout": theme.layout, "sections": theme.sections} if theme else {}),
        "ledger": ledger,
        "payouts": payouts,
    })


@dashboard_access_required
@require_http_methods(["GET", "POST"])
def order_customer_message(request, order_id):
    order = get_object_or_404(Order.objects.select_related("customer"), pk=order_id)
    if request.method == "POST":
        body = request.POST.get("body", "").strip()
        attachment = request.FILES.get("attachment")
        if not body and not attachment:
            messages.error(request, "اكتب رسالة أو أرفق صورة قبل الإرسال.")
        else:
            conversation, _ = Conversation.objects.get_or_create(
                order=order,
                defaults={"customer": order.customer, "subject": f"محادثة الطلب {order.order_number}"},
            )
            Message.objects.create(conversation=conversation, sender=request.user, body=body, attachment=attachment)
            conversation.is_closed = False
            conversation.save(update_fields=["is_closed", "updated_at"])
            messages.success(request, "تم إرسال الرسالة إلى محادثة العميل.")
    return order_detail_v5(request, order.pk) if _ajax(request) else redirect(f"{ORDERS_URL}{order.pk}/detail/#customer-chat")


control_products = control_products_v5
product_detail = product_detail_v5
control_orders = control_orders_v5
order_detail = order_detail_v5
