from collections import defaultdict
from decimal import Decimal
import uuid

from django.db import transaction
from django.utils import timezone
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response

from .marketplace_models import InventoryReservation, Payment, VendorOrder, VendorOrderItem
from .models import Notification, Order, OrderItem, OrderStatusHistory, VendorLedgerEntry, VendorPayout, Wallet, WalletTransaction
from .models_extended import City, Product, ProductVariant
from .models_extra import VendorCityShipping
from .secure_order_v2 import SecureOrderV2ViewSet
from .serializers import OrderSerializer


class LaunchOrderViewSet(SecureOrderV2ViewSet):
    """Production marketplace order flow: wallet escrow, delivery confirmation and disputes."""

    def _is_escrow(self, order):
        meta = order.metadata or {}
        return bool(meta.get("escrow"))

    @staticmethod
    def _escrow(order):
        return dict((order.metadata or {}).get("escrow") or {})

    @staticmethod
    def _notify(user_id, title, body, product_id=None):
        if not user_id:
            return
        Notification.objects.create(recipient_id=user_id, title=title, body=body, product_id=product_id)

    @staticmethod
    def _wallet(wallet, amount, transaction_type, reference, note, metadata=None):
        wallet.balance += amount
        wallet.save(update_fields=["balance", "updated_at"])
        WalletTransaction.objects.create(
            wallet=wallet,
            transaction_type=transaction_type,
            amount=amount,
            balance_after=wallet.balance,
            reference=reference,
            note=note,
            metadata=metadata or {},
        )

    def _reprice_vendor_shipping(self, order):
        address = order.shipping_address or {}
        city_id = address.get("city_id")
        total_shipping = Decimal("0.00")
        city = City.objects.filter(id=city_id, is_active=True).first() if city_id else None
        if city_id and not city:
            raise ValidationError({"shipping_address": {"city_id": "المدينة غير صالحة"}})
        vendor_orders = list(order.vendor_orders.select_for_update().all())
        for vendor_order in vendor_orders:
            fee = Decimal("0.00")
            if city:
                fee = VendorCityShipping.objects.filter(vendor=vendor_order.vendor_id, city_id=city.id, is_active=True).values_list("fee", flat=True).first() or Decimal("0.00")
            vendor_order.shipping_fee = fee
            vendor_order.total = max(Decimal("0.00"), vendor_order.subtotal - vendor_order.discount + fee)
            vendor_order.vendor_net = max(Decimal("0.00"), vendor_order.subtotal - vendor_order.commission + fee)
            vendor_order.save(update_fields=["shipping_fee", "total", "vendor_net", "updated_at"])
            total_shipping += fee
        order.shipping_fee = total_shipping
        order.total = max(Decimal("0.00"), order.subtotal - order.discount + total_shipping)
        order.save(update_fields=["shipping_fee", "total", "updated_at"])
        return order

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        if request.user.role != "customer":
            raise PermissionDenied("إنشاء الطلبات متاح للعملاء فقط")
        mutable = request.data.copy()
        mutable["payment_method"] = "wallet"
        request._full_data = mutable
        response = super().create(request, *args, **kwargs)
        order = Order.objects.select_for_update().get(pk=response.data["id"])
        order = self._reprice_vendor_shipping(order)
        wallet = Wallet.objects.select_for_update().filter(user=request.user).first()
        if not wallet:
            raise ValidationError({"wallet": "لا يوجد رصيد مرتبط بالحساب."})
        if wallet.is_locked or wallet.currency != order.currency:
            raise ValidationError({"wallet": "الرصيد مقفل أو عملته لا تطابق عملة الطلب."})
        if wallet.balance < order.total:
            raise ValidationError({"wallet": "الرصيد غير كافٍ لإتمام الطلب."})
        wallet.balance -= order.total
        wallet.save(update_fields=["balance", "updated_at"])
        hold_ref = f"ORDER-HOLD-{order.id}-{uuid.uuid4().hex[:8].upper()}"
        WalletTransaction.objects.create(
            wallet=wallet,
            transaction_type=WalletTransaction.Types.PAYMENT,
            amount=-order.total,
            balance_after=wallet.balance,
            reference=hold_ref,
            note=f"حجز قيمة الطلب {order.order_number}",
            metadata={"order_id": order.id, "escrow": True},
        )
        escrow = {
            "state": "held",
            "held_amount": str(order.total),
            "released_amount": "0.00",
            "refunded_amount": "0.00",
            "customer_confirmed": False,
            "disputes": {},
        }
        for vendor_order in order.vendor_orders.select_for_update().all():
            VendorPayout.objects.get_or_create(
                vendor_order=vendor_order,
                defaults={
                    "vendor": vendor_order.vendor,
                    "order": order,
                    "amount": vendor_order.vendor_net,
                    "currency": order.currency,
                    "status": "pending",
                    "reference": f"PAYOUT-{vendor_order.id}",
                },
            )
            self._notify(vendor_order.vendor.owner_id, "طلب جديد", f"وصل طلب جديد {order.order_number}. المبلغ محجوز حتى استلام العميل واعتماده.")
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
        items = request.data.get("items")
        if items is not None and not isinstance(items, list):
            raise ValidationError({"items": "صيغة الأصناف غير صحيحة."})
        quantities = {int(row["order_item_id"]): int(row["quantity"]) for row in (items or []) if isinstance(row, dict) and str(row.get("order_item_id", "")).isdigit()}
        current_items = list(order.items.select_for_update().select_related("product", "vendor"))
        if quantities and set(quantities) != {item.id for item in current_items}:
            raise ValidationError({"items": "لتفادي أخطاء مالية يجب تعديل كميات الأصناف الموجودة فقط."})
        for item in current_items:
            if item.id in quantities and quantities[item.id] < 1:
                raise ValidationError({"items": "الكمية يجب أن تكون 1 أو أكثر."})

        reservations = list(order.inventory_reservations.select_for_update().filter(status=InventoryReservation.Status.ACTIVE))
        for reservation in reservations:
            if reservation.variant_id:
                variant = reservation.variant
                variant.reserved_stock = max(0, variant.reserved_stock - reservation.quantity)
                variant.save(update_fields=["reserved_stock", "updated_at"])
            elif reservation.product_id:
                product = reservation.product
                product.reserved_stock = max(0, product.reserved_stock - reservation.quantity)
                product.save(update_fields=["reserved_stock", "updated_at"])
            reservation.status = InventoryReservation.Status.RELEASED
            reservation.save(update_fields=["status", "updated_at"])

        subtotal = Decimal("0.00")
        by_vendor = defaultdict(lambda: {"subtotal": Decimal("0.00"), "items": []})
        for item in current_items:
            quantity = quantities.get(item.id, item.quantity)
            product = Product.objects.select_for_update().get(pk=item.product_id, is_published=True, vendor__status="active")
            variant = None
            reservation_template = None
            old = next((r for r in reservations if r.order_item_id == item.id), None)
            if old and old.variant_id:
                variant = ProductVariant.objects.select_for_update().get(pk=old.variant_id, product=product, is_active=True)
            available = variant.available_stock if variant else product.available_stock
            if available < quantity:
                raise ValidationError({"items": f"الكمية غير متاحة للمنتج {product.name}"})
            line_total = item.unit_price * quantity
            subtotal += line_total
            item.quantity = quantity
            item.vendor_total = line_total
            item.vendor_net = max(Decimal("0.00"), line_total - item.commission)
            item.save(update_fields=["quantity", "vendor_total", "vendor_net", "updated_at"])
            by_vendor[item.vendor_id]["subtotal"] += line_total
            by_vendor[item.vendor_id]["items"].append((item, variant, quantity, product))
            reservation_template = variant
            if reservation_template:
                reservation_template.reserved_stock += quantity
                reservation_template.save(update_fields=["reserved_stock", "updated_at"])
            else:
                product.reserved_stock += quantity
                product.save(update_fields=["reserved_stock", "updated_at"])
            InventoryReservation.objects.create(
                order=order,
                order_item=item,
                variant=variant,
                product=None if variant else product,
                quantity=quantity,
                status=InventoryReservation.Status.ACTIVE,
                expires_at=timezone.now() + __import__("datetime").timedelta(minutes=30),
            )

        old_subtotal = Decimal(order.subtotal)
        order.subtotal = subtotal
        order.discount = min(Decimal(order.discount), subtotal)
        address = request.data.get("shipping_address")
        if isinstance(address, dict):
            order.shipping_address = address
        order.save(update_fields=["subtotal", "discount", "shipping_address", "updated_at"])
        self._reprice_vendor_shipping(order)

        old_total = Decimal((self._escrow(order)).get("held_amount", "0.00"))
        new_total = Decimal(order.total)
        wallet = Wallet.objects.select_for_update().get(user=request.user)
        delta = new_total - old_total
        if delta > 0:
            if wallet.balance < delta:
                raise ValidationError({"wallet": "الرصيد غير كافٍ للزيادة المطلوبة."})
            wallet.balance -= delta
            wallet.save(update_fields=["balance", "updated_at"])
            WalletTransaction.objects.create(wallet=wallet, transaction_type=WalletTransaction.Types.PAYMENT, amount=-delta, balance_after=wallet.balance, reference=f"ORDER-HOLD-ADJUST-{order.id}-{uuid.uuid4().hex[:6]}", note=f"زيادة حجز الطلب {order.order_number}")
        elif delta < 0:
            self._wallet(wallet, -delta, WalletTransaction.Types.REFUND, f"ORDER-HOLD-REDUCE-{order.id}-{uuid.uuid4().hex[:6]}", f"إعادة فرق تعديل الطلب {order.order_number}")
        escrow = self._escrow(order)
        escrow["held_amount"] = str(new_total)
        order.metadata = {**(order.metadata or {}), "escrow": escrow}
        order.save(update_fields=["metadata", "updated_at"])
        return Response(OrderSerializer(order, context={"request": request}).data)

    @action(detail=True, methods=["get"])
    def order_view(self, request, pk=None):
        order = self.get_queryset().select_related("customer").prefetch_related("items__product", "items__vendor", "vendor_orders__vendor").get(pk=pk)
        payload = OrderSerializer(order, context={"request": request}).data
        payload["timeline"] = [{"status": h.new_status, "old_status": h.old_status, "created_at": h.created_at.isoformat(), "note": h.note} for h in order.status_history.order_by("created_at")]
        payload["items"] = [
            {**item, "product_url": f"/product/{item['product']}", "vendor_url": f"/store/{getattr(order.items.get(pk=item['id']).vendor, 'slug', '')}"}
            for item in payload["items"]
        ]
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
        escrow["customer_confirmed"] = True
        escrow["customer_confirmed_at"] = timezone.now().isoformat()
        escrow["state"] = "awaiting_release"
        order.metadata = {**(order.metadata or {}), "escrow": escrow}
        order.save(update_fields=["metadata", "updated_at"])
        for vendor_order in order.vendor_orders.all():
            self._notify(vendor_order.vendor.owner_id, "العميل أكد استلام الطلب", f"أكد العميل استلام الطلب {order.order_number}. سيتم إطلاق مستحقاتك بعد اعتماد الإدارة.")
        self._notify(request.user.id, "تم تسجيل الاستلام", "تم تسجيل تأكيد استلامك. لا يمكن التراجع عن هذه الخطوة، وأصبحت عملية الإطلاق تحت اعتماد الإدارة.")
        return Response({"success": True, "message": "تم تسجيل الاستلام وبانتظار اعتماد الإدارة."})

    @action(detail=True, methods=["post"])
    @transaction.atomic
    def reject_item(self, request, pk=None):
        order = self.get_queryset().select_for_update().get(pk=pk)
        item_id = str(request.data.get("order_item_id", ""))
        reason = str(request.data.get("reason", "")).strip()
        if not item_id.isdigit() or not reason:
            raise ValidationError({"order_item_id": "رقم القطعة وسبب الرفض مطلوبان."})
        item = order.items.select_related("vendor").filter(pk=int(item_id)).first()
        if not item:
            raise ValidationError({"order_item_id": "قطعة الطلب غير موجودة."})
        user = request.user
        if user.role == "vendor" and item.vendor.owner_id != user.id:
            raise PermissionDenied("لا تملك هذه القطعة")
        if user.role not in {"vendor", "customer"}:
            raise PermissionDenied("هذه العملية متاحة للعميل أو التاجر فقط")
        escrow = self._escrow(order)
        disputes = dict(escrow.get("disputes") or {})
        key = str(item.id)
        if disputes.get(key, {}).get("status") == "pending":
            raise ValidationError({"order_item_id": "يوجد اعتراض مفتوح لهذه القطعة بالفعل."})
        disputes[key] = {"status": "pending", "reason": reason, "opened_by": user.id, "opened_at": timezone.now().isoformat()}
        escrow["disputes"] = disputes
        escrow["state"] = "partial_dispute"
        order.metadata = {**(order.metadata or {}), "escrow": escrow}
        order.save(update_fields=["metadata", "updated_at"])
        self._notify(order.customer_id, "اعتراض على قطعة من الطلب", f"يوجد اعتراض على القطعة {item.name_snapshot} في الطلب {order.order_number}: {reason}")
        self._notify(item.vendor.owner_id, "اعتراض على قطعة", f"يوجد اعتراض على القطعة {item.name_snapshot}: {reason}")
        return Response({"success": True, "status": "pending_dispute", "refund": "0.00"})

    @action(detail=True, methods=["post"])
    @transaction.atomic
    def admin_release(self, request, pk=None):
        if not (request.user.is_staff or request.user.role == "admin"):
            raise PermissionDenied("للمدير فقط")
        order = self.get_queryset().select_for_update().get(pk=pk)
        escrow = self._escrow(order)
        if not escrow or not escrow.get("customer_confirmed"):
            raise ValidationError({"order": "يجب أن يؤكد العميل استلام الطلب أولاً."})
        disputes = escrow.get("disputes") or {}
        released = Decimal(escrow.get("released_amount", "0.00"))
        for payout in VendorPayout.objects.select_for_update().filter(order=order, status="pending"):
            disputed_item_ids = {int(key) for key, value in disputes.items() if value.get("status") == "pending" and key.isdigit()}
            withheld = Decimal("0.00")
            if payout.vendor_order_id:
                for link in VendorOrderItem.objects.filter(vendor_order_id=payout.vendor_order_id).select_related("order_item"):
                    if link.order_item_id in disputed_item_ids:
                        withheld += Decimal(link.order_item.vendor_net)
            pay = max(Decimal("0.00"), Decimal(payout.amount) - withheld)
            if pay <= 0:
                payout.status = "approved"
                payout.save(update_fields=["status", "updated_at"])
                continue
            vendor_wallet, _ = Wallet.objects.select_for_update().get_or_create(user=payout.vendor.owner, defaults={"currency": payout.currency})
            if vendor_wallet.currency != payout.currency:
                raise ValidationError({"wallet": "عملة محفظة التاجر لا تطابق الطلب."})
            self._wallet(vendor_wallet, pay, WalletTransaction.Types.REWARD, f"ESCROW-PAYOUT-{payout.id}", f"إطلاق مستحقات الطلب {order.order_number}", {"order_id": order.id, "vendor_order_id": payout.vendor_order_id})
            VendorLedgerEntry.objects.get_or_create(
                reference=f"ESCROW-SALE-{payout.id}",
                defaults={"vendor": payout.vendor, "vendor_order": payout.vendor_order, "entry_type": VendorLedgerEntry.Types.SALE, "amount": pay, "balance_after": pay, "currency": payout.currency, "metadata": {"escrow_release": True, "order_id": order.id}},
            )
            payout.status = "paid"
            payout.amount = pay
            payout.save(update_fields=["status", "amount", "updated_at"])
            released += pay
        escrow["released_amount"] = str(released)
        held = Decimal(escrow.get("held_amount", "0.00"))
        unresolved = [x for x in disputes.values() if x.get("status") == "pending"]
        escrow["state"] = "partial_dispute" if unresolved else "released"
        order.metadata = {**(order.metadata or {}), "escrow": escrow}
        order.payment_status = "paid" if not unresolved else "partially_released"
        order.save(update_fields=["metadata", "payment_status", "updated_at"])
        self._notify(order.customer_id, "تم إطلاق مستحقات الطلب", f"تمت مراجعة طلبك {order.order_number} وإطلاق المستحقات غير المتنازع عليها.")
        return Response({"success": True, "released_amount": str(released), "held_amount": str(held), "state": escrow["state"]})

    @action(detail=True, methods=["post"])
    @transaction.atomic
    def resolve_item_dispute(self, request, pk=None):
        if not (request.user.is_staff or request.user.role == "admin"):
            raise PermissionDenied("للمدير فقط")
        order = self.get_queryset().select_for_update().get(pk=pk)
        item_id = str(request.data.get("order_item_id", ""))
        decision = str(request.data.get("decision", "")).lower()
        if not item_id.isdigit() or decision not in {"refund", "release"}:
            raise ValidationError({"decision": "استخدم refund أو release مع رقم القطعة."})
        item = order.items.select_related("vendor").filter(pk=int(item_id)).first()
        if not item:
            raise ValidationError({"order_item_id": "قطعة الطلب غير موجودة."})
        escrow = self._escrow(order)
        disputes = dict(escrow.get("disputes") or {})
        current = disputes.get(item_id)
        if not current or current.get("status") != "pending":
            raise ValidationError({"order_item_id": "لا يوجد اعتراض معلق لهذه القطعة."})
        wallet = Wallet.objects.select_for_update().get(user=order.customer)
        if decision == "refund":
            refund = Decimal(item.vendor_total)
            self._wallet(wallet, refund, WalletTransaction.Types.REFUND, f"DISPUTE-REFUND-{item.id}", f"استرداد قطعة من الطلب {order.order_number}", {"order_item_id": item.id})
            escrow["refunded_amount"] = str(Decimal(escrow.get("refunded_amount", "0.00")) + refund)
        else:
            payout = VendorPayout.objects.filter(order=order, vendor=item.vendor, status__in=["pending", "approved", "paid"]).first()
            vendor_wallet, _ = Wallet.objects.select_for_update().get_or_create(user=item.vendor.owner, defaults={"currency": order.currency})
            amount = Decimal(item.vendor_net)
            self._wallet(vendor_wallet, amount, WalletTransaction.Types.REWARD, f"DISPUTE-RELEASE-{item.id}", f"إطلاق مستحق القطعة بعد حل الاعتراض {order.order_number}", {"order_item_id": item.id})
            if payout:
                payout.status = "paid"
                payout.save(update_fields=["status", "updated_at"])
        current["status"] = "resolved_refund" if decision == "refund" else "resolved_release"
        current["resolved_at"] = timezone.now().isoformat()
        current["resolved_by"] = request.user.id
        disputes[item_id] = current
        escrow["disputes"] = disputes
        unresolved = [x for x in disputes.values() if x.get("status") == "pending"]
        escrow["state"] = "partial_dispute" if unresolved else "released"
        order.metadata = {**(order.metadata or {}), "escrow": escrow}
        if not unresolved and Decimal(escrow.get("held_amount", "0.00")) <= Decimal(escrow.get("released_amount", "0.00")) + Decimal(escrow.get("refunded_amount", "0.00")):
            order.payment_status = "paid"
        order.save(update_fields=["metadata", "payment_status", "updated_at"])
        self._notify(order.customer_id, "تم حل الاعتراض", f"تمت معالجة اعتراضك على القطعة في الطلب {order.order_number}.")
        self._notify(item.vendor.owner_id, "تم حل اعتراض على القطعة", f"تمت معالجة الاعتراض على القطعة {item.name_snapshot}.")
        return Response({"success": True, "decision": decision, "status": current["status"]})

    @action(detail=True, methods=["post"])
    @transaction.atomic
    def update_status(self, request, pk=None):
        order = self.get_object()
        user = request.user
        new_status = str(request.data.get("status", ""))
        if self._is_escrow(order) and user.role == "vendor":
            vendor_order = order.vendor_orders.filter(vendor__owner=user).select_for_update().first()
            if not vendor_order:
                raise PermissionDenied("لا تملك هذا الطلب")
            allowed = {"confirmed", "processing", "shipped", "delivered", "cancelled"}
            if new_status not in allowed:
                raise ValidationError({"status": "حالة التاجر غير صالحة"})
            old = vendor_order.status
            vendor_order.status = new_status
            vendor_order.save(update_fields=["status", "updated_at"])
            if new_status == "shipped":
                shipment = getattr(vendor_order, "shipment", None)
                if shipment:
                    shipment.status = "shipped"
                    shipment.shipped_at = shipment.shipped_at or timezone.now()
                    shipment.save(update_fields=["status", "shipped_at", "updated_at"])
            if new_status == "delivered" and old != "delivered":
                # Commit inventory without crediting the vendor wallet.
                for link in vendor_order.items.select_related("order_item__product").all():
                    item = link.order_item
                    reservation = InventoryReservation.objects.select_for_update().filter(order_item=item, status=InventoryReservation.Status.ACTIVE).first()
                    if reservation:
                        if reservation.variant_id:
                            variant = reservation.variant
                            variant.reserved_stock = max(0, variant.reserved_stock - reservation.quantity)
                            variant.stock = max(0, variant.stock - reservation.quantity)
                            variant.save(update_fields=["reserved_stock", "stock", "updated_at"])
                        elif reservation.product_id:
                            product = reservation.product
                            product.reserved_stock = max(0, product.reserved_stock - reservation.quantity)
                            product.stock = max(0, product.stock - reservation.quantity)
                            product.save(update_fields=["reserved_stock", "stock", "updated_at"])
                        reservation.status = InventoryReservation.Status.COMMITTED
                        reservation.save(update_fields=["status", "updated_at"])
                    item.product.sold_count += item.quantity
                    item.product.save(update_fields=["sold_count", "updated_at"])
                shipment = getattr(vendor_order, "shipment", None)
                if shipment:
                    shipment.status = "delivered"
                    shipment.delivered_at = timezone.now()
                    shipment.save(update_fields=["status", "delivered_at", "updated_at"])
            self._sync_parent_status(order)
            self._notify(order.customer_id, "تحديث طلبك", f"تم تحديث طلب {order.order_number} إلى: {new_status}")
            return Response({"vendor_order_id": vendor_order.id, "status": vendor_order.status, "order_status": order.status})
        response = super().update_status(request, pk=pk)
        order.refresh_from_db()
        label = {"confirmed": "تم تأكيد الطلب", "processing": "جارٍ تجهيز الطلب", "shipped": "تم شحن الطلب", "delivered": "تم تسليم الطلب", "cancelled": "تم إلغاء الطلب"}.get(new_status, new_status)
        self._notify(order.customer_id, "تحديث طلبك", f"{label}: {order.order_number}")
        return response
