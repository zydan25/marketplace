import json

from django.contrib import messages
from django.db import transaction
from django.shortcuts import get_object_or_404, render, redirect
from django.views.decorators.http import require_http_methods

from catalog.forms import ProductForm, ProductVariantForm
from catalog.models import Product, ProductImage, ProductVariant
from marketplace.control_pages import control_access_required
from .control_v5 import control_products as legacy_products
from .control_v5 import product_detail as legacy_product_detail

PRODUCTS_URL = "/admin/dashboard/control/products/"


def _ajax(request):
    return request.headers.get("X-Requested-With") == "XMLHttpRequest"


def _product(pk):
    return get_object_or_404(
        Product.objects.select_related("vendor", "vendor__owner").prefetch_related(
            "categories", "store_categories", "variants", "image_items"
        ),
        pk=pk,
    )


def _editor_context(form, product=None):
    global_ids = list(product.categories.values_list("pk", flat=True)) if product else []
    store_ids = list(product.store_categories.values_list("pk", flat=True)) if product else []
    store_category_queryset = form.fields["store_categories"].queryset if "store_categories" in form.fields else []
    return {
        "form": form,
        "product": product,
        "variants": list(product.variants.all().order_by("id")) if product else [],
        "images": list(product.image_items.all().order_by("sort_order", "id")) if product else [],
        "global_categories": form.fields["categories"].queryset,
        "store_categories": store_category_queryset,
        "global_category_ids": global_ids,
        "store_category_ids": store_ids,
        "system": {
            "reserved_stock": product.reserved_stock if product else 0,
            "sold_count": product.sold_count if product else 0,
            "reviews_count": product.reviews_count if product else 0,
            "rating": product.rating if product else 0,
        },
        "json_colors": json.dumps(product.colors if product else [], ensure_ascii=False, indent=2),
        "json_sizes": json.dumps(product.sizes if product else [], ensure_ascii=False, indent=2),
        "json_hashtags": json.dumps(product.hashtags if product else [], ensure_ascii=False, indent=2),
        "json_details": json.dumps(product.details if product else {}, ensure_ascii=False, indent=2),
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


@control_access_required
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
                        return legacy_product_detail(request, product.pk)
                    return redirect(f"{PRODUCTS_URL}{product.pk}/detail/")
            for error in errors:
                form.add_error(None, error)
        return render(request, "admin/control/inner/product_editor_v4.html", _editor_context(form, product))

    edit_id = request.GET.get("edit", "").strip()
    product = _product(edit_id) if edit_id.isdigit() else None
    editor = request.path.rstrip("/").endswith("/new") or bool(product)
    if editor:
        form = ProductForm(instance=product) if product else ProductForm()
        return render(request, "admin/control/inner/product_editor_v4.html", _editor_context(form, product))
    return legacy_products(request)


@control_access_required
@require_http_methods(["GET"])
def product_detail(request, product_id):
    return legacy_product_detail(request, product_id)
