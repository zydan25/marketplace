import csv
from functools import wraps
from urllib.parse import urlencode

from django.contrib import messages
from django.core.paginator import Paginator
from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from marketplace.models import VendorProfile

from .forms import CategoryForm, CatalogOptionForm, PriceGroupForm, ProductForm, ProductImageForm, ProductVariantForm
from .models import Category, CatalogOption, PriceGroup, Product, ProductImage, ProductVariant


CATALOG_HOME = "/admin/dashboard/catalog/"
PRODUCT_BULK_ACTIONS = {
    "publish": "نشر المنتجات المحددة",
    "unpublish": "إخفاء المنتجات المحددة",
    "trend": "تمييز المنتجات كترند",
    "untrend": "إلغاء حالة الترند",
}


def catalog_access_required(view):
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect(f"/admin/dashboard/login/?next={request.get_full_path()}")
        if not (request.user.is_staff or getattr(request.user, "role", None) == "admin"):
            return HttpResponse("ليس لديك صلاحية الوصول إلى مركز الكتالوج.", status=403)
        return view(request, *args, **kwargs)

    return wrapped


def _product_queryset(request):
    qs = Product.objects.select_related("vendor", "vendor__owner").prefetch_related("categories", "variants", "image_items")
    q = request.GET.get("q", "").strip()
    vendor = request.GET.get("vendor", "").strip()
    category = request.GET.get("category", "").strip()
    status = request.GET.get("status", "").strip()
    stock = request.GET.get("stock", "").strip()
    if q:
        qs = qs.filter(name__icontains=q) | Product.objects.filter(sku__icontains=q) | Product.objects.filter(description__icontains=q)
        qs = qs.distinct()
    if vendor.isdigit():
        qs = qs.filter(vendor_id=int(vendor))
    if category.isdigit():
        qs = qs.filter(categories__id=int(category))
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
    return qs.order_by("-updated_at", "-id").distinct()


@catalog_access_required
def overview(request):
    products = Product.objects.all()
    return render(
        request,
        "catalog/dashboard/overview.html",
        {
            "now": timezone.now(),
            "stats": {
                "products": products.count(),
                "published": products.filter(is_published=True).count(),
                "hidden": products.filter(is_published=False).count(),
                "trending": products.filter(is_trending=True).count(),
                "categories": Category.objects.count(),
                "active_categories": Category.objects.filter(is_active=True).count(),
                "variants": ProductVariant.objects.count(),
                "options": CatalogOption.objects.filter(is_active=True).count(),
                "price_groups": PriceGroup.objects.filter(is_active=True).count(),
                "low_stock": products.filter(stock__gt=0, stock__lte=5).count(),
                "out_of_stock": products.filter(stock__lte=0).count(),
            },
            "recent_products": products.select_related("vendor").order_by("-created_at", "-id")[:8],
            "active_vendors": VendorProfile.objects.filter(status="active").count(),
        },
    )


@catalog_access_required
def categories(request):
    qs = Category.objects.select_related("parent").order_by("sort_order", "name", "id")
    q = request.GET.get("q", "").strip()
    if q:
        qs = qs.filter(name__icontains=q)
    paginator = Paginator(qs, 30)
    page_obj = paginator.get_page(request.GET.get("page"))
    return render(request, "catalog/dashboard/categories.html", {"page_obj": page_obj, "q": q})


@catalog_access_required
def category_create(request):
    form = CategoryForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        category = form.save()
        messages.success(request, f"تم إنشاء الفئة «{category.name}».")
        return redirect("catalog-dashboard:categories")
    return render(request, "catalog/dashboard/category_form.html", {"form": form, "mode": "create"})


@catalog_access_required
def category_update(request, category_id):
    category = get_object_or_404(Category, pk=category_id)
    form = CategoryForm(request.POST or None, request.FILES or None, instance=category)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "تم حفظ الفئة.")
        return redirect("catalog-dashboard:categories")
    return render(request, "catalog/dashboard/category_form.html", {"form": form, "mode": "edit", "category": category})


@catalog_access_required
def category_toggle(request, category_id):
    category = get_object_or_404(Category, pk=category_id)
    if request.method == "POST":
        category.is_active = not category.is_active
        category.save(update_fields=["is_active", "updated_at"])
        messages.success(request, "تم تحديث حالة الفئة.")
    return redirect("catalog-dashboard:categories")


@catalog_access_required
def products(request):
    if request.method == "POST":
        action = request.POST.get("bulk_action", "")
        ids = [value for value in request.POST.getlist("selected_products") if value.isdigit()]
        if action not in PRODUCT_BULK_ACTIONS or not ids:
            messages.warning(request, "حدد منتجات واختر إجراءً صالحًا أولًا.")
        else:
            changed = Product.objects.filter(pk__in=ids)
            if action == "publish":
                changed.update(is_published=True, updated_at=timezone.now())
            elif action == "unpublish":
                changed.update(is_published=False, updated_at=timezone.now())
            elif action == "trend":
                changed.update(is_trending=True, updated_at=timezone.now())
            elif action == "untrend":
                changed.update(is_trending=False, updated_at=timezone.now())
            messages.success(request, f"تم تنفيذ «{PRODUCT_BULK_ACTIONS[action]}» على {changed.count()} منتج.")
        query = request.GET.copy()
        return redirect(f"{redirect('catalog-dashboard:products').url}?{urlencode(query, doseq=True)}" if query else redirect("catalog-dashboard:products"))

    qs = _product_queryset(request)
    paginator = Paginator(qs, 25)
    page_obj = paginator.get_page(request.GET.get("page"))
    filters = {key: request.GET.get(key, "") for key in ("q", "vendor", "category", "status", "stock")}
    return render(
        request,
        "catalog/dashboard/products.html",
        {
            "page_obj": page_obj,
            "filters": filters,
            "vendors": VendorProfile.objects.order_by("store_name"),
            "categories": Category.objects.filter(is_active=True).order_by("sort_order", "name"),
            "bulk_actions": PRODUCT_BULK_ACTIONS,
        },
    )


@catalog_access_required
def product_create(request):
    form = ProductForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        product = form.save()
        messages.success(request, f"تم إنشاء المنتج «{product.name}».")
        return redirect("catalog-dashboard:product-detail", product_id=product.pk)
    return render(request, "catalog/dashboard/product_form.html", {"form": form, "mode": "create"})


@catalog_access_required
def product_update(request, product_id):
    product = get_object_or_404(Product.objects.select_related("vendor"), pk=product_id)
    form = ProductForm(request.POST or None, request.FILES or None, instance=product)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "تم حفظ بيانات المنتج.")
        return redirect("catalog-dashboard:product-detail", product_id=product.pk)
    return render(request, "catalog/dashboard/product_form.html", {"form": form, "mode": "edit", "product": product})


@catalog_access_required
def product_detail(request, product_id):
    product = get_object_or_404(
        Product.objects.select_related("vendor").prefetch_related("categories", "variants", "image_items"),
        pk=product_id,
    )
    return render(
        request,
        "catalog/dashboard/product_detail.html",
        {
            "product": product,
            "variant_form": ProductVariantForm(),
            "image_form": ProductImageForm(),
        },
    )


@catalog_access_required
def product_publish_toggle(request, product_id):
    product = get_object_or_404(Product, pk=product_id)
    if request.method == "POST":
        product.is_published = not product.is_published
        product.save(update_fields=["is_published", "updated_at"])
        messages.success(request, "تم تحديث حالة نشر المنتج.")
    return redirect("catalog-dashboard:product-detail", product_id=product.pk)


@catalog_access_required
def product_trend_toggle(request, product_id):
    product = get_object_or_404(Product, pk=product_id)
    if request.method == "POST":
        product.is_trending = not product.is_trending
        product.save(update_fields=["is_trending", "updated_at"])
        messages.success(request, "تم تحديث حالة الترند.")
    return redirect("catalog-dashboard:product-detail", product_id=product.pk)


@catalog_access_required
def variant_create(request, product_id):
    product = get_object_or_404(Product, pk=product_id)
    form = ProductVariantForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        variant = form.save(commit=False)
        variant.product = product
        variant.save()
        messages.success(request, "تمت إضافة الصنف.")
    return redirect("catalog-dashboard:product-detail", product_id=product.pk)


@catalog_access_required
def variant_update(request, variant_id):
    variant = get_object_or_404(ProductVariant.objects.select_related("product"), pk=variant_id)
    form = ProductVariantForm(request.POST or None, instance=variant)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "تم حفظ الصنف.")
    return redirect("catalog-dashboard:product-detail", product_id=variant.product_id)


@catalog_access_required
def variant_toggle(request, variant_id):
    variant = get_object_or_404(ProductVariant.objects.select_related("product"), pk=variant_id)
    if request.method == "POST":
        variant.is_active = not variant.is_active
        variant.save(update_fields=["is_active", "updated_at"])
        messages.success(request, "تم تحديث حالة الصنف.")
    return redirect("catalog-dashboard:product-detail", product_id=variant.product_id)


@catalog_access_required
def image_create(request, product_id):
    product = get_object_or_404(Product, pk=product_id)
    form = ProductImageForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            image = form.save(commit=False)
            image.product = product
            if image.is_primary:
                product.image_items.update(is_primary=False)
            image.save()
            if not product.main_image and image.image:
                product.main_image = image.image
                product.save(update_fields=["main_image", "updated_at"])
        messages.success(request, "تمت إضافة الصورة.")
    return redirect("catalog-dashboard:product-detail", product_id=product.pk)


@catalog_access_required
def image_primary(request, image_id):
    image = get_object_or_404(ProductImage.objects.select_related("product"), pk=image_id)
    if request.method == "POST":
        with transaction.atomic():
            ProductImage.objects.filter(product=image.product).update(is_primary=False)
            image.is_primary = True
            image.save(update_fields=["is_primary", "updated_at"])
            image.product.main_image = image.image
            image.product.save(update_fields=["main_image", "updated_at"])
        messages.success(request, "تم تعيين الصورة الرئيسية.")
    return redirect("catalog-dashboard:product-detail", product_id=image.product_id)


@catalog_access_required
def image_delete(request, image_id):
    image = get_object_or_404(ProductImage.objects.select_related("product"), pk=image_id)
    product = image.product
    if request.method == "POST":
        was_primary = image.is_primary
        image.delete()
        if was_primary:
            next_image = product.image_items.order_by("sort_order", "id").first()
            ProductImage.objects.filter(product=product).update(is_primary=False)
            if next_image:
                next_image.is_primary = True
                next_image.save(update_fields=["is_primary", "updated_at"])
                product.main_image = next_image.image
            else:
                product.main_image = None
            product.save(update_fields=["main_image", "updated_at"])
        messages.success(request, "تم حذف الصورة.")
    return redirect("catalog-dashboard:product-detail", product_id=product.pk)


@catalog_access_required
def options(request):
    if request.method == "POST":
        option_id = request.POST.get("option_id")
        instance = get_object_or_404(CatalogOption, pk=option_id) if option_id else None
        form = CatalogOptionForm(request.POST, instance=instance)
        if form.is_valid():
            option = form.save(commit=False)
            if not option.slug:
                option.slug = slugify(option.name, allow_unicode=True)
            option.save()
            messages.success(request, "تم حفظ خيار الكتالوج.")
            return redirect("catalog-dashboard:options")
    form = CatalogOptionForm()
    return render(request, "catalog/dashboard/options.html", {"options": CatalogOption.objects.select_related("category").order_by("group", "sort_order", "name"), "form": form})


@catalog_access_required
def option_toggle(request, option_id):
    option = get_object_or_404(CatalogOption, pk=option_id)
    if request.method == "POST":
        option.is_active = not option.is_active
        option.save(update_fields=["is_active", "updated_at"])
        messages.success(request, "تم تحديث حالة الخيار.")
    return redirect("catalog-dashboard:options")


@catalog_access_required
def price_groups(request):
    if request.method == "POST":
        group_id = request.POST.get("group_id")
        instance = get_object_or_404(PriceGroup, pk=group_id) if group_id else None
        form = PriceGroupForm(request.POST, instance=instance)
        if form.is_valid():
            form.save()
            messages.success(request, "تم حفظ مجموعة الأسعار.")
            return redirect("catalog-dashboard:price-groups")
    form = PriceGroupForm()
    return render(request, "catalog/dashboard/price_groups.html", {"groups": PriceGroup.objects.order_by("name", "id"), "form": form})


@catalog_access_required
def price_group_toggle(request, group_id):
    group = get_object_or_404(PriceGroup, pk=group_id)
    if request.method == "POST":
        group.is_active = not group.is_active
        group.save(update_fields=["is_active", "updated_at"])
        messages.success(request, "تم تحديث حالة مجموعة الأسعار.")
    return redirect("catalog-dashboard:price-groups")


@catalog_access_required
def products_export_csv(request):
    qs = _product_queryset(request)
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="catalog-products.csv"'
    response.write("\ufeff")
    writer = csv.writer(response)
    writer.writerow(["المعرف", "الاسم", "SKU", "المتجر", "السعر", "سعر التخفيض", "العملة", "المخزون", "المحجوز", "متاح", "منشور", "ترند", "التقييم", "المبيعات", "آخر تحديث"])
    for product in qs.iterator():
        writer.writerow([
            product.pk, product.name, product.sku, product.vendor.store_name, product.price, product.sale_price or "",
            product.currency, product.stock, product.reserved_stock, product.available_stock, "نعم" if product.is_published else "لا",
            "نعم" if product.is_trending else "لا", product.rating, product.sold_count, product.updated_at.isoformat(),
        ])
    return response