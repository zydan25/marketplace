from decimal import Decimal

from django.db import transaction
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from finance.models import Wallet as LegacyWallet
from .launch_order_api import LaunchOrderViewSet
from .models import Order, VendorOrder
from .serializers import OrderSerializer
from accounting.models import Wallet as AccountingWallet
from accounting.services import account_balance, ensure_legacy_customer_opening, ensure_legacy_vendor_available, ensure_wallet, fund_order, release_vendor_pending, wallet_summary


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
        requested_rows = request.data.get("items") or []
        legacy_vendor_snapshots = {}
        from catalog.models import Product
        for row in requested_rows:
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

        # The exact total is calculated by the trusted server-side checkout below.
        # A pre-check against the existing accounting balance prevents accepting a request
        # that can never be funded; the definitive amount check happens again after pricing.
        if accounting_balance < 0:
            raise ValidationError({"wallet": "تعذر قراءة رصيد المحفظة المحاسبية."})

        response = super().create(request, *args, **kwargs)
        order = Order.objects.select_for_update().get(pk=response.data["id"])
        self._reprice_vendor_shipping(order)
        self._refresh_vendor_finance(order)

        # The amount may change after shipping repricing, so perform the authoritative check now.
        if account_balance(customer_wallet.account) < Decimal(order.total):
            raise ValidationError({"wallet": f"الرصيد المحاسبي غير كافٍ. المتاح {account_balance(customer_wallet.account)} {currency}."})

        for vendor_order in order.vendor_orders.select_related("vendor__owner").all():
            snapshot = legacy_vendor_snapshots.get(vendor_order.vendor.owner_id)
            ensure_legacy_vendor_available(vendor_order.vendor.owner, snapshot or Decimal("0.00"), currency)

        fund_order(order, created_by=request.user)
        payload = OrderSerializer(order, context={"request": request}).data
        payload["financial"] = {
            "customer_debited": str(order.total),
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
            release_vendor_pending(
                vendor_order.vendor.owner,
                Decimal(vendor_order.vendor_net),
                vendor_order.currency,
                vendor_order_id=vendor_order.id,
                created_by=request.user,
            )
        summary = wallet_summary(request.user, order.currency)
        return Response({
            **response.data,
            "message": "تم تأكيد الاستلام وإطلاق مستحقات التجار إلى الرصيد المتاح للسحب.",
            "balance": summary,
        })

    @transaction.atomic
    def update_pending(self, request, pk=None):
        response = super().update_pending(request, pk=pk)
        order = Order.objects.select_for_update().get(pk=pk)
        # Rebuild the accounting order funding entry after a checkout edit. The edit method
        # changed the legacy escrow hold; in the accounting layer the safest invariant is to
        # reject a changed total rather than silently mutate a posted journal.
        existing = order.metadata.get("accounting_funding") if order.metadata else None
        if existing and existing.get("total") != str(order.total):
            raise ValidationError({"order": "تم تعديل قيمة طلب ممول محاسبيًا؛ يجب إلغاء التمويل القديم وإعادة إنشاء الطلب قبل تغيير القيمة."})
        return response
