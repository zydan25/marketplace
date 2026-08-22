from collections import defaultdict
from datetime import timedelta
from decimal import Decimal
import uuid

from django.db import transaction
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .marketplace_models import InventoryReservation, Payment, Shipment, VendorOrder, VendorOrderItem
from .models import Order, OrderItem, OrderStatusHistory, Product
from .models_extended import City, ProductVariant
from .serializers import OrderSerializer
from .services import PricingEngine


SUPPORTED_CURRENCIES = {"YER", "SAR", "USD"}


class SecureOrderViewSet(viewsets.ModelViewSet):
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self):
        user = self.request.user
        qs = Order.objects.select_related("customer").prefetch_related(
            "items", "items__vendor", "items__product", "vendor_orders", "payment"
        )
        if user.is_staff or user.role == "admin":
            return qs
        if user.role == "vendor":
            return qs.filter(items__vendor__owner=user).distinct()
        return qs.filter(customer=user)

    @staticmethod
    def _distribute_shipping(groups, shipping_fee):
        if not groups or shipping_fee <= 0:
            return {vendor_id: Decimal("0.00") for vendor_id in groups}
        subtotal = sum(data["subtotal"] for data in groups.values()) or Decimal("1")
        result = {}
        allocated = Decimal("0.00")
        vendor_ids = list(groups)
        for vendor_id in vendor_ids[:-1]:
            fee = (shipping_fee * groups[vendor_id]["subtotal"] / subtotal).quantize(Decimal("0.01"))
            result[vendor_id] = fee
            allocated += fee
        result[vendor_ids[-1]] = shipping_fee - allocated
        return result

    @staticmethod
    def _sync_parent_status(order):
        statuses = list(order.vendor_orders.values_list("status", flat=True))
        if not statuses:
            return
        if all(s == "delivered" for s in statuses):
            parent = "delivered"
        elif all(s == "cancelled" for s in statuses):
            parent = "cancelled"
        elif any(s == "shipped" for s in statuses):
            parent = "shipped"
        elif any(s == "processing" for s in statuses):
            parent = "processing"
        elif any(s == "confirmed" for s in statuses):
            parent = "confirmed"
        else:
            parent = "pending"
        if order.status != parent:
            old_status = order.status
            order.status = parent
            order.save(update_fields=["status", "updated_at"])
            OrderStatusHistory.objects.create(order=order, old_status=old_status, new_status=parent, changed_by=None)

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        if request.user.role != "customer":
            raise PermissionDenied("إنشاء الطلبات متاح للعملاء فقط")
        rows = request.data.get("items")
        if not isinstance(rows, list) or not rows:
            raise ValidationError({"items": "السلة فارغة"})

        address = request.data.get("shipping_address") or {}
        city_id = address.get("city_id")
        city = City.objects.filter(id=city_id, is_active=True).first() if city_id else None
        if city_id and not city:
            raise ValidationError({"shipping_address": {"city_id": "المدينة غير صالحة"}})

        currency = str(request.data.get("currency", "YER")).upper()
        if currency not in SUPPORTED_CURRENCIES:
            raise ValidationError({"currency": "العملة غير مدعومة"})

        groups = defaultdict(lambda: {"vendor": None, "items": [], "subtotal": Decimal("0.00")})
        subtotal = Decimal("0.00")

        for row in rows:
            if not isinstance(row, dict):
                raise ValidationError({"items": "صيغة عنصر السلة غير صالحة"})
            try:
                product_id = int(row["product_id"])
                quantity = int(row.get("quantity", 1))
            except (KeyError, TypeError, ValueError):
                raise ValidationError({"items": "product_id وquantity مطلوبان بشكل صحيح"})
            if quantity < 1:
                raise ValidationError({"items": "الكمية يجب أن تكون 1 أو أكثر"})

            try:
                product = Product.objects.select_for_update().select_related("vendor").get(
                    pk=product_id, is_published=True, vendor__status="active"
                )
            except Product.DoesNotExist:
                raise ValidationError({"items": f"المنتج {product_id} غير موجود أو غير متاح"})

            variant = None
            if row.get("variant_id") not in (None, ""):
                try:
                    variant = ProductVariant.objects.select_for_update().get(id=int(row["variant_id"]), product=product)
                except (ProductVariant.DoesNotExist, TypeError, ValueError):
                    raise ValidationError({"items": f"الخيار المحدد للمنتج {product.name} غير صالح"})

            available = variant.available_stock if variant else product.stock
            if available < quantity:
                raise ValidationError({"items": f"الكمية غير متاحة للمنتج {product.name}"})

            pricing = PricingEngine.calculate(product, city, quantity)
            unit_price = variant.price_override if variant and variant.price_override is not None else pricing["unit_final_price"]
            line_total = unit_price * quantity
            subtotal += line_total
            groups[product.vendor_id]["vendor"] = product.vendor
            groups[product.vendor_id]["items"].append((product, variant, quantity, row, unit_price, line_total))
            groups[product.vendor_id]["subtotal"] += line_total

        shipping_fee = city.shipping_fee if city else Decimal("0.00")
        discount = Decimal("0.00")
        total = subtotal + shipping_fee
        order = Order.objects.create(
            customer=request.user,
            order_number=f"ORD-{timezone.now():%Y%m%d}-{uuid.uuid4().hex[:6].upper()}",
            subtotal=subtotal,
            shipping_fee=shipping_fee,
            discount=discount,
            total=total,
            currency=currency,
            shipping_address=address,
            payment_method=str(request.data.get("payment_method", "cash_on_delivery")),
            payment_status="pending",
            metadata={"pricing_source": "server", "api_version": "v1"},
        )

        shipping_by_vendor = self._distribute_shipping(groups, shipping_fee)
        for vendor_id, group in groups.items():
            vendor = group["vendor"]
            vendor_subtotal = group["subtotal"]
            vendor_shipping = shipping_by_vendor[vendor_id]
            vendor_total = vendor_subtotal + vendor_shipping
            commission = (vendor_subtotal * vendor.commission_percent / Decimal("100")).quantize(Decimal("0.01"))
            vendor_order = VendorOrder.objects.create(
                order=order,
                vendor=vendor,
                order_number=f"{order.order_number}-{vendor_id}",
                subtotal=vendor_subtotal,
                shipping_fee=vendor_shipping,
                total=vendor_total,
                commission=commission,
                vendor_net=vendor_subtotal - commission + vendor_shipping,
                currency=currency,
            )
            Shipment.objects.create(vendor_order=vendor_order)

            for product, variant, quantity, row, unit_price, line_total in group["items"]:
                item_commission = (line_total * vendor.commission_percent / Decimal("100")).quantize(Decimal("0.01"))
                order_item = OrderItem.objects.create(
                    order=order,
                    vendor=vendor,
                    product=product,
                    name_snapshot=product.name,
                    sku_snapshot=variant.sku if variant else product.sku,
                    quantity=quantity,
                    unit_price=unit_price,
                    color=variant.color if variant else str(row.get("color", "")),
                    size=variant.size if variant else str(row.get("size", "")),
                    vendor_total=line_total,
                    commission=item_commission,
                    vendor_net=line_total - item_commission,
                )
                VendorOrderItem.objects.create(vendor_order=vendor_order, order_item=order_item)

                if variant is not None:
                    variant.reserved_stock += quantity
                    variant.save(update_fields=["reserved_stock", "updated_at"])
                    InventoryReservation.objects.create(order=order, variant=variant, quantity=quantity, expires_at=timezone.now() + timedelta(minutes=30))
                else:
                    product.stock -= quantity
                    product.save(update_fields=["stock", "updated_at"])
                    InventoryReservation.objects.create(order=order, product=product, quantity=quantity, expires_at=timezone.now() + timedelta(minutes=30))
                product.sold_count += quantity
                product.save(update_fields=["sold_count", "updated_at"])

        Payment.objects.create(
            order=order,
            provider="manual" if request.data.get("payment_method", "cash_on_delivery") == "cash_on_delivery" else "pending",
            method=str(request.data.get("payment_method", "cash_on_delivery")),
            amount=total,
            currency=currency,
            status=Payment.Status.PENDING,
            metadata={"source": "checkout"},
        )
        return Response(OrderSerializer(order, context={"request": request}).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    @transaction.atomic
    def update_status(self, request, pk=None):
        order = self.get_object()
        user = request.user
        new_status = str(request.data.get("status", ""))
        if user.role == "vendor":
            vendor_order = order.vendor_orders.filter(vendor__owner=user).select_for_update().first()
            if not vendor_order:
                raise PermissionDenied("لا تملك هذا الطلب")
            allowed = {"confirmed", "processing", "shipped", "delivered", "cancelled"}
            if new_status not in allowed:
                raise ValidationError({"status": "حالة التاجر غير صالحة"})
            vendor_order.status = new_status
            vendor_order.save(update_fields=["status", "updated_at"])
            self._sync_parent_status(order)
            return Response({"vendor_order_id": vendor_order.id, "status": vendor_order.status})

        if not (user.is_staff or user.role == "admin"):
            raise PermissionDenied("لا تملك صلاحية تغيير حالة الطلب")
        if new_status not in {choice.value for choice in Order.Status}:
            raise ValidationError({"status": "حالة الطلب غير صالحة"})
        old_status = order.status
        order.status = new_status
        order.save(update_fields=["status", "updated_at"])
        OrderStatusHistory.objects.create(order=order, old_status=old_status, new_status=new_status, changed_by=user)
        if new_status in {"cancelled", "refunded"}:
            for reservation in order.inventory_reservations.select_for_update().filter(status="active"):
                if reservation.variant_id:
                    variant = reservation.variant
                    variant.reserved_stock = max(0, variant.reserved_stock - reservation.quantity)
                    variant.save(update_fields=["reserved_stock", "updated_at"])
                elif reservation.product_id:
                    product = reservation.product
                    product.stock += reservation.quantity
                    product.save(update_fields=["stock", "updated_at"])
                reservation.status = "released"
                reservation.save(update_fields=["status", "updated_at"])
        return Response(OrderSerializer(order, context={"request": request}).data)
