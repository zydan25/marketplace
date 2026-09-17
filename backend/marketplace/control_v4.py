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
from communication.models import Conversation, Message, OrderChat, OrderChatMessage
from marketplace.control_pages import CONTROL_HOME, control_access_required, is_ajax
from orders.models import InventoryReservation, Order, OrderItem, OrderStatusHistory, Payment, Shipment, VendorOrder
from vendors.forms import VendorProfileForm
from vendors.models import VendorProfile


CONTROL_PRODUCTS = "/admin/dashboard/control/products/"
CONTROL_STORES = "/admin/dashboard/control/stores/"
CONTROL_ORDERS = "/admin/dashboard/control/orders/"


def _json_for_display(value):
    try:
        return json.dumps(value or {}, ensure_ascii=False, indent=2)
    except (TypeError, ValueError):
        return str(value or "")


def _product_editor_context(request, form, product=None, form_open=True):
    variants = list(product.variants.all().order_by("id")) if product else []
    images = list(product.image_items.all().order_by("sort_order", "id")) if product else []
    return {
        "form": form,
        "product": product,
        "variants": variants,
        "images": images,
        "form_open": form_open,
        "json_colors": _json_for_display(product.colors if product else []),
        "json_sizes": _json_for_display(product.sizes if product else []),
        "json_hashtags": _json_for_display(product.hashtags if product else []),
        "json_details": _json_for_display(product.details if product else {}),
    }


def _save_variants(request, product):
    ids = request.POST.getlist("variant_id")
    skus = request.POST.getlist("variant_sku")
    colors = request.POST.getlist("variant_color")
    sizes = request.POST.getlist("variant_size")
    prices = request.POST.getlist("variant_price_override")
    stocks = request.POST.getlist("variant_stock")
    active = request.POST.getlist("variant_active")
    deleted = set(request.POST.getlist("variant_delete"))
    total = max(len(ids), len(skus), len(colors), len(sizes), len(prices), len(stocks), len(active))

    errors = []
    variants = {str(v.pk): v for v in product.variants.all()}
    for i in range(total):
        variant_id = ids[i] if i < len(ids) else ""
        payload = {
            "sku": skus[i] if i < len(skus) else "",
            "color": colors[i] if i < len(colors) else "",
            "size": sizes[i] if i < len(sizes) else "",
            "price_override": prices[i] if i < len(prices) and prices[i] != "" else None,
            "stock": stocks[i] if i < len(stocks) and stocks[i] != "" else 0,
            "is_active": (active[i] if i < len(active) else "1") not in {"0", "false", "off"},
        }
        if variant_id in deleted and variant_id in variants:
            variants[variant_id].delete()
            continue
        is_blank = not any([payload["color"], payload["size"], payload["sku"], str(payload["price_override"] or "").strip()]) and str(payload["stock"]) in {"", "0"}
        if not variant_id and is_blank:
            continue
        instance = variants.get(variant_id) or ProductVariant(product=product)
        form = ProductVariantForm(payload, instance=instance)
        if not form.is_valid():
            errors.append(f"المتغير رقم {i + 1}: {form.errors.as_text()}")
            continue
        saved = form.save(commit=False)
        saved.product = product
        saved.save()
    return errors


@control_access_required
@require_http_methods(["GET", "POST"])
def control_products_v4(request):
    product = None
    if request.method == "POST":
        product_id = request.POST.get("product_id", "").strip()
        product = get_object_or_404(Product.objects.select_related("vendor").prefetch_related("categories", "variants", "image_items"), pk=product_id) if product_id else None
        form = ProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            with transaction.atomic():
                product = form.save()
                delete_image_ids = [int(v) for v in request.POST.getlist("delete_image") if str(v).isdigit()]
                if delete_image_ids:
                    ProductImage.objects.filter(product=product, pk__in=delete_image_ids).delete()
                for upload in request.FILES.getlist("gallery_images"):
                    ProductImage.objects.create(product=product, image=upload, alt_text=product.name)
                errors = _save_variants(request, product)
                if errors:
                    transaction.set_rollback(True)
                else:
                    messages.success(request, f"تم حفظ المنتج «{product.name}» بكل بياناته وعلاقاته.")
                    if is_ajax(request):
                        return redirect(f"{CONTROL_PRODUCTS}{product.pk}/detail/")
                    return redirect(f"{CONTROL_PRODUCTS}{product.pk}/detail/")
            if errors:
                for error in errors:
                    form.add_error(None, error)
        context = _product_editor_context(request, form, product, True)
        return render(request, "admin/control/inner/product_editor_v4.html", context)

    edit_id = request.GET.get("edit", "").strip()
    product = get_object_or_404(Product.objects.select_related("vendor").prefetch_related("categories", "variants", "image_items"), pk=edit_id) if edit_id.isdigit() else None
    create_mode = request.path.rstrip("/").endswith("/new") or request.GET.get("create") == "1"
    if not product and not create_mode:
        return render(request, "admin/control/inner/products_v4.html", _products_list_context(request))
    form = ProductForm(instance=product) if product else ProductForm()
    context = _product_editor_context(request, form, product, True)
    return render(request, "admin/control/inner/product_editor_v4.html", context)


def _products_list_context(request):
    from django.db.models import Count

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
    page = Paginator(qs.order_by("-updated_at", "-id"), 18).get_page(request.GET.get("page"))
    return {
        "page": page,
        "filters": {"q": q, "status": status, "stock": stock},
        "stats": {
            "total": Product.objects.count(),
            "published": Product.objects.filter(is_published=True).count(),
            "low_stock": Product.objects.filter(stock__gt=0, stock__lte=5).count(),
            "out_of_stock": Product.objects.filter(stock__lte=0).count(),
        },
    }


@control_access_required
@require_http_methods(["GET"])
def control_product_detail(request, product_id):
    product = get_object_or_404(
        Product.objects.select_related("vendor", "vendor__owner").prefetch_related("categories", "variants", "image_items"),
        pk=product_id,
    )
    item_qs = OrderItem.objects.filter(product=product).select_related("order", "vendor", "order__customer").order_by("-created_at")
    report = item_qs.aggregate(units=Sum("quantity"), revenue=Sum("vendor_total"))
    return render(
        request,
        "admin/control/inner/product_detail_v4.html",
        {
            "product": product,
            "items": item_qs[:25],
            "report": {"units": report["units"] or 0, "revenue": report["revenue"] or 0, "orders": item_qs.values("order_id").distinct().count()},
            "json_colors": _json_for_display(product.colors),
            "json_sizes": _json_for_display(product.sizes),
            "json_hashtags": _json_for_display(product.hashtags),
            "json_details": _json_for_display(product.details),
        },
    )


@control_access_required
@require_http_methods(["GET", "POST"])
def control_stores_v4(request):
    vendor = None
    if request.method == "POST":
        vendor_id = request.POST.get("vendor_id", "").strip()
        vendor = get_object_or_404(VendorProfile.objects.select_related("owner"), pk=vendor_id) if vendor_id.isdigit() else None
        form = VendorProfileForm(request.POST, request.FILES, instance=vendor)
        if form.is_valid():
            vendor = form.save()
            messages.success(request, f"تم حفظ متجر «{vendor.store_name}» بكل بياناته.")
            return redirect(f"{CONTROL_STORES}{vendor.pk}/detail/")
        return render(request, "admin/control/inner/store_editor_v4.html", {"form": form, "vendor": vendor, "form_open": True})

    edit_id = request.GET.get("edit", "").strip()
    vendor = get_object_or_404(VendorProfile.objects.select_related("owner"), pk=edit_id) if edit_id.isdigit() else None
    create_mode = request.path.rstrip("/").endswith("/new") or request.GET.get("create") == "1"
    if vendor or create_mode:
        form = VendorProfileForm(instance=vendor) if vendor else VendorProfileForm(initial={"status": "active", "commission_percent": 10})
        return render(request, "admin/control/inner/store_editor_v4.html", {"form": form, "vendor": vendor, "form_open": True})
    return render(request, "admin/control/inner/stores_v4.html", _stores_list_context(request))


def _stores_list_context(request):
    qs = VendorProfile.objects.select_related("owner").annotate(product_count=Count("products", distinct=True), order_count=Count("vendor_orders", distinct=True))
    q = request.GET.get("q", "").strip()
    status = request.GET.get("status", "").strip()
    if q:
        qs = qs.filter(Q(store_name__icontains=q) | Q(slug__icontains=q) | Q(phone__icontains=q) | Q(owner__phone__icontains=q) | Q(owner__email__icontains=q))
    if status in {"active", "pending", "suspended"}:
        qs = qs.filter(status=status)
    page = Paginator(qs.order_by("-created_at"), 16).get_page(request.GET.get("page"))
    return {
        "page": page,
        "q": q,
        "status": status,
        "stats": {
            "total": VendorProfile.objects.count(),
            "active": VendorProfile.objects.filter(status="active").count(),
            "pending": VendorProfile.objects.filter(status="pending").count(),
            "suspended": VendorProfile.objects.filter(status="suspended").count(),
        },
    }


@control_access_required
@require_http_methods(["GET"])
def control_store_detail(request, vendor_id):
    vendor = get_object_or_404(VendorProfile.objects.select_related("owner"), pk=vendor_id)
    products = vendor.products.select_related("vendor").prefetch_related("categories").order_by("-updated_at")[:25]
    vendor_orders = vendor.vendor_orders.select_related("order", "order__customer").order_by("-created_at")[:25]
    conversations = vendor.conversations.select_related("customer", "order").prefetch_related("messages__sender").order_by("-updated_at")[:20]
    order_chats = vendor.order_chats.select_related("order", "order__customer", "vendor_order").prefetch_related("messages__sender").order_by("-updated_at")[:20]
    sales = vendor_orders.aggregate(gross=Sum("total"), commission=Sum("commission"), net=Sum("vendor_net"))
    return render(
        request,
        "admin/control/inner/store_detail_v4.html",
        {
            "vendor": vendor,
            "products": products,
            "orders": vendor_orders,
            "conversations": conversations,
            "order_chats": order_chats,
            "report": {
                "products": vendor.products.count(),
                "active_products": vendor.products.filter(is_published=True).count(),
                "orders": vendor.vendor_orders.count(),
                "gross": sales["gross"] or 0,
                "commission": sales["commission"] or 0,
                "net": sales["net"] or 0,
            },
            "settings_json": _json_for_display(vendor.settings),
        },
    )


@control_access_required
@require_http_methods(["GET"])
def control_orders_v4(request):
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
    page = Paginator(qs.order_by("-created_at", "-id"), 16).get_page(request.GET.get("page"))
    all_orders = Order.objects.all()
    return render(
        request,
        "admin/control/inner/orders_v4.html",
        {
            "page": page,
            "q": q,
            "status": status,
            "payment_status": payment_status,
            "stats": {
                "total": all_orders.count(),
                "pending": all_orders.filter(status="pending").count(),
                "processing": all_orders.filter(status="processing").count(),
                "delivered": all_orders.filter(status="delivered").count(),
                "paid_volume": all_orders.filter(payment_status="paid").aggregate(v=Sum("total"))["v"] or 0,
            },
        },
    )


@control_access_required
@require_http_methods(["GET"])
def control_order_detail(request, order_id):
    order = get_object_or_404(
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
        pk=order_id,
    )
    chats = list(order.order_chats.all())
    general_conversation = getattr(order, "conversation", None)
    return render(
        request,
        "admin/control/inner/order_detail_v4.html",
        {
            "order": order,
            "chats": chats,
            "conversation": general_conversation,
            "shipping_address_json": _json_for_display(order.shipping_address),
            "metadata_json": _json_for_display(order.metadata),
            "statuses": Order.Status.choices,
        },
    )


@control_access_required
@require_http_methods(["POST"])
def control_order_status_v4(request, order_id):
    order = get_object_or_404(Order, pk=order_id)
    new_status = request.POST.get("status", "").strip()
    valid = {value for value, _label in Order.Status.choices}
    if new_status not in valid:
        return HttpResponse("حالة الطلب غير صالحة", status=400)
    old_status = order.status
    if new_status != old_status:
        with transaction.atomic():
            order.status = new_status
            order.save(update_fields=["status", "updated_at"])
            OrderStatusHistory.objects.create(order=order, old_status=old_status, new_status=new_status, changed_by=request.user, note=request.POST.get("note", "").strip())
        messages.success(request, f"تم تحديث حالة الطلب {order.order_number} إلى {order.get_status_display()}.")
    return redirect(f"{CONTROL_ORDERS}{order.pk}/detail/")


@control_access_required
@require_http_methods(["POST"])
def control_order_chat_message_v4(request, order_id):
    order = get_object_or_404(Order, pk=order_id)
    chat_id = request.POST.get("chat_id", "").strip()
    body = request.POST.get("body", "").strip()
    chat = get_object_or_404(OrderChat.objects.select_related("order"), pk=chat_id, order=order)
    attachment = request.FILES.get("attachment")
    if not body and not attachment:
        messages.error(request, "اكتب رسالة أو أرفق ملفًا قبل الإرسال.")
        return redirect(f"{CONTROL_ORDERS}{order.pk}/detail/#chat-{chat.pk}")
    OrderChatMessage.objects.create(chat=chat, sender=request.user, body=body, attachment=attachment)
    chat.is_closed = False
    chat.save(update_fields=["is_closed", "updated_at"])
    messages.success(request, "تم إرسال رسالة المحادثة.")
    return redirect(f"{CONTROL_ORDERS}{order.pk}/detail/#chat-{chat.pk}")


@control_access_required
@require_http_methods(["POST"])
def control_order_chat_open_v4(request, order_id, vendor_order_id):
    order = get_object_or_404(Order, pk=order_id)
    vendor_order = get_object_or_404(VendorOrder.objects.select_related("vendor"), pk=vendor_order_id, order=order)
    chat, _created = OrderChat.objects.get_or_create(
        order=order,
        vendor=vendor_order.vendor,
        defaults={"vendor_order": vendor_order, "customer": order.customer, "subject": f"محادثة الطلب {order.order_number}"},
    )
    if not chat.vendor_order_id:
        chat.vendor_order = vendor_order
        chat.customer = order.customer
        chat.save(update_fields=["vendor_order", "customer", "updated_at"])
    return redirect(f"{CONTROL_ORDERS}{order.pk}/detail/#chat-{chat.pk}")
