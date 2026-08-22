from decimal import Decimal, InvalidOperation
import uuid

from django.db import transaction
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Order, OrderItem, Product, VendorProfile
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
        qs = Order.objects.select_related("customer").prefetch_related("items", "items__vendor", "items__product")
        if user.is_staff or user.role == "admin":
            return qs
        if user.role == "vendor":
            return qs.filter(items__vendor__owner=user).distinct()
        return qs.filter(customer=user)

    @staticmethod
    def _decimal(value, field_name):
        try:
            result = Decimal(str(value))
        except (InvalidOperation, TypeError, ValueError):
            raise ValidationError({field_name: "قيمة مالية غير صالحة"})
        if result < 0:
            raise ValidationError({field_name: "لا يمكن أن تكون القيمة سالبة"})
        return result

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

        prepared = []
        subtotal = Decimal("0")

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
                    variant = ProductVariant.objects.select_for_update().get(
                        id=int(row["variant_id"]), product=product
                    )
                except (ProductVariant.DoesNotExist, TypeError, ValueError):
                    raise ValidationError({"items": f"الخيار المحدد للمنتج {product.name} غير صالح"})

            available = variant.available_stock if variant else product.stock
            if available < quantity:
                raise ValidationError({"items": f"الكمية غير متاحة للمنتج {product.name}"})

            pricing = PricingEngine.calculate(product, city, quantity)
            unit_price = variant.price_override if variant and variant.price_override is not None else pricing["unit_final_price"]
            line_total = unit_price * quantity
            subtotal += line_total
            prepared.append((product, variant, quantity, row, unit_price, line_total))

        # Never trust client-provided shipping/discount totals. They are server-calculated.
        shipping_fee = city.shipping_fee if city else Decimal("0")
        discount = Decimal("0")
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

        for product, variant, quantity, row, unit_price, line_total in prepared:
            vendor = product.vendor
            commission = (line_total * vendor.commission_percent / Decimal("100")).quantize(Decimal("0.01"))
            OrderItem.objects.create(
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
                commission=commission,
                vendor_net=line_total - commission,
            )
            if variant:
                variant.stock -= quantity
                variant.save(update_fields=["stock", "updated_at"])
            else:
                product.stock -= quantity
                product.save(update_fields=["stock", "updated_at"])
            product.sold_count += quantity
            product.save(update_fields=["sold_count", "updated_at"])

        return Response(OrderSerializer(order, context={"request": request}).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def update_status(self, request, pk=None):
        order = self.get_object()
        user = request.user
        if user.role == "vendor":
            vendor_items = order.items.filter(vendor__owner=user)
            if not vendor_items.exists():
                raise PermissionDenied("لا تملك هذا الطلب")
            new_status = str(request.data.get("status", ""))
            allowed = {"confirmed", "processing", "shipped"}
            if new_status not in allowed:
                raise ValidationError({"status": "التاجر يستطيع تأكيد الطلب أو تجهيزه أو شحنه فقط"})
        elif not (user.is_staff or user.role == "admin"):
            raise PermissionDenied("لا تملك صلاحية تغيير حالة الطلب")
        else:
            new_status = str(request.data.get("status", ""))
            valid = {choice.value for choice in Order.Status}
            if new_status not in valid:
                raise ValidationError({"status": "حالة الطلب غير صالحة"})

        order.status = new_status
        order.save(update_fields=["status", "updated_at"])
        return Response(OrderSerializer(order, context={"request": request}).data)
