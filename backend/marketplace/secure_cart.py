from collections import defaultdict
from decimal import Decimal

from django.db import transaction
from django.utils import timezone
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.exceptions import ValidationError

from .models import Coupon, Product
from .models_extended import City, ProductVariant
from .models_extra import VendorCityShipping
from .services import PricingEngine


class SecureCartCalculateView(APIView):
    permission_classes = [AllowAny]

    @transaction.atomic
    def post(self, request):
        rows = request.data.get("items") or []
        if not isinstance(rows, list) or not rows:
            raise ValidationError({"items": "السلة فارغة"})

        city_id = request.data.get("city_id")
        city = City.objects.filter(id=city_id, is_active=True).first() if city_id else None
        if city_id and not city:
            raise ValidationError({"city_id": "المدينة غير صالحة"})

        vendor_subtotals = defaultdict(Decimal)
        vendor_shipping = defaultdict(lambda: Decimal("0.00"))
        subtotal = Decimal("0.00")
        lines = []
        errors = []
        for row in rows:
            try:
                product = Product.objects.select_for_update().select_related("vendor").get(
                    pk=int(row["product_id"]), is_published=True, vendor__status="active"
                )
                quantity = int(row.get("quantity", 1))
            except (KeyError, TypeError, ValueError, Product.DoesNotExist):
                errors.append("أحد المنتجات غير متاح")
                continue
            if quantity < 1:
                errors.append(f"الكمية غير صالحة للمنتج {product.name}")
                continue

            variant = None
            if row.get("variant_id") not in (None, ""):
                try:
                    variant = ProductVariant.objects.select_for_update().get(
                        id=int(row["variant_id"]), product=product, is_active=True
                    )
                except (TypeError, ValueError, ProductVariant.DoesNotExist):
                    errors.append(f"الخيار المحدد للمنتج {product.name} غير متاح")
                    continue
            available = variant.available_stock if variant else product.available_stock
            if available < quantity:
                errors.append(f"المتوفر من {product.name}: {available}")
                continue

            pricing = PricingEngine.calculate(product, city, quantity)
            unit_price = variant.price_override if variant and variant.price_override is not None else pricing["unit_final_price"]
            line_total = unit_price * quantity
            subtotal += line_total
            vendor_subtotals[product.vendor_id] += line_total
            lines.append({"product_id": product.id, "vendor_id": product.vendor_id, "variant_id": variant.id if variant else None, "quantity": quantity, "unit_price": str(unit_price), "line_total": str(line_total), "color": variant.color if variant else str(row.get("color", "")), "size": variant.size if variant else str(row.get("size", ""))})

        if errors:
            return Response({"valid": False, "errors": errors, "lines": lines}, status=400)

        coupon = None
        discount = Decimal("0.00")
        coupon_code = str(request.data.get("coupon_code", "")).strip()
        if coupon_code:
            coupon = Coupon.objects.select_for_update().filter(code__iexact=coupon_code).first()
            if not coupon or not coupon.is_active:
                return Response({"valid": False, "errors": ["الكوبون غير صالح أو غير نشط"]}, status=400)
            now = timezone.now()
            if coupon.starts_at and now < coupon.starts_at:
                return Response({"valid": False, "errors": ["الكوبون لم يبدأ بعد"]}, status=400)
            if coupon.ends_at and now > coupon.ends_at:
                return Response({"valid": False, "errors": ["انتهت صلاحية الكوبون"]}, status=400)
            if coupon.usage_limit is not None and coupon.used_count >= coupon.usage_limit:
                return Response({"valid": False, "errors": ["استُنفدت مرات استخدام الكوبون"]}, status=400)
            if coupon.assigned_to.exists() and (not request.user.is_authenticated or not coupon.assigned_to.filter(pk=request.user.pk).exists()):
                return Response({"valid": False, "errors": ["هذا الكوبون غير متاح لهذا الحساب"]}, status=400)
            if subtotal < coupon.minimum_order:
                return Response({"valid": False, "errors": [f"الحد الأدنى للطلب هو {coupon.minimum_order}"]}, status=400)
            discount = (subtotal * coupon.discount_percent / Decimal("100")).quantize(Decimal("0.01")) if coupon.discount_percent else coupon.discount_amount
            discount = min(discount, subtotal)

        if city:
            for vendor_id in vendor_subtotals:
                vendor_shipping[vendor_id] = VendorCityShipping.objects.filter(vendor_id=vendor_id, city_id=city.id, is_active=True).values_list("fee", flat=True).first() or Decimal("0.00")
        shipping_fee = sum(vendor_shipping.values(), Decimal("0.00"))
        total = max(Decimal("0.00"), subtotal - discount + shipping_fee)
        return Response({
            "valid": True,
            "subtotal": str(subtotal),
            "shipping_fee": str(shipping_fee),
            "shipping_by_vendor": {str(k): str(v) for k, v in vendor_shipping.items()},
            "discount": str(discount),
            "total": str(total),
            "currency": str(request.data.get("currency", "YER")).upper(),
            "coupon_code": coupon.code if coupon else None,
            "lines": lines,
        })
