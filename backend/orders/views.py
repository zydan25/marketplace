from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_http_methods

from .forms import ShipmentForm
from .models import InventoryReservation, Order, Payment, Shipment, VendorOrder


@login_required
@require_GET
def dashboard(request):
    user = request.user
    allowed = user.is_staff or getattr(user, "role", None) in {"admin", "vendor"}
    if not allowed:
        return render(request, "admin/domains/dashboard.html", {"error": "لا تملك صلاحية إدارة الطلبات."}, status=403)
    orders = Order.objects.all()
    vendor_orders = VendorOrder.objects.all()
    shipments = Shipment.objects.all()
    reservations = InventoryReservation.objects.filter(status="active")
    payments = Payment.objects.all()
    if getattr(user, "role", None) == "vendor" and not user.is_staff:
        vendor_orders = vendor_orders.filter(vendor__owner=user)
        orders = orders.filter(vendor_orders__vendor__owner=user).distinct()
        shipments = shipments.filter(vendor_order__vendor__owner=user)
        reservations = reservations.filter(order_item__vendor__owner=user)
        payments = payments.filter(order__vendor_orders__vendor__owner=user).distinct()
    return render(request, "admin/domains/dashboard.html", {
        "domain_title": "إدارة الطلبات والمخزون",
        "domain_key": "orders",
        "stats": [
            {"label": "الطلبات", "value": orders.count()},
            {"label": "طلبات التجار", "value": vendor_orders.count()},
            {"label": "الشحنات", "value": shipments.count()},
            {"label": "حجوزات المخزون النشطة", "value": reservations.count()},
            {"label": "الدفعات", "value": payments.count()},
        ],
        "api_prefix": "/api/v2/orders/",
    })


def _render_form(request, form, title, cancel_url):
    return render(request, "admin/domains/form.html", {"title": title, "form": form, "cancel_url": cancel_url})


@login_required
@require_http_methods(["GET", "POST"])
def shipment_form(request, pk):
    user = request.user
    if not (user.is_staff or getattr(user, "role", None) in {"admin", "vendor"}):
        return render(request, "admin/domains/form.html", {"title": "الشحنة", "error": "غير مصرح."}, status=403)
    queryset = Shipment.objects.all()
    if getattr(user, "role", None) == "vendor" and not user.is_staff:
        queryset = queryset.filter(vendor_order__vendor__owner=user)
    shipment = get_object_or_404(queryset, pk=pk)
    form = ShipmentForm(request.POST or None, instance=shipment)
    if request.method == "POST" and form.is_valid():
        obj = form.save(commit=False)
        obj.shipped_at = shipment.shipped_at
        obj.delivered_at = shipment.delivered_at
        if obj.status in {Shipment.Status.SHIPPED, Shipment.Status.IN_TRANSIT} and not obj.shipped_at:
            from django.utils import timezone
            obj.shipped_at = timezone.now()
        if obj.status == Shipment.Status.DELIVERED and not obj.delivered_at:
            from django.utils import timezone
            obj.delivered_at = timezone.now()
        obj.save()
        return redirect("admin-dashboard-orders")
    return _render_form(request, form, "تحديث الشحنة", "/admin/dashboard/orders/")
