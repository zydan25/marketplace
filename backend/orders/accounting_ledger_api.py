from decimal import Decimal

from django.db import transaction
from django.utils import timezone
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response

from accounting.order_ledger import item_accounting_amount, refund_order_item, release_vendor_amount

from .accounting_api import AccountingOrderViewSet
from .models import Order


class LedgerAccountingOrderViewSet(AccountingOrderViewSet):
    """Final canonical order API with allocation-aware dispute journals."""

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
        vendor_order = item.vendor_order_item.vendor_order
        allocated_net, allocated_commission, allocated_total = item_accounting_amount(vendor_order, item)
        if decision == "refund":
            entry = refund_order_item(order, item, created_by=request.user)
            refund = Decimal(entry.metadata["refund"])
            escrow["refunded_amount"] = str(Decimal(escrow.get("refunded_amount", "0.00")) + refund)
            payment = order.payment
            payment.refunded_amount = Decimal(payment.refunded_amount) + refund
            payment.status = Payment.Status.PARTIALLY_REFUNDED if payment.refunded_amount < payment.amount else Payment.Status.REFUNDED
            payment.save(update_fields=["refunded_amount", "status", "updated_at"])
            result = {"journal": entry.number, "refund": str(refund)}
        else:
            entry = release_vendor_amount(
                item.vendor.owner,
                allocated_net,
                order.currency,
                vendor_order_id=vendor_order.id,
                release_key=f"item:{item.id}",
                item_ids=[item.id],
                created_by=request.user,
                metadata={"order_item_id": item.id, "allocated_vendor_net": str(allocated_net), "allocated_commission": str(allocated_commission)},
            )
            result = {"journal": entry.number if entry else None, "release": str(allocated_net), "total": str(allocated_total)}
        current["status"] = "resolved_refund" if decision == "refund" else "resolved_release"
        current["resolved_at"] = timezone.now().isoformat()
        current["resolved_by"] = request.user.id
        current["accounting"] = {"vendor_net": str(allocated_net), "commission": str(allocated_commission), "total": str(allocated_total)}
        disputes[item_id] = current
        escrow["disputes"] = disputes
        escrow["state"] = "partial_dispute" if any(value.get("status") == "pending" for value in disputes.values()) else "awaiting_release"
        order.payment_status = "partially_refunded" if Decimal(escrow.get("refunded_amount", "0.00")) > 0 else "authorized"
        order.metadata = {**(order.metadata or {}), "escrow": escrow}
        order.save(update_fields=["metadata", "payment_status", "updated_at"])
        return Response({"success": True, "decision": decision, "status": current["status"], **result})
