from collections import defaultdict
from datetime import timedelta
from decimal import Decimal
import uuid

from django.db import transaction
from django.utils import timezone
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response

from .marketplace_models import InventoryReservation, Payment, VendorOrderItem
from .models import Coupon, Notification, Order, Product, ProductVariant, VendorLedgerEntry, VendorPayout, Wallet, WalletTransaction
from .models_extended import City
from .models_extra import VendorCityShipping
from .secure_order_v2 import SecureOrderV2ViewSet
from .serializers import OrderSerializer


class LaunchOrderViewSet(SecureOrderV2ViewSet):
    """Final marketplace order flow with wallet escrow, disputes and vendor settlement."""

    def _is_escrow(self, order):
        return bool((order.metadata or {}).get("escrow"))

    @staticmethod
    def _escrow(order):
        return dict((order.metadata or {}).get("escrow") or {})

    @staticmethod
    def _notify(user_id, title, body, product_id=None):
        if user_id:
            Notification.objects.create(recipient_id=user_id, title=title, body=body, product_id=product_id)

    @staticmethod
    def _wallet_credit(wallet, amount, transaction_type, reference, note, metadata=None):
        amount = Decimal(amount)
        if amount <= 0:
            return
        wallet.balance += amount
        wallet.save(update_fields=["balance", "updated_at"])
        WalletTransaction.objects.create(wallet=wallet, transaction_type=transaction_type, amount=amount, balance_after=wallet.balance, reference=reference, note=note, metadata=metadata or {})

    def _reprice_vendor_shipping(self, order):
        address = order.shipping_address or {}
        city_id = address.get("city_id")
        city = City.objects.filter(id=city_id, is_active=True).first() if city_id else None
        if city_id and not city:
            raise ValidationError({"shipping_address": {"city_id": "المحافظة غير صالحة"}})
        vendor_orders = list(order.vendor_orders.select_for_update().all())
        discount_total = Decimal(order.discount)
        discount_split = self._distribute_amount({item.id: {"subtotal": Decimal(item.subtotal)} for item in vendor_orders}, discount_total)
        total_shipping = Decimal("0.00")
        for vendor_order in vendor_orders:
            fee = Decimal("0.00")
            if city:
                fee = VendorCityShipping.objects.filter(vendor_id=vendor_order.vendor_id, city_id=city.id, is_active=True).values_list("fee", flat=True).first() or Decimal("0.00")
            vendor_order.shipping_fee = fee
            vendor_order.discount = discount_split.get(vendor_order.id, Decimal("0.00"))
            vendor_order.commission = sum((Decimal(link.order_item.commission) for link in vendor_order.items.select_related("order_item").all()), Decimal("0.00"))
            vendor_order.total = max(Decimal("0.00"), vendor_order.subtotal - vendor_order.discount + fee)
            vendor_order.vendor_net = max(Decimal("0.00"), vendor_order.subtotal - vendor_order.discount - vendor_order.commission + fee)
            vendor_order.save(update_fields=["shipping_fee", "discount", "commission", "total", "vendor_net", "updated_at"])
            total_shipping += fee
        order.shipping_fee = total_shipping
        order.total = max(Decimal("0.00"), order.subtotal - order.discount + total_shipping)
        order.save(update_fields=["shipping_fee", "total", "updated_at"])
        return order

    def _refresh_vendor_finance(self, order):
        for vendor_order in order.vendor_orders.select_for_update().all():
            vendor_order.commission = sum((Decimal(link.order_item.commission) for link in vendor_order.items.select_related("order_item").all()), Decimal("0.00"))
            vendor_order.total = max(Decimal("0.00"), vendor_order.subtotal - vendor_order.discount + vendor_order.shipping_fee)
            vendor_order.vendor_net = max(Decimal("0.00"), vendor_order.subtotal - vendor_order.discount - vendor_order.commission + vendor_order.shipping_fee)
            vendor_order.save(update_fields=["commission", "total", "vendor_net", "updated_at"])

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        if request.user.role != "customer":
            raise PermissionDenied("إنشاء الطلبات متاح للعملاء فقط")
        mutable = request.data.copy()
        mutable["payment_method"] = "wallet"
        request._full_data = mutable
        response = super().create(request, *args, **kwargs)
        order = Order.objects.select_for_update().get(pk=response.data["id"])
        self._reprice_vendor_shipping(order)
        self._refresh_vendor_finance(order)
        wallet = Wallet.objects.select_for_update().filter(user=request.user).first()
        if not wallet:
            raise ValidationError({"wallet": "لا توجد محفظة مرتبطة بالحساب."})
        if wallet.is_locked or wallet.currency != order.currency:
            raise ValidationError({"wallet": "المحفظة مقفلة أو عملتها لا تطابق عملة الطلب."})
        if wallet.balance < order.total:
            raise ValidationError({"wallet": "الرصيد غير كافٍ لإتمام الطلب."})
        wallet.balance -= order.total
        wallet.save(update_fields=["balance", "updated_at"])
        hold_ref = f"ORDER-HOLD-{order.id}-{uuid.uuid4().hex[:8].upper()}"
        WalletTransaction.objects.create(wallet=wallet, transaction_type=WalletTransaction.Types.PAYMENT, amount=-order.total, balance_after=wallet.balance, reference=hold_ref, note=f"حجز قيمة الطلب {order.order_number}", metadata={"order_id": order.id, "escrow": True})
        escrow = {"state": "held", "held_amount": str(order.total), "released_amount": "0.00", "refunded_amount": "0.00", "customer_confirmed": False, "disputes": {}}
        for vendor_order in order.vendor_orders.select_for_update().all():
            payout, created = VendorPayout.objects.get_or_create(vendor_order=vendor_order, defaults={"vendor": vendor_order.vendor, "order": order, "amount": vendor_order.vendor_net, "currency": order.currency, "status": "pending", "reference": f"PAYOUT-{vendor_order.id}"})
            if not created and payout.status == "pending":
                payout.amount = vendor_order.vendor_net
                payout.currency = order.currency
                payout.save(update_fields=["amount", "currency", "updated_at"])
            self._notify(vendor_order.vendor.owner_id, "طلب جديد", f"وصل طلب جديد {order.order_number}. المبلغ محجوز حتى استلام العميل واعتماد العملية.")
        payment = order.payment
        payment.provider = "wallet"
        payment.method = "wallet"
        payment.amount = order.total
        payment.status = Payment.Status.AUTHORIZED
        payment.paid_at = timezone.now()
        payment.metadata = {**(payment.metadata or {}), "escrow": True, "hold_reference": hold_ref}
        payment.save(update_fields=["provider", "method", "amount", "status", "paid_at", "metadata", "updated_at"])
        order.payment_method = "wallet"
        order.payment_status = "authorized"
        order.metadata = {**(order.metadata or {}), "escrow": escrow}
        order.save(update_fields=["payment_method", "payment_status", "metadata", "updated_at"])
        self._notify(request.user.id, "تم إنشاء طلبك", f"تم حجز {order.total} {order.currency} في رصيدك لحماية عملية الشراء.")
        return Response(OrderSerializer(order, context={"request": request}).data, status=response.status_code)

    @action(detail=True, methods=["post"])
    @transaction.atomic
    def update_pending(self, request, pk=None):
        order = self.get_queryset().select_for_update().get(pk=pk)
        if order.customer_id != request.user.id:
            raise PermissionDenied("لا تملك هذا الطلب")
        if order.status != Order.Status.PENDING or not self._is_escrow(order):
            raise ValidationError({"order": "يمكن تعديل الطلب قبل تأكيد التاجر فقط."})
        rows = request.data.get("items")
        if not isinstance(rows, list) or not rows:
            raise ValidationError({"items": "قائمة المنتجات مطلوبة."})
        quantities = {}
        for row in rows:
            if not isinstance(row, dict) or not str(row.get("order_item_id", "")).isdigit():
                raise ValidationError({"items": "رقم عنصر الطلب غير صالح."})
            qty = int(row.get("quantity", 0))
            if qty < 1:
                raise ValidationError({"items": "الكمية يجب أن تكون 1 أو أكثر."})
            quantities[int(row["order_item_id"])] = qty
        current_items = list(order.items.select_for_update().select_related("product", "vendor"))
        if set(quantities) != {item.id for item in current_items}:
            raise ValidationError({"items": "يمكن تعديل كميات عناصر الطلب الحالية فقط."})
        active_reservations = list(order.inventory_reservations.select_for_update().filter(status=InventoryReservation.Status.ACTIVE))
        reservation_by_item = {reservation.order_item_id: reservation for reservation in active_reservations}
        for reservation in active_reservations:
            if reservation.variant_id:
                variant = ProductVariant.objects.select_for_update().get(pk=reservation.variant_id)
                variant.reserved_stock = max(0, variant.reserved_stock - reservation.quantity)
                variant.save(update_fields=["reserved_stock", "updated_at"])
            elif reservation.product_id:
                product = Product.objects.select_for_update().get(pk=reservation.product_id)
                product.reserved_stock = max(0, product.reserved_stock - reservation.quantity)
                product.save(update_fields=["reserved_stock", "updated_at"])
            reservation.status = InventoryReservation.Status.RELEASED
            reservation.save(update_fields=["status", "updated_at"])
        subtotal = Decimal("0.00")
        for item in current_items:
            quantity = quantities[item.id]
            product = Product.objects.select_for_update().select_related("vendor").get(pk=item.product_id, is_published=True, vendor__status="active")
            old_reservation = reservation_by_item.get(item.id)
            variant = ProductVariant.objects.select_for_update().get(pk=old_reservation.variant_id, product=product, is_active=True) if old_reservation and old_reservation.variant_id else None
            available = variant.available_stock if variant else product.available_stock
            if available < quantity:
                raise ValidationError({"items": f"الكمية غير متاحة للمنتج {product.name}. المتاح: {available}"})
            line_total = Decimal(item.unit_price) * quantity
            item.quantity = quantity
            item.vendor_total = line_total
            item.commission = (line_total * Decimal(item.vendor.commission_percent) / Decimal("100")).quantize(Decimal("0.01"))
            item.vendor_net = max(Decimal("0.00"), line_total - item.commission)
            item.save(update_fields=["quantity", "vendor_total", "commission", "vendor_net", "updated_at"])
            subtotal += line_total
            if variant:
                variant.reserved_stock += quantity
                variant.save(update_fields=["reserved_stock", "updated_at"])
            else:
                product.reserved_stock += quantity
                product.save(update_fields=["reserved_stock", "updated_at"])
            InventoryReservation.objects.create(order=order, order_item=item, variant=variant, product=None if variant else product, quantity=quantity, status=InventoryReservation.Status.ACTIVE, expires_at=timezone.now() + timedelta(minutes=30))
        order.subtotal = subtotal
        coupon_code = str((order.metadata or {}).get("coupon_code") or "").strip()
        if coupon_code:
            coupon = Coupon.objects.filter(code__iexact=coupon_code, is_active=True).first()
            if coupon and coupon.minimum_order <= subtotal:
                order.discount = min((subtotal * coupon.discount_percent / Decimal("100")).quantize(Decimal("0.01")) if coupon.discount_percent else Decimal(coupon.discount_amount), subtotal)
        else:
            order.discount = min(Decimal(order.discount), subtotal)
        if isinstance(request.data.get("shipping_address"), dict):
            order.shipping_address = request.data["shipping_address"]
        order.save(update_fields=["subtotal", "discount", "shipping_address", "updated_at"])
        self._reprice_vendor_shipping(order)
        self._refresh_vendor_finance(order)
        old_total = Decimal(self._escrow(order).get("held_amount", "0.00"))
        new_total = Decimal(order.total)
        wallet = Wallet.objects.select_for_update().get(user=request.user)
        if wallet.is_locked or wallet.currency != order.currency:
            raise ValidationError({"wallet": "المحفظة مقفلة أو عملتها لا تطابق الطلب."})
        delta = new_total - old_total
        if delta > 0:
            if wallet.balance < delta:
                raise ValidationError({"wallet": "الرصيد غير كافٍ للزيادة المطلوبة."})
            wallet.balance -= delta
            wallet.save(update_fields=["balance", "updated_at"])
            WalletTransaction.objects.create(wallet=wallet, transaction_type=WalletTransaction.Types.PAYMENT, amount=-delta, balance_after=wallet.balance, reference=f"ORDER-HOLD-ADJUST-{order.id}-{uuid.uuid4().hex[:7].upper()}", note=f"زيادة حجز الطلب {order.order_number}")
        elif delta < 0:
            self._wallet_credit(wallet, -delta, WalletTransaction.Types.REFUND, f"ORDER-HOLD-REDUCE-{order.id}-{uuid.uuid4().hex[:7].upper()}", f"إعادة فرق تعديل الطلب {order.order_number}")
        payment = order.payment
        payment.amount = order.total
        payment.save(update_fields=["amount", "updated_at"])
        for vendor_order in order.vendor_orders.select_for_update().all():
            payout = VendorPayout.objects.filter(vendor_order=vendor_order, status="pending").first()
            if payout:
                payout.amount = vendor_order.vendor_net
                payout.save(update_fields=["amount", "updated_at"])
        escrow = self._escrow(order)
        escrow["held_amount"] = str(new_total)
        order.metadata = {**(order.metadata or {}), "escrow": escrow}
        order.save(update_fields=["metadata", "updated_at"])
        return Response(OrderSerializer(order, context={"request": request}).data)

    @action(detail=True, methods=["get"])
    def order_view(self, request, pk=None):
        order = self.get_queryset().select_related("customer").prefetch_related("items__product", "items__vendor", "vendor_orders__vendor", "status_history").get(pk=pk)
        payload = OrderSerializer(order, context={"request": request}).data
        payload["items"] = [{**item, "product_url": f"/product/{item['product']}", "vendor_url": f"/store/{order.items.get(pk=item['id']).vendor.slug}", "image_url": request.build_absolute_uri(order.items.get(pk=item['id']).product.main_image.url) if order.items.get(pk=item['id']).product.main_image else None} for item in payload["items"]]
        payload["timeline"] = [{"status": h.new_status, "old_status": h.old_status, "created_at": h.created_at.isoformat(), "note": h.note} for h in order.status_history.order_by("created_at")]
        payload["escrow"] = self._escrow(order) if self._is_escrow(order) else None
        return Response(payload)

    @action(detail=True, methods=["post"])
    @transaction.atomic
    def confirm_received(self, request, pk=None):
        order = self.get_queryset().select_for_update().get(pk=pk)
        if order.customer_id != request.user.id:
            raise PermissionDenied("لا تملك هذا الطلب")
        escrow = self._escrow(order)
        if not escrow or escrow.get("customer_confirmed"):
            raise ValidationError({"order": "تم تسجيل تأكيد الاستلام مسبقًا أو لا يوجد مبلغ معلق."})
        if order.status != Order.Status.DELIVERED:
            raise ValidationError({"order": "لا يمكن تأكيد الاستلام قبل وصول الطلب بالكامل."})
        if any(value.get("status") == "pending" for value in (escrow.get("disputes") or {}).values()):
            raise ValidationError({"order": "يوجد اعتراض مفتوح. يجب حله قبل التأكيد النهائي."})
        escrow["customer_confirmed"] = True
        escrow["customer_confirmed_at"] = timezone.now().isoformat()
        escrow["state"] = "awaiting_release"
        order.metadata = {**(order.metadata or {}), "escrow": escrow}
        order.save(update_fields=["metadata", "updated_at"])
        for vendor_order in order.vendor_orders.all():
            self._notify(vendor_order.vendor.owner_id, "العميل أكد استلام الطلب", f"أكد العميل استلام الطلب {order.order_number}. أصبحت مستحقاتك جاهزة لاعتماد الإدارة.")
        self._notify(request.user.id, "تم تسجيل الاستلام", "تم تسجيل تأكيد استلامك. هذه الخطوة نهائية ولا يمكن التراجع عنها.")
        return Response({"success": True, "message": "تم تسجيل الاستلام وبانتظار اعتماد الإدارة."})

    @action(detail=True, methods=["post"])
    @transaction.atomic
    def reject_item(self, request, pk=None):
        order = self.get_queryset().select_for_update().get(pk=pk)
        item_id = str(request.data.get("order_item_id", "")); reason = str(request.data.get("reason", "")).strip()
        if not item_id.isdigit() or not reason:
            raise ValidationError({"order_item_id": "رقم القطعة وسبب الاعتراض مطلوبان."})
        item = order.items.select_related("vendor").filter(pk=int(item_id)).first()
        if not item: raise ValidationError({"order_item_id": "قطعة الطلب غير موجودة."})
        if request.user.role == "customer":
            if order.customer_id != request.user.id: raise PermissionDenied("لا تملك هذا الطلب")
            if order.status != Order.Status.DELIVERED: raise ValidationError({"order": "يمكن فتح الاعتراض بعد تسليم الطلب."})
        elif request.user.role == "vendor":
            if item.vendor.owner_id != request.user.id: raise PermissionDenied("لا تملك هذه القطعة")
        else:
            raise PermissionDenied("هذه العملية متاحة للعميل أو التاجر فقط")
        escrow = self._escrow(order)
        if not escrow: raise ValidationError({"order": "لا يوجد مبلغ معلق لهذا الطلب."})
        disputes = dict(escrow.get("disputes") or {}); key = str(item.id)
        if disputes.get(key, {}).get("status") == "pending": raise ValidationError({"order_item_id": "يوجد اعتراض مفتوح لهذه القطعة بالفعل."})
        disputes[key] = {"status": "pending", "reason": reason, "opened_by": request.user.id, "opened_at": timezone.now().isoformat()}
        escrow["disputes"] = disputes; escrow["state"] = "partial_dispute"
        order.metadata = {**(order.metadata or {}), "escrow": escrow}; order.save(update_fields=["metadata", "updated_at"])
        self._notify(order.customer_id, "تم فتح اعتراض على قطعة", f"تم فتح اعتراض على {item.name_snapshot} في الطلب {order.order_number}.")
        self._notify(item.vendor.owner_id, "يوجد اعتراض على قطعة", f"يوجد اعتراض على {item.name_snapshot}: {reason}")
        return Response({"success": True, "status": "pending_dispute", "refund": "0.00"})

    @action(detail=True, methods=["post"])
    @transaction.atomic
    def reject_order(self, request, pk=None):
        order = self.get_queryset().select_for_update().get(pk=pk)
        if order.customer_id != request.user.id: raise PermissionDenied("لا تملك هذا الطلب")
        if order.status != Order.Status.DELIVERED or not self._is_escrow(order): raise ValidationError({"order": "يمكن رفض الطلب بعد تسليمه فقط."})
        reason = str(request.data.get("reason", "")).strip()
        if not reason: raise ValidationError({"reason": "سبب رفض الطلب مطلوب."})
        escrow = self._escrow(order); disputes = dict(escrow.get("disputes") or {})
        for item in order.items.all(): disputes[str(item.id)] = {"status":"pending","reason":reason,"opened_by":request.user.id,"opened_at":timezone.now().isoformat(),"whole_order":True}
        escrow["disputes"] = disputes; escrow["state"] = "full_dispute"
        order.metadata = {**(order.metadata or {}), "escrow": escrow}; order.save(update_fields=["metadata","updated_at"])
        for vendor_order in order.vendor_orders.all(): self._notify(vendor_order.vendor.owner_id,"اعتراض على كامل الطلب",f"فتح العميل اعتراضًا على كامل الطلب {order.order_number}: {reason}")
        return Response({"success":True,"status":"full_dispute"})

    @action(detail=True, methods=["post"])
    @transaction.atomic
    def admin_release(self, request, pk=None):
        if not (request.user.is_staff or request.user.role == "admin"): raise PermissionDenied("للمدير فقط")
        order = self.get_queryset().select_for_update().get(pk=pk); escrow = self._escrow(order)
        if not escrow or not escrow.get("customer_confirmed"): raise ValidationError({"order":"يجب أن يؤكد العميل استلام الطلب أولاً."})
        disputes = escrow.get("disputes") or {}; unresolved = {int(k) for k,v in disputes.items() if v.get("status")=="pending" and k.isdigit()}; released = Decimal(escrow.get("released_amount","0.00"))
        for payout in VendorPayout.objects.select_for_update().filter(order=order,status="pending"):
            withheld=Decimal("0.00")
            if payout.vendor_order_id:
                for link in VendorOrderItem.objects.filter(vendor_order_id=payout.vendor_order_id).select_related("order_item"):
                    if link.order_item_id in unresolved: withheld += Decimal(link.order_item.vendor_net)
            pay=max(Decimal("0.00"),Decimal(payout.amount)-withheld)
            if pay>0:
                vendor_wallet,_=Wallet.objects.select_for_update().get_or_create(user=payout.vendor.owner,defaults={"currency":payout.currency})
                if vendor_wallet.currency!=payout.currency: raise ValidationError({"wallet":"عملة محفظة التاجر لا تطابق الطلب."})
                self._wallet_credit(vendor_wallet,pay,WalletTransaction.Types.REWARD,f"ESCROW-PAYOUT-{payout.id}",f"إطلاق مستحقات الطلب {order.order_number}",{"order_id":order.id,"vendor_order_id":payout.vendor_order_id})
                previous=VendorLedgerEntry.objects.filter(vendor=payout.vendor,currency=payout.currency).order_by("-id").first(); balance_after=(previous.balance_after if previous else Decimal("0.00"))+pay
                VendorLedgerEntry.objects.get_or_create(reference=f"ESCROW-SALE-{payout.id}",defaults={"vendor":payout.vendor,"vendor_order":payout.vendor_order,"entry_type":VendorLedgerEntry.Types.SALE,"amount":pay,"balance_after":balance_after,"currency":payout.currency,"metadata":{"escrow_release":True,"order_id":order.id}})
            payout.status="approved" if withheld>0 else "paid"; payout.save(update_fields=["status","updated_at"]); released += pay
        escrow["released_amount"]=str(released); escrow["state"]="partial_dispute" if unresolved else "released"; order.metadata={**(order.metadata or {}),"escrow":escrow}; order.payment_status="partially_released" if unresolved else "paid"; order.save(update_fields=["metadata","payment_status","updated_at"])
        self._notify(order.customer_id,"تمت مراجعة طلبك",f"تم إطلاق المستحقات غير المتنازع عليها للطلب {order.order_number}.")
        return Response({"success":True,"released_amount":str(released),"held_amount":escrow.get("held_amount","0.00"),"state":escrow["state"]})

    @action(detail=True, methods=["post"])
    @transaction.atomic
    def resolve_item_dispute(self, request, pk=None):
        if not (request.user.is_staff or request.user.role == "admin"): raise PermissionDenied("للمدير فقط")
        order=self.get_queryset().select_for_update().get(pk=pk); item_id=str(request.data.get("order_item_id","")); decision=str(request.data.get("decision","")).lower()
        if not item_id.isdigit() or decision not in {"refund","release"}: raise ValidationError({"decision":"استخدم refund أو release مع رقم القطعة."})
        item=order.items.select_related("vendor").filter(pk=int(item_id)).first()
        if not item: raise ValidationError({"order_item_id":"قطعة الطلب غير موجودة."})
        escrow=self._escrow(order); disputes=dict(escrow.get("disputes") or {}); current=disputes.get(item_id)
        if not current or current.get("status")!="pending": raise ValidationError({"order_item_id":"لا يوجد اعتراض معلق لهذه القطعة."})
        if decision=="refund":
            wallet=Wallet.objects.select_for_update().get(user=order.customer); refund=Decimal(item.vendor_total)
            self._wallet_credit(wallet,refund,WalletTransaction.Types.REFUND,f"DISPUTE-REFUND-{item.id}",f"استرداد قيمة القطعة من الطلب {order.order_number}",{"order_item_id":item.id}); escrow["refunded_amount"]=str(Decimal(escrow.get("refunded_amount","0.00"))+refund)
        else:
            vendor_wallet,_=Wallet.objects.select_for_update().get_or_create(user=item.vendor.owner,defaults={"currency":order.currency})
            if vendor_wallet.currency!=order.currency: raise ValidationError({"wallet":"عملة محفظة التاجر لا تطابق الطلب."})
            self._wallet_credit(vendor_wallet,item.vendor_net,WalletTransaction.Types.REWARD,f"DISPUTE-RELEASE-{item.id}",f"إطلاق مستحق القطعة بعد حل الاعتراض {order.order_number}",{"order_item_id":item.id})
            payout=VendorPayout.objects.filter(order=order,vendor=item.vendor).first()
            if payout:
                pending_ids={int(k) for k,v in disputes.items() if v.get("status")=="pending" and k.isdigit() and int(k)!=item.id}
                vendor_pending=VendorOrderItem.objects.filter(vendor_order_id=payout.vendor_order_id,order_item_id__in=pending_ids).exists()
                if not vendor_pending: payout.status="paid"; payout.save(update_fields=["status","updated_at"])
        current["status"]="resolved_refund" if decision=="refund" else "resolved_release"; current["resolved_at"]=timezone.now().isoformat(); current["resolved_by"]=request.user.id; disputes[item_id]=current; escrow["disputes"]=disputes
        unresolved=any(v.get("status")=="pending" for v in disputes.values()); escrow["state"]="partial_dispute" if unresolved else "released"; order.metadata={**(order.metadata or {}),"escrow":escrow}; order.payment_status="partially_released" if unresolved else "paid"; order.save(update_fields=["metadata","payment_status","updated_at"])
        self._notify(order.customer_id,"تم حل الاعتراض",f"تمت معالجة اعتراضك على القطعة في الطلب {order.order_number}."); self._notify(item.vendor.owner_id,"تم حل اعتراض على القطعة",f"تمت معالجة الاعتراض على القطعة {item.name_snapshot}.")
        return Response({"success":True,"decision":decision,"status":current["status"]})

    @action(detail=True, methods=["post"])
    @transaction.atomic
    def update_status(self, request, pk=None):
        order=self.get_object(); user=request.user; new_status=str(request.data.get("status",""))
        if user.role=="vendor" and self._is_escrow(order):
            vendor_order=order.vendor_orders.filter(vendor__owner=user).select_for_update().first()
            if not vendor_order: raise PermissionDenied("لا تملك هذا الطلب")
            if new_status not in {"confirmed","processing","shipped","delivered","cancelled"}: raise ValidationError({"status":"حالة التاجر غير صالحة"})
            old=vendor_order.status; vendor_order.status=new_status; vendor_order.save(update_fields=["status","updated_at"])
            if new_status=="shipped" and getattr(vendor_order,"shipment",None):
                shipment=vendor_order.shipment; shipment.status="shipped"; shipment.shipped_at=shipment.shipped_at or timezone.now(); shipment.save(update_fields=["status","shipped_at","updated_at"])
            if new_status=="delivered" and old!="delivered":
                for link in vendor_order.items.select_related("order_item__product").all():
                    reservation=InventoryReservation.objects.select_for_update().filter(order_item=link.order_item,status=InventoryReservation.Status.ACTIVE).first()
                    if reservation:
                        if reservation.variant_id:
                            variant=ProductVariant.objects.select_for_update().get(pk=reservation.variant_id); variant.reserved_stock=max(0,variant.reserved_stock-reservation.quantity); variant.stock=max(0,variant.stock-reservation.quantity); variant.save(update_fields=["reserved_stock","stock","updated_at"])
                        elif reservation.product_id:
                            product=Product.objects.select_for_update().get(pk=reservation.product_id); product.reserved_stock=max(0,product.reserved_stock-reservation.quantity); product.stock=max(0,product.stock-reservation.quantity); product.save(update_fields=["reserved_stock","stock","updated_at"])
                        reservation.status=InventoryReservation.Status.COMMITTED; reservation.save(update_fields=["status","updated_at"])
                    link.order_item.product.sold_count+=link.order_item.quantity; link.order_item.product.save(update_fields=["sold_count","updated_at"])
                if getattr(vendor_order,"shipment",None):
                    shipment=vendor_order.shipment; shipment.status="delivered"; shipment.delivered_at=timezone.now(); shipment.save(update_fields=["status","delivered_at","updated_at"])
            self._sync_parent_status(order); self._notify(order.customer_id,"تحديث طلبك",f"تم تحديث طلب {order.order_number} إلى: {new_status}")
            return Response({"vendor_order_id":vendor_order.id,"status":vendor_order.status,"order_status":order.status})
        if not (user.is_staff or user.role=="admin"): raise PermissionDenied("لا تملك صلاحية تغيير حالة الطلب")
        if new_status not in {choice.value for choice in Order.Status}: raise ValidationError({"status":"حالة الطلب غير صالحة"})
        if new_status==Order.Status.CANCELLED and self._is_escrow(order):
            response=super().update_status(request,pk=order.pk); order.refresh_from_db(); escrow=self._escrow(order)
            remaining=max(Decimal("0.00"),Decimal(escrow.get("held_amount","0.00"))-Decimal(escrow.get("released_amount","0.00"))-Decimal(escrow.get("refunded_amount","0.00")))
            if remaining>0:
                wallet=Wallet.objects.select_for_update().get(user=order.customer); self._wallet_credit(wallet,remaining,WalletTransaction.Types.REFUND,f"ORDER-CANCEL-REFUND-{order.id}",f"استرداد قيمة الطلب الملغي {order.order_number}",{"order_id":order.id}); escrow["refunded_amount"]=str(Decimal(escrow.get("refunded_amount","0.00"))+remaining)
            escrow["state"]="refunded"; order.metadata={**(order.metadata or {}),"escrow":escrow}; order.payment_status="refunded"; payment=getattr(order,"payment",None)
            if payment: payment.status=Payment.Status.REFUNDED; payment.refunded_amount=payment.amount; payment.save(update_fields=["status","refunded_amount","updated_at"])
            order.save(update_fields=["metadata","payment_status","updated_at"]); self._notify(order.customer_id,"تم إلغاء الطلب واسترداد الرصيد",f"تم إلغاء الطلب {order.order_number} وإعادة المبلغ المحجوز إلى محفظتك."); return response
        response=super().update_status(request,pk=order.pk); order.refresh_from_db(); label={"confirmed":"تم تأكيد الطلب","processing":"جارٍ تجهيز الطلب","shipped":"تم شحن الطلب","delivered":"تم تسليم الطلب","cancelled":"تم إلغاء الطلب"}.get(new_status,new_status); self._notify(order.customer_id,"تحديث طلبك",f"{label}: {order.order_number}"); return response
