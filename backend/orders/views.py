from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.views.decorators.http import require_GET

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
