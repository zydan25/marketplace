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

from .marketplace_models import CouponRedemption, InventoryReservation, Payment, VendorLedgerEntry, VendorOrder, VendorOrderItem, Shipment
from .models import Coupon, Order, OrderItem, OrderStatusHistory, Product, VendorPayout
from .models_extended import City, ProductVariant
from .order_chat_models import OrderChat
from .serializers import OrderSerializer
from .services import PricingEngine

SUPPORTED_CURRENCIES = {"YER", "SAR", "USD"}

class SecureOrderViewSet(viewsets.ModelViewSet):
    serializer_class=OrderSerializer; permission_classes=[IsAuthenticated]; http_method_names=["get","post","head","options"]
    def get_queryset(self):
        user=self.request.user; qs=Order.objects.select_related("customer").prefetch_related("items","items__vendor","items__product","vendor_orders","payment","coupon_redemption")
        if user.is_staff or user.role=="admin": return qs
        if user.role=="vendor": return qs.filter(items__vendor__owner=user).distinct()
        return qs.filter(customer=user)
    @staticmethod
    def _distribute_amount(groups,amount):
        if not groups or amount<=0:return {vendor_id:Decimal("0.00") for vendor_id in groups}
        subtotal=sum(data["subtotal"] for data in groups.values()) or Decimal("1"); result={}; allocated=Decimal("0.00"); vendor_ids=list(groups)
        for vendor_id in vendor_ids[:-1]: share=(amount*groups[vendor_id]["subtotal"]/subtotal).quantize(Decimal("0.01")); result[vendor_id]=share; allocated+=share
        result[vendor_ids[-1]]=amount-allocated; return result
    @staticmethod
    def _sync_parent_status(order):
        statuses=list(order.vendor_orders.values_list("status",flat=True))
        if not statuses:return
        if all(s=="delivered" for s in statuses): parent="delivered"
        elif all(s=="cancelled" for s in statuses): parent="cancelled"
        elif any(s in {"delivered","cancelled"} for s in statuses): parent="partially_fulfilled"
        elif any(s=="shipped" for s in statuses): parent="shipped"
        elif any(s=="processing" for s in statuses): parent="processing"
        elif any(s=="confirmed" for s in statuses): parent="confirmed"
        else: parent="pending"
        if order.status!=parent:
            old_status=order.status; order.status=parent; order.save(update_fields=["status","updated_at"]); OrderStatusHistory.objects.create(order=order,old_status=old_status,new_status=parent,changed_by=None)
    @staticmethod
    def _accrue_vendor_sale(vendor_order):
        reference=f"SALE-{vendor_order.id}"
        if VendorLedgerEntry.objects.filter(reference=reference).exists():return
        previous=VendorLedgerEntry.objects.filter(vendor=vendor_order.vendor,currency=vendor_order.currency).order_by("-id").first(); before=previous.balance_after if previous else Decimal("0.00")
        VendorLedgerEntry.objects.create(vendor=vendor_order.vendor,vendor_order=vendor_order,entry_type=VendorLedgerEntry.Types.SALE,amount=vendor_order.vendor_net,balance_after=before+vendor_order.vendor_net,currency=vendor_order.currency,reference=reference,metadata={"source":"vendor_order_delivered"})
    @staticmethod
    def _commit_vendor_order_inventory(vendor_order):
        for link in vendor_order.items.select_related("order_item__product").all():
            item=link.order_item; reservation=InventoryReservation.objects.select_for_update().filter(order_item=item).exclude(status=InventoryReservation.Status.RELEASED).first()
            if reservation:
                if reservation.status==InventoryReservation.Status.ACTIVE:
                    if reservation.variant_id:
                        variant=reservation.variant; variant.reserved_stock=max(0,variant.reserved_stock-reservation.quantity); variant.stock=max(0,variant.stock-reservation.quantity); variant.save(update_fields=["reserved_stock","stock","updated_at"])
                    elif reservation.product_id:
                        product=reservation.product; product.reserved_stock=max(0,product.reserved_stock-reservation.quantity); product.stock=max(0,product.stock-reservation.quantity); product.save(update_fields=["reserved_stock","stock","updated_at"])
                    reservation.status=InventoryReservation.Status.COMMITTED; reservation.save(update_fields=["status","updated_at"])
                elif reservation.status==InventoryReservation.Status.EXPIRED: raise ValidationError({"order":"لا يمكن تسليم الطلب لأن حجز المخزون منتهي."})
            item.product.sold_count=max(0,item.product.sold_count)+item.quantity; item.product.save(update_fields=["sold_count","updated_at"])
        VendorPayout.objects.get_or_create(vendor_order=vendor_order,defaults={"vendor":vendor_order.vendor,"order":vendor_order.order,"amount":vendor_order.vendor_net,"currency":vendor_order.currency,"status":"pending","reference":f"PAYOUT-{vendor_order.id}"}); SecureOrderViewSet._accrue_vendor_sale(vendor_order)
    @staticmethod
    def _resolve_coupon(code,user,subtotal,currency):
        if not code:return None,Decimal("0.00")
        coupon=Coupon.objects.select_for_update().filter(code__iexact=code.strip()).first()
        if not coupon or not coupon.is_active:raise ValidationError({"coupon_code":"الكوبون غير صالح أو غير نشط"})
        now=timezone.now()
        if coupon.starts_at and now<coupon.starts_at:raise ValidationError({"coupon_code":"الكوبون لم يبدأ بعد"})
        if coupon.ends_at and now>coupon.ends_at:raise ValidationError({"coupon_code":"انتهت صلاحية الكوبون"})
        if coupon.usage_limit is not None and coupon.used_count>=coupon.usage_limit:raise ValidationError({"coupon_code":"استُنفدت مرات استخدام الكوبون"})
        if coupon.assigned_to.exists() and not coupon.assigned_to.filter(pk=user.pk).exists():raise ValidationError({"coupon_code":"هذا الكوبون غير متاح لهذا الحساب"})
        if subtotal<coupon.minimum_order:raise ValidationError({"coupon_code":f"الحد الأدنى للطلب هو {coupon.minimum_order}"})
        if coupon.discount_percent and coupon.discount_amount:raise ValidationError({"coupon_code":"إعداد الكوبون غير صالح: اختر نسبة أو مبلغًا ثابتًا فقط"})
        discount=(subtotal*coupon.discount_percent/Decimal("100")).quantize(Decimal("0.01")) if coupon.discount_percent else coupon.discount_amount
        return coupon,min(discount,subtotal)
    @transaction.atomic
    def create(self,request,*args,**kwargs):
        if request.user.role!="customer":raise PermissionDenied("إنشاء الطلبات متاح للعملاء فقط")
        rows=request.data.get("items")
        if not isinstance(rows,list) or not rows:raise ValidationError({"items":"السلة فارغة"})
        address=request.data.get("shipping_address") or {}; city_id=address.get("city_id"); city=City.objects.filter(id=city_id,is_active=True).first() if city_id else None
        if city_id and not city:raise ValidationError({"shipping_address":{"city_id":"المدينة غير صالحة"}})
        currency=str(request.data.get("currency","YER")).upper()
        if currency not in SUPPORTED_CURRENCIES:raise ValidationError({"currency":"العملة غير مدعومة"})
        payment_method=str(request.data.get("payment_method","cash_on_delivery")); requires_payment=payment_method!="cash_on_delivery"
        groups=defaultdict(lambda:{"vendor":None,"items":[],"subtotal":Decimal("0.00")}); subtotal=Decimal("0.00")
        for row in rows:
            if not isinstance(row,dict):raise ValidationError({"items":"صيغة عنصر السلة غير صالحة"})
            try: product_id=int(row["product_id"]); quantity=int(row.get("quantity",1))
            except (KeyError,TypeError,ValueError):raise ValidationError({"items":"product_id وquantity مطلوبان بشكل صحيح"})
            if quantity<1:raise ValidationError({"items":"الكمية يجب أن تكون 1 أو أكثر"})
            try:product=Product.objects.select_for_update().select_related("vendor").get(pk=product_id,is_published=True,vendor__status="active")
            except Product.DoesNotExist:raise ValidationError({"items":f"المنتج {product_id} غير موجود أو غير متاح"})
            variant=None
            if row.get("variant_id") not in (None,""):
                try:variant=ProductVariant.objects.select_for_update().get(id=int(row["variant_id"]),product=product,is_active=True)
                except (ProductVariant.DoesNotExist,TypeError,ValueError):raise ValidationError({"items":f"الخيار المحدد للمنتج {product.name} غير صالح"})
            available=variant.available_stock if variant else product.available_stock
            if available<quantity:raise ValidationError({"items":f"الكمية غير متاحة للمنتج {product.name}"})
            pricing=PricingEngine.calculate(product,city,quantity); unit_price=variant.price_override if variant and variant.price_override is not None else pricing["unit_final_price"]; line_total=unit_price*quantity
            subtotal+=line_total; groups[product.vendor_id]["vendor"]=product.vendor; groups[product.vendor_id]["items"].append((product,variant,quantity,row,unit_price,line_total)); groups[product.vendor_id]["subtotal"]+=line_total
        coupon,coupon_discount=self._resolve_coupon(str(request.data.get("coupon_code","")).strip(),request.user,subtotal,currency); shipping_fee=city.shipping_fee if city else Decimal("0.00"); total=max(Decimal("0.00"),subtotal-coupon_discount+shipping_fee)
        order=Order.objects.create(customer=request.user,order_number=f"ORD-{timezone.now():%Y%m%d}-{uuid.uuid4().hex[:6].upper()}",subtotal=subtotal,shipping_fee=shipping_fee,discount=coupon_discount,total=total,currency=currency,shipping_address=address,payment_method=payment_method,payment_status="pending",metadata={"pricing_source":"server","api_version":"v1","coupon_code":coupon.code if coupon else None})
        if coupon:
            coupon.used_count+=1; coupon.save(update_fields=["used_count","updated_at"]); CouponRedemption.objects.create(coupon=coupon,order=order,user=request.user,code_snapshot=coupon.code,discount_amount=coupon_discount,currency=currency)
        shipping_by_vendor=self._distribute_amount(groups,shipping_fee); discount_by_vendor=self._distribute_amount(groups,coupon_discount)
        for vendor_id,group in groups.items():
            vendor=group["vendor"]; vendor_subtotal=group["subtotal"]; vendor_discount=discount_by_vendor[vendor_id]; vendor_shipping=shipping_by_vendor[vendor_id]; vendor_total=max(Decimal("0.00"),vendor_subtotal-vendor_discount+vendor_shipping); commission=(vendor_subtotal*vendor.commission_percent/Decimal("100")).quantize(Decimal("0.01"))
            vendor_order=VendorOrder.objects.create(order=order,vendor=vendor,order_number=f"{order.order_number}-{vendor_id}",subtotal=vendor_subtotal,shipping_fee=vendor_shipping,discount=vendor_discount,total=vendor_total,commission=commission,vendor_net=vendor_subtotal-commission+vendor_shipping,currency=currency); Shipment.objects.create(vendor_order=vendor_order); OrderChat.objects.create(order=order,vendor_order=vendor_order,vendor=vendor,customer=request.user,subject=f"محادثة الطلب {order.order_number}")
            for product,variant,quantity,row,unit_price,line_total in group["items"]:
                item_commission=(line_total*vendor.commission_percent/Decimal("100")).quantize(Decimal("0.01")); order_item=OrderItem.objects.create(order=order,vendor=vendor,product=product,name_snapshot=product.name,sku_snapshot=variant.sku if variant else product.sku,quantity=quantity,unit_price=unit_price,color=variant.color if variant else str(row.get("color","")),size=variant.size if variant else str(row.get("size","")),vendor_total=line_total,commission=item_commission,vendor_net=line_total-item_commission); VendorOrderItem.objects.create(vendor_order=vendor_order,order_item=order_item)
                reservation_status=InventoryReservation.Status.ACTIVE if requires_payment else InventoryReservation.Status.COMMITTED
                if requires_payment:
                    if variant:variant.reserved_stock+=quantity;variant.save(update_fields=["reserved_stock","updated_at"])
                    else:product.reserved_stock+=quantity;product.save(update_fields=["reserved_stock","updated_at"])
                else:
                    if variant:variant.stock-=quantity;variant.save(update_fields=["stock","updated_at"])
                    else:product.stock-=quantity;product.save(update_fields=["stock","updated_at"])
                InventoryReservation.objects.create(order=order,order_item=order_item,variant=variant,product=None if variant else product,quantity=quantity,status=reservation_status,expires_at=timezone.now()+timedelta(minutes=30) if requires_payment else timezone.now())
        Payment.objects.create(order=order,provider="manual" if payment_method=="cash_on_delivery" else payment_method,method=payment_method,amount=total,currency=currency,status=Payment.Status.PENDING,metadata={"source":"checkout"})
        return Response(OrderSerializer(order,context={"request":request}).data,status=status.HTTP_201_CREATED)
    @action(detail=True,methods=["post"])
    @transaction.atomic
    def update_status(self,request,pk=None):
        order=self.get_object();user=request.user;new_status=str(request.data.get("status",""))
        if user.role=="vendor":
            vendor_order=order.vendor_orders.filter(vendor__owner=user).select_for_update().first()
            if not vendor_order:raise PermissionDenied("لا تملك هذا الطلب")
            if new_status in {"shipped","delivered"} and order.payment_method!="cash_on_delivery" and getattr(getattr(order,"payment",None),"status",None)!=Payment.Status.PAID:raise ValidationError({"status":"لا يمكن شحن الطلب قبل تأكيد الدفع"})
            if new_status not in {"confirmed","processing","shipped","delivered","cancelled"}:raise ValidationError({"status":"حالة التاجر غير صالحة"})
            old_status=vendor_order.status;vendor_order.status=new_status;vendor_order.save(update_fields=["status","updated_at"])
            if new_status=="delivered" and old_status!="delivered":
                self._commit_vendor_order_inventory(vendor_order);shipment=getattr(vendor_order,"shipment",None)
                if shipment:shipment.status=Shipment.Status.DELIVERED;shipment.delivered_at=timezone.now();shipment.save(update_fields=["status","delivered_at","updated_at"])
                if order.payment_method=="cash_on_delivery":
                    payment=order.payment;payment.status=Payment.Status.PAID;payment.paid_at=timezone.now();payment.save(update_fields=["status","paid_at","updated_at"]);order.payment_status="paid";order.save(update_fields=["payment_status","updated_at"])
            self._sync_parent_status(order);return Response({"vendor_order_id":vendor_order.id,"status":vendor_order.status})
        if not(user.is_staff or user.role=="admin"):raise PermissionDenied("لا تملك صلاحية تغيير حالة الطلب")
        if new_status not in {choice.value for choice in Order.Status}:raise ValidationError({"status":"حالة الطلب غير صالحة"})
        old_status=order.status;order.status=new_status;order.save(update_fields=["status","updated_at"]);OrderStatusHistory.objects.create(order=order,old_status=old_status,new_status=new_status,changed_by=user)
        if new_status=="cancelled":
            for reservation in order.inventory_reservations.select_for_update().filter(status__in=[InventoryReservation.Status.ACTIVE,InventoryReservation.Status.COMMITTED]):
                if reservation.variant_id:
                    variant=reservation.variant
                    if reservation.status==InventoryReservation.Status.ACTIVE:variant.reserved_stock=max(0,variant.reserved_stock-reservation.quantity)
                    else:variant.stock+=reservation.quantity
                    variant.save(update_fields=["reserved_stock","stock","updated_at"])
                elif reservation.product_id:
                    product=reservation.product
                    if reservation.status==InventoryReservation.Status.ACTIVE:product.reserved_stock=max(0,product.reserved_stock-reservation.quantity)
                    else:product.stock+=reservation.quantity
                    product.save(update_fields=["reserved_stock","stock","updated_at"])
                reservation.status=InventoryReservation.Status.RELEASED;reservation.save(update_fields=["status","updated_at"])
        return Response(OrderSerializer(order,context={"request":request}).data)
