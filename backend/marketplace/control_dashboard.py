from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.db.models.deletion import ProtectedError
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .dashboard import dashboard_access_required
from vendors.forms import VendorProfileForm
from vendors.models import VendorProfile
from vendors.services import set_vendor_status


STORE_STATUSES = {"active", "pending", "suspended"}


def _stores_context(request, form=None, edit_vendor=None, form_mode="create"):
    queryset = (
        VendorProfile.objects.select_related("owner")
        .annotate(
            product_count=Count("products", distinct=True),
            order_count=Count("vendor_orders", distinct=True),
        )
    )

    q = request.GET.get("q", "").strip()
    status = request.GET.get("status", "").strip()
    sort = request.GET.get("sort", "newest").strip()

    if q:
        queryset = queryset.filter(
            Q(store_name__icontains=q)
            | Q(slug__icontains=q)
            | Q(phone__icontains=q)
            | Q(owner__phone__icontains=q)
            | Q(owner__email__icontains=q)
            | Q(owner__first_name__icontains=q)
            | Q(owner__last_name__icontains=q)
        )
    if status in STORE_STATUSES:
        queryset = queryset.filter(status=status)

    if sort == "name":
        queryset = queryset.order_by("store_name")
    elif sort == "products":
        queryset = queryset.order_by("-product_count", "store_name")
    elif sort == "orders":
        queryset = queryset.order_by("-order_count", "store_name")
    else:
        sort = "newest"
        queryset = queryset.order_by("-created_at")

    paginator = Paginator(queryset, 15)
    page = paginator.get_page(request.GET.get("page"))

    stats = {
        "total": VendorProfile.objects.count(),
        "active": VendorProfile.objects.filter(status="active").count(),
        "pending": VendorProfile.objects.filter(status="pending").count(),
        "suspended": VendorProfile.objects.filter(status="suspended").count(),
    }

    return {
        "page": page,
        "q": q,
        "status": status,
        "sort": sort,
        "stats": stats,
        "form": form,
        "edit_vendor": edit_vendor,
        "form_mode": form_mode,
        "store_form_open": bool(form and (edit_vendor or getattr(form, "errors", None))),
    }


@dashboard_access_required
def stores(request):
    edit_vendor_id = request.GET.get("edit")
    edit_vendor = None
    form = None
    form_mode = "create"

    if request.method == "POST":
        vendor_id = request.POST.get("vendor_id") or ""
        if vendor_id:
            edit_vendor = get_object_or_404(VendorProfile, pk=vendor_id)
            form_mode = "edit"
            form = VendorProfileForm(request.POST, request.FILES, instance=edit_vendor)
        else:
            form = VendorProfileForm(request.POST, request.FILES)

        if form.is_valid():
            vendor = form.save()
            messages.success(request, f"تم حفظ المتجر «{vendor.store_name}» بنجاح.")
            return redirect("admin-control-stores")

        form_mode = "edit" if edit_vendor else "create"
    elif edit_vendor_id:
        edit_vendor = get_object_or_404(
            VendorProfile.objects.select_related("owner"), pk=edit_vendor_id
        )
        form_mode = "edit"
        form = VendorProfileForm(instance=edit_vendor)
    else:
        form = VendorProfileForm(initial={"status": "active", "commission_percent": 10})

    return render(
        request,
        "admin/control/stores.html",
        _stores_context(request, form, edit_vendor, form_mode),
    )


@dashboard_access_required
@require_POST
def store_status(request, vendor_id, status):
    if status not in STORE_STATUSES:
        return redirect("admin-control-stores")
    vendor = get_object_or_404(VendorProfile, pk=vendor_id)
    set_vendor_status(vendor, status)
    messages.success(
        request,
        f"تم تغيير حالة متجر «{vendor.store_name}» إلى {vendor.get_status_display()}.",
    )
    return redirect(request.POST.get("next") or "admin-control-stores")


@dashboard_access_required
@require_POST
def store_delete(request, vendor_id):
    vendor = get_object_or_404(VendorProfile, pk=vendor_id)
    has_products = vendor.products.exists()
    has_orders = vendor.vendor_orders.exists() or vendor.order_items.exists()

    if has_products or has_orders:
        messages.error(
            request,
            "لا يمكن حذف متجر مرتبط بمنتجات أو طلبات. استخدم «إيقاف المتجر» للحفاظ على السجل والارتباطات.",
        )
        return redirect(request.POST.get("next") or "admin-control-stores")

    name = vendor.store_name
    try:
        vendor.delete()
    except ProtectedError:
        messages.error(
            request,
            "تعذر حذف المتجر بسبب ارتباطات محمية في النظام. تم الإبقاء عليه دون تغيير.",
        )
    else:
        messages.success(request, f"تم حذف المتجر «{name}».")
    return redirect(request.POST.get("next") or "admin-control-stores")
