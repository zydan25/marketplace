import json
import re

from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from catalog.models import Product
from marketplace.dashboard import dashboard_access_required
from orders.models import OrderItem
from vendors.forms import VendorApplicationReviewForm
from vendors.models import VendorApplication
from vendors.services import approve_application, reject_application

from . import control_v10 as core
from . import control_v9 as legacy
from . import erp_style_dashboard_bridge as shell_module

APPLICATIONS_URL = "/admin/dashboard/control/applications/"


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
@require_http_methods(["GET"])
def product_detail(request, product_id):
    product = get_object_or_404(
        Product.objects.select_related("vendor", "vendor__owner").prefetch_related("categories", "store_categories", "variants", "image_items"),
        pk=product_id,
    )
    items = OrderItem.objects.filter(product=product).select_related("order", "vendor", "order__customer").order_by("-created_at")
    totals = items.aggregate(units=Sum("quantity"), revenue=Sum("vendor_total"))
    return render(request, "admin/control/inner/product_detail_v10.html", {
        "product": product,
        "items": items[:40],
        "report": {"units": totals["units"] or 0, "revenue": totals["revenue"] or 0, "orders": items.values("order_id").distinct().count()},
        "json_colors": json.dumps(product.colors or [], ensure_ascii=False, indent=2),
        "json_sizes": json.dumps(product.sizes or [], ensure_ascii=False, indent=2),
        "json_hashtags": json.dumps(product.hashtags or [], ensure_ascii=False, indent=2),
        "json_details": json.dumps(product.details or {}, ensure_ascii=False, indent=2),
    })


@dashboard_access_required
@require_http_methods(["POST"])
def application_review(request, application_id):
    application = get_object_or_404(VendorApplication, pk=application_id)
    action = request.POST.get("action", "").strip()
    if action not in {"approve", "reject"}:
        messages.error(request, "قرار المراجعة غير صالح.")
        return redirect(APPLICATIONS_URL)
    form = VendorApplicationReviewForm(request.POST, instance=application)
    if action == "approve":
        try:
            vendor, _ = approve_application(application, request.user)
            messages.success(request, f"تم اعتماد الطلب وإنشاء/تفعيل متجر «{vendor.store_name}».")
        except Exception as exc:
            messages.error(request, f"تعذر اعتماد الطلب: {exc}")
    elif form.is_valid():
        reject_application(application, request.user, form.cleaned_data.get("review_note", ""))
        messages.success(request, "تم رفض طلب المتجر وتسجيل الملاحظة.")
    else:
        messages.error(request, "تعذر حفظ ملاحظة المراجعة.")
    return redirect(APPLICATIONS_URL)


legacy._product_editor_context = _product_editor_context
legacy.product_detail = product_detail
core.product_detail = product_detail
core._product_editor_context = _product_editor_context


def _wrap_control_response(request, response):
    """Return control fragments for AJAX, but a complete responsive ERP shell for direct page loads."""
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return response
    if response.status_code < 200 or response.status_code >= 300:
        return response
    content_type = response.get("Content-Type", "")
    if "text/html" not in content_type:
        return response

    fragment_html = response.content.decode("utf-8")
    shell_response = shell_module.erp_style_dashboard(request)
    shell_html = shell_response.content.decode("utf-8")
    match = re.search(r'(<main class="content">)(.*?)(</main>)', shell_html, re.S)
    if not match:
        return response
    wrapped = shell_html[:match.start(2)] + fragment_html + shell_html[match.end(2):]
    return HttpResponse(wrapped, content_type="text/html; charset=utf-8")


def _shell(view):
    def wrapped(request, *args, **kwargs):
        return _wrap_control_response(request, view(request, *args, **kwargs))

    wrapped.__name__ = getattr(view, "__name__", "control_view")
    wrapped.__doc__ = getattr(view, "__doc__", None)
    return wrapped


control_products = _shell(legacy.control_products)
control_stores = _shell(legacy.control_stores)
control_categories = _shell(core.control_categories)
control_inventory = _shell(core.control_inventory)
control_orders = _shell(core.control_orders)
order_detail = _shell(core.order_detail)
store_detail = _shell(core.store_detail)
control_applications = _shell(core.control_applications)
control_payments = _shell(core.control_payments)
control_finance = _shell(core.control_finance)
control_variants = _shell(core.control_variants)

order_status = core.order_status
order_customer_message = core.order_customer_message
order_chat_message = core.order_chat_message
order_chat_open = core.order_chat_open
store_design_save = core.store_design_save
store_section_save = core.store_section_save
store_section_delete = core.store_section_delete
store_media_save = core.store_media_save
store_media_delete = core.store_media_delete
store_category_save = core.store_category_save
store_category_delete = core.store_category_delete
store_branch_save = core.store_branch_save
store_branch_delete = core.store_branch_delete
