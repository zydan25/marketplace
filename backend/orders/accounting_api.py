from datetime import timedelta
from decimal import Decimal

from django.db import transaction
from django.utils import timezone
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response

from accounting.models import Wallet as AccountingWallet
from accounting.order_ledger import (
    fund_order_revision,
    order_has_settlements,
    order_item_refunded,
    refund_order_item,
    refund_vendor_order,
    release_order_items,
    release_vendor_amount,
    reverse_current_funding,
    vendor_order_has_settlements,
)
from accounting.services_v2 import (
    account_balance,
    ensure_legacy_customer_opening,
    ensure_legacy_vendor_available,
    ensure_wallet,
    fund_order,
    wallet_summary,
)
from catalog.models import Product, ProductVariant
from communication.models import Notification
from finance.models import Wallet as LegacyWallet, VendorPayout
from promotions.models import Coupon

from .launch_order_api import LaunchOrderViewSet
from .models import InventoryReservation, Order, OrderStatusHistory, Payment, Shipment
from .secure_order_api import SecureOrderViewSet
from .serializers import OrderSerializer


class AccountingOrderViewSet(LaunchOrderViewSet):
    """Canonical v2 order lifecycle. Financial truth lives exclusively in double-entry journals."""

    @staticmethod
    def _record_sale(vendor_order):
        return None

    @staticmethod
    def _commit_vendor_order_inventory(vendor_order):
        for link in vendor_order.items.select_related("order_item__product").all():
            item = link.order_item
            reservation = (
                InventoryReservation.objects.select_for_update()
                .filter(order_item=item)
                .exclude(status=InventoryReservation.Status.RELEASED)
                .first()
            )
            if reservation and reservation.status == InventoryReservation.Status.ACTIVE:
                if reservation.variant_id:
                    variant = ProductVariant.objects.select_for_update().get(pk=reservation.variant_id)
                    variant.reserved_stock = max(0, variant.reserved_stock - reservation.quantity)
                    variant.stock = max(0, variant.stock - reservation.quantity)
                    variant.save(update_fields=["reserved_stock", "stock", "updated_at"])
                elif reservation.product_id:
                    product = Product.objects.select_for_update().get(pk=reservation.product_id)
                    product.reserved_stock = max(0, product.reserved_stock - reservation.quantity)
                    product.stock = max(0, product.stock - reservation.quantity)
                    product.save(update_fields=["reserved_stock", "stock", "updated_at"])
                reservation.status = InventoryReservation.Status.COMMITTED
                reservation.save(update_fields=["status", "updated_at"])
            elif reservation and reservation.status == InventoryReservation.Status.EXPIRED:
                raise ValidationError({"order": "لا يمكن تسليم الطلب لأن حجز المخزون منتهي."})
            item.product.sold_count = max(0, item.product.sold_count) + item.quantity
            item.product.save(update_fields=["sold_count", "updated_at"])
        VendorPayout.objects.get_or_create(
            vendor_order=vendor_order,
            defaults={
                "vendor": vendor_order.vendor,
                "order": vendor_order.order,
                "amount": vendor_order.vendor_net,
                "currency": vendor_order.currency,
                "status": "pending",
                "reference": f"PAYOUT-{vendor_order.id}",
            },
        )

    def _set_vendor_status(self, order, user, new_status):
        if getattr(user, "role", None) != "vendor":
            raise PermissionDenied("هذه العملية للتاجر فقط")
        vendor_order = order.vendor_orders.select_for_update().filter(vendor__owner=user).first()
        if not vendor_order:
            raise PermissionDenied("لا تملك هذا الطلب")
        allowed = {"confirmed", "processing", "shipped", "delivered", "cancelled"}
        if new_status not in allowed:
            raise ValidationError({"status": "حالة التاجر غير صالحة"})
        if new_status == "cancelled" and vendor_order_has_settlements(vendor_order):
            raise ValidationError({"status": "لا يمكن إلغاء طلب التاجر بعد بدء التسوية المالية. استخدم مسار الاعتراض والاسترداد."})
        old_status = vendor_order.status
        vendor_order.status = new_status
        vendor_order.save(update_fields=["status", "updated_at"])
        return vendor_order, old_status

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        if getattr(request.user, "role", None) != "customer":
            raise PermissionDenied("إنشاء الطلبات متاح للعملاء فقط")
        currency = str(request.data.get("currency", "YER")).upper()
        legacy_customer_wallet = LegacyWallet.objects.filter(user=request.user).first()
        legacy_customer_balance = Decimal(legacy_customer_wallet.balance) if legacy_customer_wallet else Decimal("0.00")
        ensure_legacy_customer_opening(request.user, legacy_customer_balance, currency)
        customer_wallet = ensure_wallet(request.user, AccountingWallet.Kinds.CUSTOMER, currency)
        mutable = request.data.copy()
        mutable["payment_method"] = "wallet"
        request._full_data = mutable
        response = SecureOrderViewSet.create(self, request, *args, **kwargs)
        order = Order.objects.select_for_update().get(pk=response.data["id"])
        self._reprice_vendor_shipping(order)
        self._refresh_vendor_finance(order)
        if account_balance(customer_wallet.account) < Decimal(order.total):
            raise ValidationError({"wallet": f"الرصيد المحاسبي غير كافٍ. المتاح {account_balance(customer_wallet.account)} {currency}."})
        for vendor_order in order.vendor_orders.select_related("vendor__owner").all():
            old = LegacyWallet.objects.filter(user=vendor_order.vendor.owner).first()
            old_balance = Decimal(old.balance) if old else Decimal("0.00")
            ensure_legacy_vendor_available(vendor_order.vendor.owner, old_balance, currency)
        entry = fund_order(order, created_by=request.user)
        order.metadata = {
            **(order.metadata or {}),
            "accounting_funding": {"journal": entry.number, "total": str(order.total), "currency": order.currency, "revision": 0},
            "escrow": {
                "state": "held",
                "held_amount": str(order.total),
                "released_amount": "0.00",
                "refunded_amount": "0.00",
                "customer_confirmed": False,
                "disputes": {},
            },
        }
        order.payment_method = "wallet"
        order.payment_status = "authorized"
        order.save(update_fields=["metadata", "payment_method", "payment_status", "updated_at"])
        payment = order.payment
        payment.provider = "wallet"
        payment.method = "wallet"
        payment.amount = order.total
        payment.status = Payment.Status.AUTHORIZED
        payment.paid_at = timezone.now()
        payment.metadata = {**(payment.metadata or {}), "escrow": True, "journal": entry.number}
        payment.save(update_fields=["provider", "method", "amount", "status", "paid_at", "metadata", "updated_at"])
        for vendor_order in order.vendor_orders.select_related("vendor__owner").all():
            payout, _ = VendorPayout.objects.get_or_create(
                vendor_order=vendor_order,
                defaults={"vendor": vendor_order.vendor, "order": order, "amount": vendor_order.vendor_net, "currency": order.currency, "status": "pending", "reference": f"PAYOUT-{vendor_order.id}"},
            )
            if payout.status == "pending":
                payout.amount = vendor_order.vendor_net
                payout.currency = order.currency
                payout.save(update_fields=["amount", "currency", "updated_at"])
            Notification.objects.create(recipient_id=vendor_order.vendor.owner_id, title="طلب جديد", body=f"وصل طلب جديد {order.order_number}. مستحقاتك معلقة محاسبيًا حتى تأكيد الاستلام.")
        Notification.objects.create(recipient_id=request.user.id, title="تم إنشاء طلبك", body=f"تم حجز {order.total} {order.currency} بقيد محاسبي لحماية عملية الشراء.")
        payload = OrderSerializer(order, context={"request": request}).data
        payload["financial"] = {
            "journal": entry.number,
            "customer_debited": str(order.total),
            "customer_balance": str(account_balance(customer_wallet.account)),
            "currency": order.currency,
            "vendor_status": "pending",
            "source_of_truth": "accounting_journal",
            "message": f"مرحبًا {request.user.get_full_name() or request.user.phone or request.user.username}، تم قبول الطلب وحجز قيمته من رصيدك.",
        }
        return Response(payload, status=response.status_code)

    @action(detail=True, methods=["post"])
    @transaction.atomic
    def update_pending(self, request, pk=None):
        order = self.get_queryset().select_for_update().get(pk=pk)
        if order.customer_id != request.user.id:
            raise PermissionDenied("لا تملك هذا الطلب")
        if order.status != Order.Status.PENDING or not (order.metadata or {}).get("accounting_funding"):
            raise ValidationError({"order": "يمكن تعديل الطلب الممول قبل تأكيد التاجر فقط."})
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
        reverse = reverse_current_funding(order, created_by=request.user, reason="عكس قيد تعديل الطلب")
        if not reverse:
            raise ValidationError({"order": "لم يتم العثور على قيد التمويل الحالي."})
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
                discount = (subtotal * coupon.discount_percent / Decimal("100")).quantize(Decimal("0.01")) if coupon.discount_percent else Decimal(coupon.discount_amount)
                order.discount = min(discount, subtotal)
        else:
            order.discount = min(Decimal(order.discount), subtotal)
        if isinstance(request.data.get("shipping_address"), dict):
            order.shipping_address = request.data["shipping_address"]
        order.save(update_fields=["subtotal", "discount", "shipping_address", "updated_at"])
        self._reprice_vendor_shipping(order)
        self._refresh_vendor_finance(order)
        customer_wallet = ensure_wallet(request.user, AccountingWallet.Kinds.CUSTOMER, order.currency)
        if account_balance(customer_wallet.account) < Decimal(order.total):
            raise ValidationError({"wallet": "الرصيد المحاسبي غير كافٍ للقيمة الجديدة؛ لم يتم تغيير العملية."})
        revision = int(((order.metadata or {}).get("accounting_funding") or {}).get("revision", 0)) + 1
        entry = fund_order_revision(order, revision, created_by=request.user)
        order.metadata = {**(order.metadata or {}), "accounting_funding": {"journal": entry.number, "total": str(order.total), "currency": order.currency, "revision": revision}, "escrow": {**self._escrow(order), "held_amount": str(order.total)}}
        order.payment_status = "authorized"
        order.save(update_fields=["metadata", "payment_status", "updated_at"])
        Payment.objects.filter(order=order).update(amount=order.total, updated_at=timezone.now())
        for vendor_order in order.vendor_orders.select_for_update().all():
            payout = VendorPayout.objects.filter(vendor_order=vendor_order, status="pending").first()
            if payout:
                payout.amount = vendor_order.vendor_net
                payout.save(update_fields=["amount", "updated_at"])
        return Response(OrderSerializer(order, context={"request": request}).data)

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
        released = release_order_items(order, created_by=request.user)
        escrow["customer_confirmed"] = True
        escrow["customer_confirmed_at"] = timezone.now().isoformat()
        escrow["state"] = "released"
        escrow["released_amount"] = str(Decimal(escrow.get("released_amount", "0.00")) + released)
        order.metadata = {**(order.metadata or {}), "escrow": escrow}
        order.payment_status = "partially_refunded" if Decimal(escrow.get("refunded_amount", "0.00")) > 0 else "paid"
        order.save(update_fields=["metadata", "payment_status", "updated_at"])
        for payout in VendorPayout.objects.select_for_update().filter(order=order, status="pending"):
            payout.status = "paid"
            payout.save(update_fields=["status", "updated_at"])
        return Response({"success": True, "message": "تم تأكيد الاستلام وإطلاق مستحقات التجار في القيود المحاسبية.", "released_amount": str(released), "balance": wallet_summary(request.user, order.currency)})

    @action(detail=True, methods=["post"])
    @transaction.atomic
    def admin_release(self, request, pk=None):
        if not (request.user.is_staff or getattr(request.user, "role", None) == "admin"):
            raise PermissionDenied("للمدير فقط")
        order = self.get_queryset().select_for_update().get(pk=pk)
        escrow = self._escrow(order)
        if not escrow or not escrow.get("customer_confirmed"):
            raise ValidationError({"order": "يجب تأكيد الاستلام أولاً."})
        if any(value.get("status") == "pending" for value in (escrow.get("disputes") or {}).values()):
            raise ValidationError({"order": "لا يمكن اعتماد التسوية مع اعتراضات مفتوحة."})
        released = release_order_items(order, created_by=request.user)
        escrow["released_amount"] = str(Decimal(escrow.get("released_amount", "0.00")) + released)
        escrow["state"] = "released"
        order.metadata = {**(order.metadata or {}), "escrow": escrow}
        order.payment_status = "paid"
        order.save(update_fields=["metadata", "payment_status", "updated_at"])
        return Response({"success": True, "released_amount": str(released), "state": "released", "balance": wallet_summary(order.customer, order.currency)})

    @action(detail=True, methods=["post"])
    @transaction.atomic
    def resolve_item_dispute(self, request, pk=None):
        if not (request.user.is_staff or getattr(request.user, "role", None) == "admin"):
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
        if decision == "refund":
            entry = refund_order_item(order, item, created_by=request.user)
            escrow["refunded_amount"] = str(Decimal(escrow.get("refunded_amount", "0.00")) + Decimal(item.vendor_total))
            result = {"journal": entry.number, "refund": str(item.vendor_total)}
        else:
            entry = release_vendor_amount(item.vendor.owner, Decimal(item.vendor_net), order.currency, vendor_order_id=item.vendor_order_id, release_key=f"item:{item.id}", item_ids=[item.id], created_by=request.user)
            result = {"journal": entry.number if entry else None, "release": str(item.vendor_net)}
        current["status"] = "resolved_refund" if decision == "refund" else "resolved_release"
        current["resolved_at"] = timezone.now().isoformat()
        current["resolved_by"] = request.user.id
        disputes[item_id] = current
        escrow["disputes"] = disputes
        escrow["state"] = "partial_dispute" if any(value.get("status") == "pending" for value in disputes.values()) else "awaiting_release"
        order.payment_status = "partially_refunded" if Decimal(escrow.get("refunded_amount", "0.00")) > 0 else "authorized"
        order.metadata = {**(order.metadata or {}), "escrow": escrow}
        order.save(update_fields=["metadata", "payment_status", "updated_at"])
        return Response({"success": True, "decision": decision, "status": current["status"], **result})

    @action(detail=True, methods=["post"])
    @transaction.atomic
    def update_vendor_status(self, request, pk=None):
        order = self.get_object()
        vendor_order, old_status = self._set_vendor_status(order, request.user, str(request.data.get("status", "")))
        if vendor_order.status == "delivered" and old_status != "delivered":
            self._commit_vendor_order_inventory(vendor_order)
            shipment = getattr(vendor_order, "shipment", None)
            if shipment:
                shipment.status = Shipment.Status.DELIVERED
                shipment.delivered_at = shipment.delivered_at or timezone.now()
                shipment.save(update_fields=["status", "delivered_at", "updated_at"])
        if vendor_order.status == "cancelled" and old_status != "cancelled":
            refund_vendor_order(order, vendor_order, created_by=request.user)
        self._sync_parent_status(order)
        return Response({"vendor_order_id": vendor_order.id, "status": vendor_order.status, "order_status": order.status})

    @action(detail=True, methods=["post"])
    @transaction.atomic
    def update_status(self, request, pk=None):
        order = self.get_object()
        user = request.user
        new_status = str(request.data.get("status", ""))
        if getattr(user, "role", None) == "vendor":
            vendor_order, old_status = self._set_vendor_status(order, user, new_status)
            if new_status == "delivered" and old_status != "delivered":
                self._commit_vendor_order_inventory(vendor_order)
                shipment = getattr(vendor_order, "shipment", None)
                if shipment:
                    shipment.status = Shipment.Status.DELIVERED
                    shipment.delivered_at = shipment.delivered_at or timezone.now()
                    shipment.save(update_fields=["status", "delivered_at", "updated_at"])
            if new_status == "cancelled" and old_status != "cancelled":
                refund_vendor_order(order, vendor_order, created_by=user)
            self._sync_parent_status(order)
            return Response({"vendor_order_id": vendor_order.id, "status": vendor_order.status, "order_status": order.status})
        if not (user.is_staff or getattr(user, "role", None) == "admin"):
            raise PermissionDenied("لا تملك صلاحية تغيير حالة الطلب")
        if new_status not in {choice.value for choice in Order.Status}:
            raise ValidationError({"status": "حالة الطلب غير صالحة"})
        old_status = order.status
        if new_status == Order.Status.CANCELLED and self._is_escrow(order):
            if order_has_settlements(order):
                raise ValidationError({"status": "لا يمكن إلغاء طلب له تسويات مالية قائمة. عالج الاعتراضات والاستردادات أولاً."})
            entry = reverse_current_funding(order, created_by=user, reason="عكس قيد إلغاء الطلب")
            if entry:
                escrow = self._escrow(order)
                escrow["state"] = "refunded"
                escrow["refunded_amount"] = str(Decimal(escrow.get("refunded_amount", "0.00")) + Decimal(escrow.get("held_amount", "0.00")))
                order.metadata = {**(order.metadata or {}), "escrow": escrow, "accounting_cancellation": entry.number}
                order.payment_status = "refunded"
                payment = getattr(order, "payment", None)
                if payment:
                    payment.status = Payment.Status.REFUNDED
                    payment.refunded_amount = payment.amount
                    payment.save(update_fields=["status", "refunded_amount", "updated_at"])
        order.status = new_status
        order.save(update_fields=["status", "updated_at"])
        OrderStatusHistory.objects.create(order=order, old_status=old_status, new_status=new_status, changed_by=user)
        if new_status == Order.Status.CANCELLED and self._is_escrow(order):
            order.save(update_fields=["metadata", "payment_status", "updated_at"])
            Notification.objects.create(recipient_id=order.customer_id, title="تم إلغاء الطلب واسترداد الرصيد", body=f"تم إلغاء الطلب {order.order_number} وعكس قيده المالي.")
        return Response(OrderSerializer(order, context={"request": request}).data)

    @action(detail=True, methods=["post"])
    @transaction.atomic
    def reject_item(self, request, pk=None):
        order = self.get_queryset().select_for_update().get(pk=pk)
        if self._escrow(order).get("customer_confirmed"):
            raise ValidationError({"order": "تم تأكيد الاستلام نهائيًا."})
        return super().reject_item(request, pk=pk)

    @action(detail=True, methods=["post"])
    @transaction.atomic
    def reject_order(self, request, pk=None):
        order = self.get_queryset().select_for_update().get(pk=pk)
        if self._escrow(order).get("customer_confirmed"):
            raise ValidationError({"order": "تم تأكيد الاستلام نهائيًا."})
        return super().reject_order(request, pk=pk)
