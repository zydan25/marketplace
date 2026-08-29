from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.text import slugify

from .forms import CatalogOptionForm, PriceGroupForm, ProductVariantForm
from .models import CatalogOption, PriceGroup, ProductVariant
from .dashboard import catalog_access_required


@catalog_access_required
def option_update(request, option_id):
    option = get_object_or_404(CatalogOption, pk=option_id)
    form = CatalogOptionForm(request.POST or None, instance=option)
    if request.method == "POST" and form.is_valid():
        option = form.save(commit=False)
        if not option.slug:
            option.slug = slugify(option.name, allow_unicode=True) or f"option-{option.pk}"
        option.save()
        messages.success(request, "تم حفظ خيار الكتالوج.")
        return redirect("catalog-dashboard:options")
    return render(request, "catalog/dashboard/option_form.html", {"form": form, "option": option})


@catalog_access_required
def price_group_update(request, group_id):
    group = get_object_or_404(PriceGroup, pk=group_id)
    form = PriceGroupForm(request.POST or None, instance=group)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "تم حفظ مجموعة الأسعار.")
        return redirect("catalog-dashboard:price-groups")
    return render(request, "catalog/dashboard/price_group_form.html", {"form": form, "group": group})


@catalog_access_required
def variant_edit(request, variant_id):
    variant = get_object_or_404(ProductVariant.objects.select_related("product"), pk=variant_id)
    form = ProductVariantForm(request.POST or None, instance=variant)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "تم حفظ الصنف.")
        return redirect("catalog-dashboard:product-detail", product_id=variant.product_id)
    return render(request, "catalog/dashboard/variant_form.html", {"form": form, "variant": variant, "product": variant.product})