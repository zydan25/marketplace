import json

from django.contrib import messages
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Count, Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from catalog.forms import CategoryForm, ProductForm, ProductVariantForm
from catalog.models import Category, Product, ProductImage, ProductVariant
from communication.models import Conversation, Message, OrderChat, OrderChatMessage
from finance.models import VendorLedgerEntry, VendorPayout
from orders.models import Order, OrderItem, OrderStatusHistory, VendorOrder
from storefront.models import DesignTheme, StorefrontMedia, StorefrontSection
from vendors.forms import VendorBranchForm, VendorCategoryForm, VendorProfileForm
from vendors.models import BranchInventory, VendorBranch, VendorCategory, VendorProfile
from marketplace.dashboard import dashboard_access_required

CONTROL_HOME = "/admin/dashboard/control/"
STORES_URL = f"{CONTROL_HOME}stores/"
PRODUCTS_URL = f"{CONTROL_HOME}products/"
ORDERS_URL = f"{CONTROL_HOME}orders/"
CATEGORIES_URL = f"{CONTROL_HOME}categories/"
INVENTORY_URL = f"{CONTROL_HOME}inventory/"


def _ajax(request):
    return request.headers.get("X-Requested-With") == "XMLHttpRequest"


def _json(value):
    try:
        return json.dumps(value if value is not None else {}, ensure_ascii=False, indent=2)
    except (TypeError, ValueError):
        return str(value or "")


def _render_or_redirect(request, url, template, context):
    return render(request, template, context) if _ajax(request) else redirect(url)


def _product_queryset():
    return Product.objects.select_related("vendor", "vendor__owner").prefetch_related(
        "categories", "store_categories", "variants", "image_items"
    )


def _product(pk):
    return get_object_or_404(_product_queryset(), pk=pk)


def _save_variants(request, product):
    ids = request.POST.getlist("variant_id")
    skus = request.POST.getlist("variant_sku")
    colors = request.POST.getlist("variant_color")
    sizes = request.POST.getlist("variant_size")
    prices = request.POST.getlist("variant_price_override")
    stocks = request.POST.getlist("variant_stock")
    actives = request.POST.getlist("variant_active")
    deletes = set(request.POST.getlist("variant_delete"))
    total = max(len(ids), len(skus), len(colors), len(sizes), len(prices), len(stocks), len(actives), 0)
    existing = {str(obj.pk): obj for obj in product.variants.all()}
    errors = []
    for i in range(total):
        variant_id = ids[i] if i < len(ids) else ""
        payload = {
            "sku": skus[i] if i < len(skus) else "",
            "color": colors[i] if i < len(colors) else "",
            "size": sizes[i] if i < len(sizes) else "",
            "price_override": prices[i] if i < len(prices) and prices[i] else None,
            "stock": stocks[i] if i < len(stocks) and stocks[i] else 0,
            "is_active": (actives[i] if i < len(actives) else "1") not in {"0", "false", "off"},
        }
        if variant_id in deletes and variant_id in existing:
            existing[variant_id].delete()
            continue
        blank_new = not variant_id and not any([
            payload["sku"], payload["color"], payload["size"], payload["price_override"], str(payload["stock"]) not in {"", "0"}
        ])
        if blank_new:
            continue
        form = ProductVariantForm(payload, instance=existing.get(variant_id) or ProductVariant(product=product))
        if not form.is_valid():
            errors.append(f"المتغير رقم {i + 1}: {form.errors.as_text()}")
            continue
        obj = form.save(commit=False)
        obj.product = product
        obj.save()
    return errors


@dashboard_access_required
@require_http_methods(["GET", "POST"])
def control_products(request):
    if request.method == "POST":
        product_id = request.POST.get("product_id", "").strip()
        product = _product(product_id) if product_id.isdigit() else None
        form = ProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            with transaction.atomic():
                product = form.save()
                delete_ids = [int(v) for v in request.POST.getlist("delete_image") if str(v).isdigit()]
                if delete_ids:
                    ProductImage.objects.filter(product=product, pk__in=delete_ids).delete()
                for upload in request.FILES.getlist("gallery_images"):
                    ProductImage.objects.create(product=product, image=upload, alt_text=product.name)
                errors = _save_variants(request, product)
                if errors:
                    transaction.set_rollback(True)
                else:
                    messages.success(request, f"تم حفظ المنتج «{product.name}» بكل بياناته وعلاقاته.")
                    if _ajax(request):
                        return product_detail(request, product.pk)
                    return redirect(f"{PRODUCTS_URL}{product.pk}/detail/")
            for error in errors:
                form.add_error(None, error)
        return render(request, "admin/control/inner/product_editor_v4.html", _product_editor_context(form, product))

    edit_id = request.GET.get("edit", "").strip()
    product = _product(edit_id) if edit_id.isdigit() else None
    if request.path.rstrip("/").endswith("/new") or product:
        return render(request, "admin/control/inner/product_editor_v4.html", _product_editor_context(ProductForm(instance=product) if product else ProductForm(), product))

    qs = _product_queryset()
    q = request.GET.get("q", "").strip()
    vendor_id = request.GET.get("vendor", "").strip()
    status = request.GET.get("status", "").strip()
    stock_state = request.GET.get("stock", "").strip()
    if q:
        qs = qs.filter(Q(name__icontains=q) | Q(sku__icontains=q) | Q(brand__icontains=q) | Q(material__icontains=q))
    if vendor_id.isdigit():
        qs = qs.filter(vendor_id=vendor_id)
    if status == "published":
        qs = qs.filter(is_published=True)
    elif status == "hidden":
        qs = qs.filter(is_published=False)
    elif status == "trending":
        qs = qs.filter(is_trending=True)
    if stock_state == "low":
        qs = qs.filter(stock__gt=0, stock__lte=5)
    elif stock_state == "out":
        qs = qs.filter(stock__lte=0)
    context = {
        "page": Paginator(qs.order_by("-updated_at", "-id"), 18).get_page(request.GET.get("page")),
        "filters": {"q": q, "vendor": vendor_id, "status": status, "stock": stock_state},
        "stats": {
            "total": Product.objects.count(),
            "published": Product.objects.filter(is_published=True).count(),
            "low_stock": Product.objects.filter(stock__gt=0, stock__lte=5).count(),
            "out_of_stock": Product.objects.filter(stock__lte=0).count(),
        },
    }
    return render(request, "admin/control/inner/products_v4.html", context)


def _product_editor_context(form, product=None):
    return {
        "form": form,
        "product": product,
        "variants": list(product.variants.all().order_by("id")) if product else [],
        "images": list(product.image_items.all().order_by("sort_order", "id")) if product else [],
        "global_categories": form.fields["categories"].queryset,
        "store_categories": form.fields["store_categories"].queryset,
        "global_category_ids": list(product.categories.values_list("pk", flat=True)) if product else [],
        "store_category_ids": list(product.store_categories.values_list("pk", flat=True)) if product else [],
        "system": {
            "reserved_stock": product.reserved_stock if product else 0,
            "sold_count": product.sold_count if product else 0,
            "reviews_count": product.reviews_count if product else 0,
            "rating": product.rating if product else 0,
        },
    }


@dashboard_access_required
@require_http_methods(["GET"])
def product_detail(request, product_id):
    product = _product(product_id)
    items = OrderItem.objects.filter(product=product).select_related("order", "vendor", "order__customer").order_by("-created_at")
    totals = items.aggregate(units=Sum("quantity"), revenue=Sum("vendor_total"))
    return render(request, "admin/control/inner/product_detail_v9.html", {
        "product": product,
        "items": items[:40],
        "report": {"units": totals["units"] or 0, "revenue": totals["revenue"] or 0, "orders": items.values("order_id").distinct().count()},
        "json_colors": _json(product.colors),
        "json_sizes": _json(product.sizes),
        "json_hashtags": _json(product.hashtags),
        "json_details": _json(product.details),
    })


@dashboard_access_required
@require_http_methods(["GET", "POST"])
def control_stores(request):
    if request.method == "POST":
        vendor_id = request.POST.get("vendor_id", "").strip()
        vendor = get_object_or_404(VendorProfile.objects.select_related("owner"), pk=vendor_id) if vendor_id.isdigit() else None
        form = VendorProfileForm(request.POST, request.FILES, instance=vendor)
        if form.is_valid():
            vendor = form.save()
            messages.success(request, f"تم حفظ متجر «{vendor.store_name}» بكل بياناته.")
            return store_detail(request, vendor.pk) if _ajax(request) else redirect(f"{STORES_URL}{vendor.pk}/detail/")
        return render(request, "admin/control/inner/store_editor_v4.html", {"form": form, "vendor": vendor})

    edit_id = request.GET.get("edit", "").strip()
    if request.path.rstrip("/").endswith("/new") or edit_id.isdigit():
        vendor = get_object_or_404(VendorProfile.objects.select_related("owner"), pk=int(edit_id)) if edit_id.isdigit() else None
        form = VendorProfileForm(instance=vendor) if vendor else VendorProfileForm(initial={"status": "active", "commission_percent": 10})
        return render(request, "admin/control/inner/store_editor_v4.html", {"form": form, "vendor": vendor})

    qs = VendorProfile.objects.select_related("owner").annotate(
        product_count=Count("products", distinct=True), order_count=Count("vendor_orders", distinct=True),
        branch_count=Count("branches", distinct=True), category_count=Count("store_categories", distinct=True),
    )
    q = request.GET.get("q", "").strip(); status = request.GET.get("status", "").strip(); sort = request.GET.get("sort", "newest").strip()
    if q:
        qs = qs.filter(Q(store_name__icontains=q) | Q(slug__icontains=q) | Q(phone__icontains=q) | Q(owner__phone__icontains=q) | Q(owner__email__icontains=q))
    if status in {"active", "pending", "suspended"}: qs = qs.filter(status=status)
    ordering = {"name": ("store_name",), "products": ("-product_count", "store_name"), "orders": ("-order_count", "store_name"), "newest": ("-created_at",)}
    qs = qs.order_by(*ordering.get(sort, ordering["newest"]))
    return render(request, "admin/control/inner/stores_v6.html", {
        "page": Paginator(qs, 16).get_page(request.GET.get("page")),
        "q": q, "status": status, "sort": sort,
        "stats": {
            "total": VendorProfile.objects.count(), "active": VendorProfile.objects.filter(status="active").count(),
            "pending": VendorProfile.objects.filter(status="pending").count(), "suspended": VendorProfile.objects.filter(status="suspended").count(),
            "products": Product.objects.count(), "orders": Order.objects.count(), "branches": VendorBranch.objects.count(), "categories": VendorCategory.objects.count(),
        },
    })


def _store_detail_context(request, vendor):
    products = list(vendor.products.select_related("vendor").prefetch_related("categories", "store_categories", "variants", "image_items").order_by("-updated_at")[:40])
    orders = list(vendor.vendor_orders.select_related("order", "order__customer").order_by("-created_at")[:40])
    conversations = list(Conversation.objects.filter(vendor=vendor).select_related("customer", "order").prefetch_related("messages__sender").order_by("-updated_at")[:20])
    order_chats = list(OrderChat.objects.filter(vendor=vendor).select_related("order", "order__customer", "vendor_order").prefetch_related("messages__sender").order_by("-updated_at")[:20])
    theme = DesignTheme.objects.filter(vendor=vendor).first()
    sections = list(StorefrontSection.objects.filter(vendor=vendor).order_by("sort_order", "id")[:30])
    media = list(StorefrontMedia.objects.filter(vendor=vendor).order_by("sort_order", "id")[:30])
    store_categories = list(VendorCategory.objects.filter(vendor=vendor).select_related("parent").annotate(product_count=Count("products", distinct=True)).order_by("parent_id", "sort_order", "name"))
    branches = list(VendorBranch.objects.filter(vendor=vendor).order_by("-is_main", "name"))
    ledger = list(VendorLedgerEntry.objects.filter(vendor=vendor).order_by("-created_at")[:20])
    payouts = list(VendorPayout.objects.filter(vendor=vendor).order_by("-created_at")[:20])
    sales = vendor.vendor_orders.aggregate(gross=Sum("total"), commission=Sum("commission"), net=Sum("vendor_net"))
    edit_category_id = request.GET.get("edit_category", "").strip()
    edit_branch_id = request.GET.get("edit_branch", "").strip()
    category_instance = get_object_or_404(VendorCategory, pk=edit_category_id, vendor=vendor) if edit_category_id.isdigit() else None
    branch_instance = get_object_or_404(VendorBranch, pk=edit_branch_id, vendor=vendor) if edit_branch_id.isdigit() else None
    return {
        "vendor": vendor, "products": products, "orders": orders, "conversations": conversations, "order_chats": order_chats,
        "theme": theme, "sections": sections, "media": media, "store_categories": store_categories, "branches": branches,
        "category_form": VendorCategoryForm(instance=category_instance, initial={"vendor": vendor.pk} if not category_instance else None),
        "branch_form": VendorBranchForm(instance=branch_instance, initial={"vendor": vendor.pk} if not branch_instance else None),
        "editing_category": category_instance, "editing_branch": branch_instance,
        "report": {
            "products": vendor.products.count(), "active_products": vendor.products.filter(is_published=True).count(), "orders": vendor.vendor_orders.count(),
            "gross": sales["gross"] or 0, "commission": sales["commission"] or 0, "net": sales["net"] or 0,
            "commission_percent": vendor.commission_percent, "branches": vendor.branches.count(), "store_categories": vendor.store_categories.count(),
        },
        "settings_json": _json(vendor.settings),
        "theme_json": _json({"tokens": theme.tokens, "layout": theme.layout, "sections": theme.sections} if theme else {}),
        "ledger": ledger, "payouts": payouts,
    }


@dashboard_access_required
@require_http_methods(["GET"])
def store_detail(request, vendor_id):
    vendor = get_object_or_404(VendorProfile.objects.select_related("owner"), pk=vendor_id)
    return render(request, "admin/control/inner/store_detail_v6.html", _store_detail_context(request, vendor))


@dashboard_access_required
@require_http_methods(["POST"])
def store_category_save(request, vendor_id):
    vendor = get_object_or_404(VendorProfile, pk=vendor_id)
    category_id = request.POST.get("category_id", "").strip()
    instance = get_object_or_404(VendorCategory, pk=category_id, vendor=vendor) if category_id.isdigit() else None
    data = request.POST.copy(); data["vendor"] = str(vendor.pk)
    form = VendorCategoryForm(data, request.FILES, instance=instance)
    if form.is_valid():
        obj = form.save(); messages.success(request, f"تم حفظ فئة المتجر «{obj.name}».")
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
    get_object_or_404(VendorBranch, pk=branch_id, vendor=vendor).delete(); messages.success(request, "تم حذف الفرع.")
    return store_detail(request, vendor.pk) if _ajax(request) else redirect(f"{STORES_URL}{vendor.pk}/detail/")


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
            obj = form.save(); messages.success(request, f"تم حفظ الفئة «{obj.name}».")
            return control_categories(request)
        return render(request, "admin/control/inner/categories_v6.html", {"form": form, **_categories_context(request)})
    if deleting.isdigit():
        obj = get_object_or_404(Category, pk=deleting)
        if obj.children.exists() or obj.products.exists(): messages.error(request, "لا يمكن حذف الفئة وهي تحتوي على فئات أو منتجات.")
        else: obj.delete(); messages.success(request, "تم حذف الفئة.")
    form = CategoryForm(instance=get_object_or_404(Category, pk=edit_id)) if edit_id.isdigit() else CategoryForm()
    return render(request, "admin/control/inner/categories_v6.html", _categories_context(request, form))


def _categories_context(request, form=None):
    qs = Category.objects.select_related("parent").annotate(product_count=Count("products", distinct=True), child_count=Count("children", distinct=True))
    q = request.GET.get("q", "").strip(); active = request.GET.get("active", "").strip()
    if q: qs = qs.filter(Q(name__icontains=q) | Q(slug__icontains=q))
    if active == "active": qs = qs.filter(is_active=True)
    elif active == "inactive": qs = qs.filter(is_active=False)
    return {
        "page": Paginator(qs.order_by("sort_order", "name"), 100).get_page(request.GET.get("page")),
        "form": form or CategoryForm(), "edit_id": request.GET.get("edit", ""), "q": q, "active": active,
        "stats": {"total": Category.objects.count(), "active": Category.objects.filter(is_active=True).count(), "roots": Category.objects.filter(parent__isnull=True).count(), "products": Product.objects.count()},
    }


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
        stock = max(0, int(request.POST.get("stock", "0") or 0))
        reserved = max(0, int(request.POST.get("reserved_stock", "0") or 0))
        row, _ = BranchInventory.objects.get_or_create(branch=branch, product=product, variant=variant)
        row.stock = stock; row.reserved_stock = min(reserved, stock); row.save()
        messages.success(request, "تم تحديث مخزون الفرع.")
        return store_detail(request, branch.vendor_id) if _ajax(request) else redirect(INVENTORY_URL)

    qs = Product.objects.select_related("vendor").prefetch_related("variants", "branch_inventory__branch")
    q = request.GET.get("q", "").strip(); vendor_id = request.GET.get("vendor", "").strip(); state = request.GET.get("state", "").strip()
    if q: qs = qs.filter(Q(name__icontains=q) | Q(sku__icontains=q) | Q(vendor__store_name__icontains=q))
    if vendor_id.isdigit(): qs = qs.filter(vendor_id=vendor_id)
    if state == "out": qs = qs.filter(stock=0)
    elif state == "low": qs = qs.filter(stock__gt=0, stock__lte=5)
    return render(request, "admin/control/inner/inventory_v9.html", {
        "page": Paginator(qs.order_by("stock", "name"), 30).get_page(request.GET.get("page")),
        "q": q, "vendor_id": vendor_id, "state": state,
        "vendors": VendorProfile.objects.filter(status="active").order_by("store_name"),
    })


@dashboard_access_required
@require_http_methods(["GET"])
def control_orders(request):
    qs = Order.objects.select_related("customer", "payment").prefetch_related("vendor_orders__vendor").order_by("-created_at")
    q = request.GET.get("q", "").strip(); vendor_id = request.GET.get("vendor", "").strip(); status = request.GET.get("status", "").strip(); payment = request.GET.get("payment", "").strip()
    if q: qs = qs.filter(Q(order_number__icontains=q) | Q(customer__phone__icontains=q) | Q(customer__email__icontains=q))
    if vendor_id.isdigit(): qs = qs.filter(vendor_orders__vendor_id=vendor_id).distinct()
    if status: qs = qs.filter(status=status)
    if payment: qs = qs.filter(payment_status=payment)
    return render(request, "admin/control/inner/orders_v4.html", {
        "page": Paginator(qs, 18).get_page(request.GET.get("page")), "q": q, "vendor_id": vendor_id, "status": status, "payment_status": payment,
        "order_statuses": Order._meta.get_field("status").choices,
        "stats": {"total": Order.objects.count(), "pending": Order.objects.filter(status="pending").count(), "processing": Order.objects.filter(status="processing").count(), "delivered": Order.objects.filter(status="delivered").count(), "paid_volume": Order.objects.filter(payment_status="paid").aggregate(v=Sum("total"))["v"] or 0},
    })


@dashboard_access_required
@require_http_methods(["GET"])
def order_detail(request, order_id):
    order = get_object_or_404(Order.objects.select_related("customer", "payment").prefetch_related(
        "items__product__categories", "items__product__store_categories", "items__vendor", "vendor_orders__vendor", "vendor_orders__items__order_item__product",
        "vendor_orders__shipment", "status_history__changed_by", "inventory_reservations__product", "inventory_reservations__variant", "conversation__messages__sender",
        "order_chats__vendor", "order_chats__vendor_order", "order_chats__messages__sender",
    ), pk=order_id)
    return render(request, "admin/control/inner/order_detail_v6.html", {
        "order": order, "chats": list(order.order_chats.all()), "conversation": getattr(order, "conversation", None),
        "shipping_address_json": _json(order.shipping_address), "metadata_json": _json(order.metadata), "statuses": Order.Status.choices,
    })


@dashboard_access_required
@require_http_methods(["GET", "POST"])
def order_status(request, order_id):
    if request.method == "GET": return order_detail(request, order_id)
    order = get_object_or_404(Order, pk=order_id)
    new_status = request.POST.get("status", "").strip()
    allowed = {value for value, _ in Order.Status.choices}
    if new_status not in allowed: return render(request, "admin/control/inner/order_detail_v6.html", {"order": order}, status=400)
    old = order.status
    if old != new_status:
        order.status = new_status; order.save(update_fields=["status", "updated_at"])
        OrderStatusHistory.objects.create(order=order, old_status=old, new_status=new_status, changed_by=request.user, note=request.POST.get("note", "").strip())
    return order_detail(request, order_id) if _ajax(request) else redirect(f"{ORDERS_URL}{order_id}/detail/")


@dashboard_access_required
@require_http_methods(["GET", "POST"])
def order_customer_message(request, order_id):
    order = get_object_or_404(Order.objects.select_related("customer"), pk=order_id)
    if request.method == "POST":
        body = request.POST.get("body", "").strip(); attachment = request.FILES.get("attachment")
        if not body and not attachment:
            messages.error(request, "اكتب رسالة أو أرفق صورة قبل الإرسال.")
        else:
            conversation, _ = Conversation.objects.get_or_create(order=order, defaults={"customer": order.customer, "subject": f"محادثة الطلب {order.order_number}"})
            Message.objects.create(conversation=conversation, sender=request.user, body=body, attachment=attachment)
            conversation.is_closed = False; conversation.save(update_fields=["is_closed", "updated_at"])
            messages.success(request, "تم إرسال الرسالة إلى محادثة العميل.")
    return order_detail(request, order_id) if _ajax(request) else redirect(f"{ORDERS_URL}{order_id}/detail/#customer-chat")


@dashboard_access_required
@require_http_methods(["GET", "POST"])
def order_chat_message(request, order_id):
    order = get_object_or_404(Order, pk=order_id)
    if request.method == "POST":
        chat = get_object_or_404(OrderChat, pk=request.POST.get("chat_id"), order=order)
        body = request.POST.get("body", "").strip(); attachment = request.FILES.get("attachment")
        if not body and not attachment:
            messages.error(request, "اكتب رسالة أو أرفق صورة قبل الإرسال.")
        else:
            OrderChatMessage.objects.create(chat=chat, sender=request.user, body=body, attachment=attachment)
            chat.is_closed = False; chat.save(update_fields=["is_closed", "updated_at"])
            messages.success(request, "تم إرسال رسالة محادثة المتجر.")
    return order_detail(request, order_id) if _ajax(request) else redirect(f"{ORDERS_URL}{order_id}/detail/#chat")


@dashboard_access_required
@require_http_methods(["GET", "POST"])
def order_chat_open(request, order_id, vendor_order_id):
    order = get_object_or_404(Order, pk=order_id)
    if request.method == "POST":
        vendor_order = get_object_or_404(VendorOrder.objects.select_related("vendor"), pk=vendor_order_id, order=order)
        OrderChat.objects.get_or_create(order=order, vendor=vendor_order.vendor, vendor_order=vendor_order, defaults={"customer": order.customer, "subject": f"محادثة الطلب {order.order_number}"})
    return order_detail(request, order_id) if _ajax(request) else redirect(f"{ORDERS_URL}{order_id}/detail/#chat")


# Compatibility aliases for the previous split Control implementation.
product_detail_v9 = product_detail
store_detail_v9 = store_detail
