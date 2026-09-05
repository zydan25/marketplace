from decimal import Decimal

from django.db import transaction
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from finance.models import Wallet as LegacyWallet
from .launch_order_api import LaunchOrderViewSet
from .models import Order
from .serializers import OrderSerializer
from accounting.models import Wallet as AccountingWallet
from accounting.services_v2 import account_balance, ensure_legacy_customer_opening, ensure_legacy_vendor_available, ensure_wallet, fund_order, release_vendor_pending, wallet_summary


class AccountingOrderViewSet(LaunchOrderViewSet):
    """Canonical checkout lifecycle backed by the double-entry accounting ledger."""

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        if getattr(request.user, "role", None) != "customer":
            return super().create(request, *args, **kwargs)
        currency = str(request.data.get("currency", "YER")).upper()
        legacy_customer_wallet = LegacyWallet.objects.select_for_update().filter(user=request.user).first()
        legacy_customer_balance = Decimal(legacy_customer_wallet.balance) if legacy_customer_wallet else Decimal("0.00")
        ensure_legacy_customer_opening(request.user, legacy_customer_balance, currency)
        customer_wallet = ensure_wallet(request.user, AccountingWallet.Kinds.CUSTOMER, currency)
        accounting_balance = account_balance(customer_wallet.account)
        if accounting_balance < 0:
            raise ValidationError({"wallet": "رصيد المحفظة المحاسبي غير صالح."})
        legacy_vendor_snapshots = {}
        from catalog.models import Product
        for row in request.data.get("items") or []:
            try:
                product_id = int(row.get("product_id"))
            except (AttributeError, TypeError, ValueError):
                continue
            product = Product.objects.select_related("vendor__owner").filter(pk=product_id).first()
            if product and product.vendor and product.vendor.owner_id:
                owner_id = product.vendor.owner_id
                if owner_id not in legacy_vendor_snapshots:
                    old = LegacyWallet.objects.filter(user_id=owner_id).first()
                    legacy_vendor_snapshots[owner_id] = Decimal(old.balance) if old else Decimal("0.00")

        response = super().create(request, *args, **kwargs)
        order = Order.objects.select_for_update().get(pk=response.data["id"])
        self._reprice_vendor_shipping(order)
        self._refresh_vendor_finance(order)
        authoritative_balance = account_balance(customer_wallet.account)
        if authoritative_balance < Decimal(order.total):
            raise ValidationError({"wallet": f"الرصيد المحاسبي غير كافٍ. المتاح {authoritative_balance} {currency}."})

        for vendor_order in order.vendor_orders.select_related("vendor__owner").all():
            snapshot = legacy_vendor_snapshots.get(vendor_order.vendor.owner_id)
            ensure_legacy_vendor_available(vendor_order.vendor.owner, snapshot or Decimal("0.00"), currency)

        entry = fund_order(order, created_by=request.user)
        order.metadata = {
            **(order.metadata or {}),
            "accounting_funding": {"journal": entry.number, "total": str(order.total), "currency": order.currency},
        }
        order.save(update_fields=["metadata", "updated_at"])
        payload = OrderSerializer(order, context={"request": request}).data
        balance_after = account_balance(customer_wallet.account)
        payload["financial"] = {
            "journal": entry.number,
            "customer_debited": str(order.total),
            "customer_balance": str(balance_after),
            "currency": order.currency,
            "vendor_status": "pending",
            "message": f"مرحبًا {request.user.get_full_name() or request.user.phone or request.user.username}، تم قبول الطلب وحجز قيمته من رصيدك. مستحقات التاجر معلقة حتى تأكيد الاستلام.",
        }
        return Response(payload, status=response.status_code)

    @transaction.atomic
    def confirm_received(self, request, pk=None):
        response = super().confirm_received(request, pk=pk)
        order = Order.objects.select_for_update().prefetch_related("vendor_orders__vendor__owner").get(pk=pk)
        for vendor_order in order.vendor_orders.all():
            release_vendor_pending(vendor_order.vendor.owner, Decimal(vendor_order.vendor_net), vendor_order.currency, vendor_order_id=vendor_order.id, created_by=request.user)
        return Response({
            **response.data,
            "message": "تم تأكيد الاستلام وإطلاق مستحقات التجار إلى الرصيد المتاح للسحب.",
            "balance": wallet_summary(request.user, order.currency),
        })

    @transaction.atomic
    def update_pending(self, request, pk=None):
        order = self.get_queryset().select_for_update().get(pk=pk)
        if (order.metadata or {}).get("accounting_funding"):
            raise ValidationError({"order": "تم تمويل الطلب محاسبيًا؛ لا يمكن تغيير القيمة بعد ترحيل القيد."})
        return super().update_pending(request, pk=pk)

    @transaction.atomic
    def reject_item(self, request, pk=None):
        order = self.get_queryset().select_for_update().get(pk=pk)
        if (order.metadata or {}).get("escrow", {}).get("customer_confirmed"):
            raise ValidationError({"order": "تم تأكيد الاستلام نهائيًا."})
        return super().reject_item(request, pk=pk)

    @transaction.atomic
    def reject_order(self, request, pk=None):
        order = self.get_queryset().select_for_update().get(pk=pk)
        if (order.metadata or {}).get("escrow", {}).get("customer_confirmed"):
            raise ValidationError({"order": "تم تأكيد الاستلام نهائيًا."})
        return super().reject_order(request, pk=pk)
