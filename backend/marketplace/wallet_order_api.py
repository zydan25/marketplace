from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response
from .secure_order_api import SecureOrderViewSet
from .models import Wallet, WalletTransaction, VendorPayout, OrderStatusHistory
from .models_extra import WalletHold, OrderItemDecision, VendorCityShipping
from .marketplace_models import Payment

class WalletOrderViewSet(SecureOrderViewSet):
    @transaction.atomic
    def create(self, request, *args, **kwargs):
        if str(request.data.get("payment_method", "wallet")).lower() not in {"wallet", "balance"}: raise ValidationError({"payment_method": "الدفع في المتجر يتم من رصيد العميل فقط."})
        mutable=request.data.copy(); mutable["payment_method"]="wallet"; request._full_data=mutable
        response=super().create(request,*args,**kwargs)
        order=self.get_queryset().select_for_update().get(order_number=response.data.get("order_number"))
        city_id=(order.shipping_address or {}).get("city_id")
        if city_id:
            vendor_orders=list(order.vendor_orders.select_related("vendor"))
            total_shipping=Decimal("0.00")
            for vendor_order in vendor_orders:
                fee=(VendorCityShipping.objects.filter(vendor=vendor_order.vendor_id,city_id=city_id,is_active=True).values_list("fee",flat=True).first())
                if fee is None: fee=Decimal("0.00")
                vendor_order.shipping_fee=fee
                vendor_order.total=max(Decimal("0.00"),vendor_order.subtotal-vendor_order.discount+fee)
                vendor_order.vendor_net=max(Decimal("0.00"),vendor_order.subtotal-vendor_order.commission+fee)
                vendor_order.save(update_fields=["shipping_fee","total","vendor_net","updated_at"])
                total_shipping += fee
            order.shipping_fee=total_shipping; order.total=max(Decimal("0.00"),order.subtotal-order.discount+total_shipping); order.save(update_fields=["shipping_fee","total","updated_at"])
            payment=order.payment; payment.amount=order.total; payment.save(update_fields=["amount","updated_at"])
        wallet=Wallet.objects.select_for_update().filter(user=request.user).first()
        if not wallet: raise ValidationError({"wallet": "لا يوجد رصيد مرتبط بالحساب."})
        if wallet.currency!=order.currency: raise ValidationError({"wallet": "عملة الرصيد لا تطابق عملة الطلب."})
        if wallet.is_locked or wallet.balance<order.total: raise ValidationError({"wallet": "الرصيد غير كافٍ لإتمام الطلب."})
        wallet.balance-=order.total; wallet.save(update_fields=["balance","updated_at"])
        hold_ref=f"ORDER-HOLD-{order.id}"
        WalletTransaction.objects.create(wallet=wallet,transaction_type=WalletTransaction.Types.PAYMENT,amount=-order.total,balance_after=wallet.balance,reference=hold_ref,note=f"حجز طلب {order.order_number}",metadata={"order_id":order.id,"escrow":True})
        hold=WalletHold.objects.create(wallet=wallet,order=order,amount=order.total,note="مبلغ معلق حتى استلام العميل واعتماد الإدارة")
        payment=order.payment; payment.status=Payment.Status.AUTHORIZED; payment.provider="wallet"; payment.method="wallet"; payment.paid_at=timezone.now(); payment.metadata={**(payment.metadata or {}),"escrow_hold_id":hold.id}; payment.save(update_fields=["status","provider","method","paid_at","metadata","updated_at"])
        order.payment_status="authorized"; order.metadata={**(order.metadata or {}),"escrow":True,"customer_confirmed":False,"admin_released":False}; order.save(update_fields=["payment_status","metadata","updated_at"])
        return Response(response.data,status=response.status_code,headers=response.headers)

    @action(detail=True,methods=["post"])
    @transaction.atomic
    def confirm_received(self,request,pk=None):
        order=self.get_queryset().select_for_update().get(pk=pk)
        if order.customer_id!=request.user.id: raise PermissionDenied("لا تملك هذا الطلب")
        hold=WalletHold.objects.select_for_update().get(order=order)
        if hold.status not in {WalletHold.Status.HELD,WalletHold.Status.PARTIAL}: raise ValidationError({"order":"لا يوجد مبلغ معلق لهذا الطلب."})
        order.metadata={**(order.metadata or {}),"customer_confirmed":True,"confirmed_at":timezone.now().isoformat()}; order.save(update_fields=["metadata","updated_at"])
        return Response({"success":True,"status":"بانتظار اعتماد الإدارة"})

    @action(detail=True,methods=["post"])
    @transaction.atomic
    def admin_release(self,request,pk=None):
        if not (request.user.is_staff or request.user.role=="admin"): raise PermissionDenied("للمدير فقط")
        order=self.get_queryset().select_for_update().get(pk=pk); hold=WalletHold.objects.select_for_update().get(order=order)
        if not (order.metadata or {}).get("customer_confirmed"): raise ValidationError({"order":"يجب أن يؤكد العميل استلام الطلب أولاً."})
        remaining=hold.amount-hold.refunded_amount-hold.released_amount
        for payout in VendorPayout.objects.select_for_update().filter(order=order,status="pending"):
            vendor_wallet,_=Wallet.objects.select_for_update().get_or_create(user=payout.vendor.owner,defaults={"currency":payout.currency})
            if vendor_wallet.currency!=payout.currency: raise ValidationError({"wallet":"عملة محفظة التاجر لا تطابق الطلب."})
            vendor_wallet.balance+=payout.amount; vendor_wallet.save(update_fields=["balance","updated_at"])
            WalletTransaction.objects.create(wallet=vendor_wallet,transaction_type=WalletTransaction.Types.REWARD,amount=payout.amount,balance_after=vendor_wallet.balance,reference=f"PAYOUT-{payout.id}",note=f"إطلاق طلب {order.order_number}",metadata={"vendor_order_id":payout.vendor_order_id})
            payout.status="paid"; payout.save(update_fields=["status","updated_at"])
        hold.released_amount+=max(Decimal("0.00"),remaining); hold.status=WalletHold.Status.RELEASED if hold.refunded_amount==0 else WalletHold.Status.PARTIAL; hold.save(update_fields=["released_amount","status","updated_at"])
        order.metadata={**(order.metadata or {}),"admin_released":True,"released_at":timezone.now().isoformat()}; order.payment_status="paid"; order.save(update_fields=["metadata","payment_status","updated_at"])
        return Response({"success":True,"status":hold.status,"released_amount":str(hold.released_amount)})

    @action(detail=True,methods=["post"])
    @transaction.atomic
    def reject_item(self,request,pk=None):
        order=self.get_queryset().select_for_update().get(pk=pk)
        if request.user.role!="vendor": raise PermissionDenied("رفض القطعة متاح للتاجر فقط")
        vendor_order=order.vendor_orders.filter(vendor__owner=request.user).first()
        if not vendor_order: raise PermissionDenied("لا تملك هذا الطلب")
        item=order.items.filter(pk=request.data.get("order_item_id"),vendor=vendor_order.vendor).first()
        if not item: raise ValidationError({"order_item_id":"قطعة الطلب غير موجودة."})
        reason=str(request.data.get("reason","")).strip()
        if not reason: raise ValidationError({"reason":"سبب الرفض مطلوب."})
        decision,_=OrderItemDecision.objects.select_for_update().get_or_create(order_item=item)
        if decision.status==OrderItemDecision.Status.REJECTED: raise ValidationError({"order_item":"تم رفض القطعة مسبقًا."})
        decision.status=OrderItemDecision.Status.REJECTED; decision.reason=reason; decision.decided_by=request.user; decision.save()
        refund=item.vendor_total; hold=WalletHold.objects.select_for_update().get(order=order); refund=min(refund,max(Decimal("0.00"),hold.amount-hold.refunded_amount))
        wallet=Wallet.objects.select_for_update().get(user=order.customer); wallet.balance+=refund; wallet.save(update_fields=["balance","updated_at"])
        WalletTransaction.objects.create(wallet=wallet,transaction_type=WalletTransaction.Types.REFUND,amount=refund,balance_after=wallet.balance,reference=f"REFUND-{item.id}",note=f"استرداد قطعة مرفوضة من {order.order_number}",metadata={"order_item_id":item.id})
        hold.refunded_amount+=refund; hold.status=WalletHold.Status.PARTIAL if hold.refunded_amount<hold.amount else WalletHold.Status.REFUNDED; hold.save(update_fields=["refunded_amount","status","updated_at"])
        return Response({"success":True,"order_item_id":item.id,"status":"rejected","refund":str(refund),"reason":reason})
