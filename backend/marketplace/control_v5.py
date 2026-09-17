import json

from django.contrib import messages
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Count, Q, Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from catalog.forms import ProductForm, ProductVariantForm
from catalog.models import Product, ProductImage, ProductVariant
from communication.models import OrderChat, OrderChatMessage
from marketplace.dashboard import dashboard_access_required
from orders.models import Order, OrderItem, OrderStatusHistory, VendorOrder
from vendors.forms import VendorProfileForm
from vendors.models import VendorProfile

PRODUCTS_URL = "/admin/dashboard/control/products/"
STORES_URL = "/admin/dashboard/control/stores/"
ORDERS_URL = "/admin/dashboard/control/orders/"


def _ajax(request):
    return request.headers.get("X-Requested-With") == "XMLHttpRequest"


def _json(value):
    try:
        return json.dumps(value if value is not None else {}, ensure_ascii=False, indent=2)
    except (TypeError, ValueError):
        return str(value or "")


def _product(pk):
    qs = Product.objects.select_related("vendor", "vendor__owner").prefetch_related("categories", "variants", "image_items")
    return get_object_or_404(qs, pk=pk)


def _product_editor_context(form, product=None):
    return {
        "form": form,
        "product": product,
        "variants": list(product.variants.all().order_by("id")) if product else [],
        "images": list(product.image_items.all().order_by("sort_order", "id")) if product else [],
        "json_colors": _json(product.colors if product else []),
        "json_sizes": _json(product.sizes if product else []),
        "json_hashtags": _json(product.hashtags if product else []),
        "json_details": _json(product.details if product else {}),
    }


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


def _products_context(request):
    qs = Product.objects.select_related("vendor").prefetch_related("categories")
    q = request.GET.get("q", "").strip()
    status = request.GET.get("status", "").strip()
    stock = request.GET.get("stock", "").strip()
    if q:
        qs = qs.filter(Q(name__icontains=q) | Q(sku__icontains=q) | Q(brand__icontains=q) | Q(material__icontains=q))
    if status == "published":
        qs = qs.filter(is_published=True)
    elif status == "hidden":
        qs = qs.filter(is_published=False)
    elif status == "trending":
        qs = qs.filter(is_trending=True)
    if stock == "low":
        qs = qs.filter(stock__gt=0, stock__lte=5)
    elif stock == "out":
        qs = qs.filter(stock__lte=0)
    return {
        "page": Paginator(qs.order_by("-updated_at", "-id"), 18).get_page(request.GET.get("page")),
        "filters": {"q": q, "status": status, "stock": stock},
        "stats": {
            "total": Product.objects.count(),
            "published": Product.objects.filter(is_published=True).count(),
            "low_stock": Product.objects.filter(stock__gt=0, stock__lte=5).count(),
            "out_of_stock": Product.objects.filter(stock__lte=0).count(),
        },
    }


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
    editor = request.path.rstrip("/").endswith("/new") or bool(product)
    if editor:
        return render(request, "admin/control/inner/product_editor_v4.html", _product_editor_context(ProductForm(instance=product) if product else ProductForm(), product))
    return render(request, "admin/control/inner/products_v4.html", _products_context(request))


@dashboard_access_required
@require_http_methods(["GET"])
def product_detail(request, product_id):
    product = _product(product_id)
    items = OrderItem.objects.filter(product=product).select_related("order", "vendor", "order__customer").order_by("-created_at")
    totals = items.aggregate(units=Sum("quantity"), revenue=Sum("vendor_total"))
    return render(request, "admin/control/inner/product_detail_v4.html", {
        "product": product,
        "items": items[:25],
        "report": {"units": totals["units"] or 0, "revenue": totals["revenue"] or 0, "orders": items.values("order_id").distinct().count()},
        "json_colors": _json(product.colors),
        "json_sizes": _json(product.sizes),
        "json_hashtags": _json(product.hashtags),
        "json_details": _json(product.details),
    })


def _stores_context(request):
    qs = VendorProfile.objects.select_related("owner").annotate(product_count=Count("products", distinct=True), order_count=Count("vendor_orders", distinct=True))
    q = request.GET.get("q", "").strip()
    status = request.GET.get("status", "").strip()
    if q:
        qs = qs.filter(Q(store_name__icontains=q) | Q(slug__icontains=q) | Q(phone__icontains=q) | Q(owner__phone__icontains=q) | Q(owner__email__icontains=q))
    if status in {"active", "pending", "suspended"}:
        qs = qs.filter(status=status)
    return {
        "page": Paginator(qs.order_by("-created_at"), 16).get_page(request.GET.get("page")),
        "q": q,
        "status": status,
        "stats": {
            "total": VendorProfile.objects.count(),
            "active": VendorProfile.objects.filter(status="active").count(),
            "pending": VendorProfile.objects.filter(status="pending").count(),
            "suspended": VendorProfile.objects.filter(status="suspended").count(),
        },
    }


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
            if _ajax(request):
                return store_detail(request, vendor.pk)
            return redirect(f"{STORES_URL}{vendor.pk}/detail/")
        return render(request, "admin/control/inner/store_editor_v4.html", {"form": form, "vendor": vendor})

    edit_id = request.GET.get("edit", "").strip()
    vendor = get_object_or_404(VendorProfile.objects.select_related("owner"), pk=edit_id) if edit_id.isdigit() else None
    editor = request.path.rstrip("/").endswith("/new") or bool(vendor)
    if editor:
        form = VendorProfileForm(instance=vendor) if vendor else VendorProfileForm(initial={"status": "active", "commission_percent": 10})
        return render(request, "admin/control/inner/store_editor_v4.html", {"form": form, "vendor": vendor})
    return render(request, "admin/control/inner/stores_v4.html", _stores_context(request))


@dashboard_access_required
@require_http_methods(["GET"])
def store_detail(request, vendor_id):
    vendor = get_object_or_404(VendorProfile.objects.select_related("owner"), pk=vendor_id)
    products = vendor.products.select_related("vendor").prefetch_related("categories").order_by("-updated_at")[:25]
    orders = vendor.vendor_orders.select_related("order", "order__customer").order_by("-created_at")[:25]
    conversations = vendor.conversations.select_related("customer", "order").prefetch_related("messages__sender").order_by("-updated_at")[:20]
    order_chats = vendor.order_chats.select_related("order", "order__customer", "vendor_order").prefetch_related("messages__sender").order_by("-updated_at")[:20]
    sales = vendor.vendor_orders.aggregate(gross=Sum("total"), commission=Sum("commission"), net=Sum("vendor_net"))
    return render(request, "admin/control/inner/store_detail_v4.html", {
        "vendor": vendor,
        "products": products,
        "orders": orders,
        "conversations": conversations,
        "order_chats": order_chats,
        "report": {"products": vendor.products.count(), "active_products": vendor.products.filter(is_published=True).count(), "orders": vendor.vendor_orders.count(), "gross": sales["gross"] or 0, "commission": sales["commission"] or 0, "net": sales["net"] or 0},
        "settings_json": _json(vendor.settings),
    })


@dashboard_access_required
@require_http_methods(["GET"])
def control_orders(request):
    qs = Order.objects.select_related("customer", "payment").annotate(item_count=Count("items", distinct=True), vendor_count=Count("vendor_orders", distinct=True))
    q = request.GET.get("q", "").strip()
    status = request.GET.get("status", "").strip()
    payment_status = request.GET.get("payment", "").strip()
    if q:
        qs = qs.filter(Q(order_number__icontains=q) | Q(customer__phone__icontains=q) | Q(customer__email__icontains=q))
    if status:
        qs = qs.filter(status=status)
    if payment_status:
        qs = qs.filter(payment_status=payment_status)
    all_orders = Order.objects.all()
    return render(request, "admin/control/inner/orders_v4.html", {
        "page": Paginator(qs.order_by("-created_at", "-id"), 16).get_page(request.GET.get("page")),
        "q": q,
        "status": status,
        "payment_status": payment_status,
        "order_statuses": Order.Status.choices,
        "stats": {"total": all_orders.count(), "pending": all_orders.filter(status="pending").count(), "processing": all_orders.filter(status="processing").count(), "delivered": all_orders.filter(status="delivered").count(), "paid_volume": all_orders.filter(payment_status="paid").aggregate(v=Sum("total"))["v"] or 0},
    })


def _order(pk):
    return get_object_or_404(
        Order.objects.select_related("customer", "payment").prefetch_related(
            "items__product__categories",
            "items__vendor",
            "vendor_orders__vendor",
            "vendor_orders__items__order_item__product",
            "vendor_orders__shipment",
            "status_history__changed_by",
            "inventory_reservations__product",
            "inventory_reservations__variant",
            "conversation__messages__sender",
            "order_chats__vendor",
            "order_chats__vendor_order",
            "order_chats__messages__sender",
        ),
        pk=pk,
    )


@dashboard_access_required
@require_http_methods(["GET"])
def order_detail(request, order_id):
    order = _order(order_id)
    return render(request, "admin/control/inner/order_detail_v4.html", {
        "order": order,
        "chats": list(order.order_chats.all()),
        "conversation": getattr(order, "conversation", None),
        "shipping_address_json": _json(order.shipping_address),
        "metadata_json": _json(order.metadata),
        "statuses": Order.Status.choices,
    })


@dashboard_access_required
@require_http_methods(["GET", "POST"])
def order_status(request, order_id):
    if request.method == "GET":
        return order_detail(request, order_id)
    order = get_object_or_404(Order, pk=order_id)
    new_status = request.POST.get("status", "").strip()
    allowed = {value for value, _label in Order.Status.choices}
    if new_status not in allowed:
        return HttpResponse("حالة الطلب غير صالحة", status=400)
    if order.status != new_status:
        old_status = order.status
        with transaction.atomic():
            order.status = new_status
            order.save(update_fields=["status", "updated_at"])
            OrderStatusHistory.objects.create(order=order, old_status=old_status, new_status=new_status, changed_by=request.user, note=request.POST.get("note", "").strip())
        messages.success(request, f"تم تحديث حالة الطلب {order.order_number} إلى {order.get_status_display()}.")
    return order_detail(request, order.pk) if _ajax(request) else redirect(f"{ORDERS_URL}{order.pk}/detail/")


@dashboard_access_required
@require_http_methods(["GET", "POST"])
def order_chat_message(request, order_id):
    if request.method == "GET":
        return order_detail(request, order_id)
    order = get_object_or_404(Order, pk=order_id)
    chat = get_object_or_404(OrderChat, pk=request.POST.get("chat_id"), order=order)
    body = request.POST.get("body", "").strip()
    attachment = request.FILES.get("attachment")
    if not body and not attachment:
        messages.error(request, "اكتب رسالة أو أرفق ملفًا قبل الإرسال.")
        return order_detail(request, order.pk) if _ajax(request) else redirect(f"{ORDERS_URL}{order.pk}/detail/#chat-{chat.pk}")
    OrderChatMessage.objects.create(chat=chat, sender=request.user, body=body, attachment=attachment)
    chat.is_closed = False
    chat.save(update_fields=["is_closed", "updated_at"])
    messages.success(request, "تم إرسال رسالة المحادثة.")
    return order_detail(request, order.pk) if _ajax(request) else redirect(f"{ORDERS_URL}{order.pk}/detail/#chat-{chat.pk}")


@dashboard_access_required
@require_http_methods(["GET", "POST"])
def order_chat_open(request, order_id, vendor_order_id):
    if request.method == "GET":
        return order_detail(request, order_id)
    order = get_object_or_404(Order, pk=order_id)
    vendor_order = get_object_or_404(VendorOrder.objects.select_related("vendor"), pk=vendor_order_id, order=order)
    OrderChat.objects.get_or_create(
        order=order,
        vendor=vendor_order.vendor,
        defaults={"vendor_order": vendor_order, "customer": order.customer, "subject": f"محادثة الطلب {order.order_number}"},
    )
    return order_detail(request, order.pk) if _ajax(request) else redirect(f"{ORDERS_URL}{order.pk}/detail/#chat")
