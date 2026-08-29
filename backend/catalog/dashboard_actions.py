from urllib.parse import urlencode

from django.contrib import messages
from django.shortcuts import redirect
from django.utils import timezone

from .dashboard import PRODUCT_BULK_ACTIONS, _product_queryset, catalog_access_required
from .models import Product


@catalog_access_required
def products_bulk(request):
    if request.method != "POST":
        return redirect("catalog-dashboard:products")

    action = request.POST.get("bulk_action", "")
    ids = [value for value in request.POST.getlist("selected_products") if value.isdigit()]
    query = request.GET.copy()
    target = "/admin/dashboard/catalog/products/"

    if action not in PRODUCT_BULK_ACTIONS:
        messages.warning(request, "اختر إجراءً جماعيًا صالحًا أولًا.")
    elif not ids:
        messages.warning(request, "حدد منتجًا واحدًا على الأقل أولًا.")
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

    return redirect(f"{target}?{urlencode(query, doseq=True)}" if query else target)