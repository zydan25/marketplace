import csv
from functools import wraps

from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from marketplace.models import Product, User
from marketplace.marketplace_models import VendorOrder

from .forms import VendorApplicationReviewForm, VendorProfileForm
from .models import VendorApplication, VendorProfile
from .services import approve_application, create_vendor_for_user, reject_application, set_vendor_status


def vendor_admin_required(view):
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        user = request.user
        if not user.is_authenticated:
            return redirect(f"/admin/dashboard/login/?next={request.path}")
        if not (user.is_staff or user.role == "admin"):
            return HttpResponse("ليس لديك صلاحية الوصول إلى إدارة التجار.", status=403)
        return view(request, *args, **kwargs)

    return wrapped


@vendor_admin_required
def overview(request):
    vendors = VendorProfile.objects.all()
    context = {
        "total": vendors.count(),
        "active": vendors.filter(status="active").count(),
        "pending": vendors.filter(status="pending").count(),
        "suspended": vendors.filter(status="suspended").count(),
        "applications_pending": VendorApplication.objects.filter(status=VendorApplication.Status.PENDING).count(),
        "products": Product.objects.count(),
        "recent_vendors": vendors.select_related("owner")[:8],
        "recent_applications": VendorApplication.objects.select_related("applicant")[:8],
    }
    return render(request, "vendors/dashboard/overview.html", context)


@vendor_admin_required
def vendors(request):
    queryset = VendorProfile.objects.select_related("owner").annotate(product_count=Count("products", distinct=True), order_count=Count("vendor_orders", distinct=True))
    q = request.GET.get("q", "").strip()
    status_filter = request.GET.get("status", "").strip()
    if q:
        queryset = queryset.filter(Q(store_name__icontains=q) | Q(slug__icontains=q) | Q(owner__phone__icontains=q) | Q(owner__email__icontains=q))
    if status_filter in {"active", "pending", "suspended"}:
        queryset = queryset.filter(status=status_filter)
    paginator = Paginator(queryset.order_by("-created_at"), 20)
    page = paginator.get_page(request.GET.get("page"))
    return render(request, "vendors/dashboard/vendors.html", {"page": page, "q": q, "status_filter": status_filter})


@vendor_admin_required
def vendor_create(request):
    if request.method == "POST":
        form = VendorProfileForm(request.POST, request.FILES)
        if form.is_valid():
            owner = form.cleaned_data["owner"]
            data = {field: form.cleaned_data[field] for field in ["store_name", "slug", "description", "logo", "cover", "phone", "address", "status", "commission_percent", "settings"]}
            try:
                create_vendor_for_user(owner, **data)
            except Exception as exc:
                form.add_error(None, str(exc))
            else:
                messages.success(request, "تم إنشاء التاجر وربط المتجر بالحساب.")
                return redirect("vendors-dashboard:vendors")
    else:
        form = VendorProfileForm(initial={"status": "active", "commission_percent": 10})
    return render(request, "vendors/dashboard/vendor_form.html", {"form": form, "mode": "create"})


@vendor_admin_required
def vendor_detail(request, vendor_id):
    vendor = get_object_or_404(VendorProfile.objects.select_related("owner"), pk=vendor_id)
    products = Product.objects.filter(vendor_id=vendor.pk).order_by("-created_at")[:10]
    orders = VendorOrder.objects.filter(vendor_id=vendor.pk).select_related("order").order_by("-created_at")[:10]
    return render(request, "vendors/dashboard/vendor_detail.html", {"vendor": vendor, "products": products, "orders": orders})


@vendor_admin_required
def vendor_update(request, vendor_id):
    vendor = get_object_or_404(VendorProfile.objects.select_related("owner"), pk=vendor_id)
    if request.method == "POST":
        form = VendorProfileForm(request.POST, request.FILES, instance=vendor)
        if form.is_valid():
            form.save()
            messages.success(request, "تم حفظ بيانات التاجر.")
            return redirect("vendors-dashboard:vendor-detail", vendor_id=vendor.pk)
    else:
        form = VendorProfileForm(instance=vendor)
    return render(request, "vendors/dashboard/vendor_form.html", {"form": form, "vendor": vendor, "mode": "edit"})


@vendor_admin_required
def vendor_status(request, vendor_id, status):
    vendor = get_object_or_404(VendorProfile, pk=vendor_id)
    if request.method != "POST":
        return redirect("vendors-dashboard:vendor-detail", vendor_id=vendor.pk)
    set_vendor_status(vendor, status)
    messages.success(request, "تم تحديث حالة التاجر.")
    return redirect("vendors-dashboard:vendor-detail", vendor_id=vendor.pk)


@vendor_admin_required
def applications(request):
    queryset = VendorApplication.objects.select_related("applicant", "reviewed_by")
    status_filter = request.GET.get("status", "pending")
    q = request.GET.get("q", "").strip()
    if status_filter in {"pending", "approved", "rejected"}:
        queryset = queryset.filter(status=status_filter)
    if q:
        queryset = queryset.filter(Q(store_name__icontains=q) | Q(phone__icontains=q) | Q(applicant__phone__icontains=q))
    paginator = Paginator(queryset.order_by("-created_at"), 20)
    page = paginator.get_page(request.GET.get("page"))
    return render(request, "vendors/dashboard/applications.html", {"page": page, "status_filter": status_filter, "q": q})


@vendor_admin_required
def application_detail(request, application_id):
    application = get_object_or_404(VendorApplication.objects.select_related("applicant", "reviewed_by"), pk=application_id)
    form = VendorApplicationReviewForm(request.POST or None, instance=application)
    return render(request, "vendors/dashboard/application_detail.html", {"application": application, "form": form})


@vendor_admin_required
def application_action(request, application_id, action):
    application = get_object_or_404(VendorApplication, pk=application_id)
    if request.method != "POST":
        return redirect("vendors-dashboard:application-detail", application_id=application.pk)
    form = VendorApplicationReviewForm(request.POST, instance=application)
    if action == "approve":
        try:
            vendor, _ = approve_application(application, request.user)
        except Exception as exc:
            messages.error(request, str(exc))
        else:
            messages.success(request, f"تم اعتماد الطلب وإنشاء/تفعيل متجر {vendor.store_name}.")
    elif action == "reject" and form.is_valid():
        reject_application(application, request.user, form.cleaned_data.get("review_note", ""))
        messages.success(request, "تم رفض الطلب وتسجيل ملاحظة المراجعة.")
    return redirect("vendors-dashboard:application-detail", application_id=application.pk)


@vendor_admin_required
def export_csv(request):
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="vendors.csv"'
    response.write("\ufeff")
    writer = csv.writer(response)
    writer.writerow(["ID", "المتجر", "الرابط", "الهاتف", "الحالة", "العمولة", "المنتجات", "تاريخ الإنشاء"])
    for vendor in VendorProfile.objects.select_related("owner").annotate(product_count=Count("products", distinct=True)).order_by("-created_at"):
        writer.writerow([vendor.pk, vendor.store_name, vendor.slug, vendor.owner.phone, vendor.status, vendor.commission_percent, vendor.product_count, vendor.created_at.strftime("%Y-%m-%d %H:%M")])
    return response
