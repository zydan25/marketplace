from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response
from .models import Wallet, WalletTransaction, VendorPayout
from .models_extra import WalletHold, OrderItemDecision, VendorCityShipping, MarketplaceOffice
from .models_extended import City
from .marketplace_models import Payment, PlatformLedgerEntry
from .secure_order_v2 import SecureOrderV2ViewSet

def order_response(order,request):
    from .serializers import OrderSerializer
    return OrderSerializer(order,context={"request":request}).data

class WalletOrderV2ViewSet(SecureOrderV2ViewSet):
    @transaction.atomic
    def create(self,request,*args,**kwargs):
        if str(request.data.get("payment_method","")).lower() not in {"wallet","balance"}: raise ValidationError({"payment_method":"الدفع في المنصة يتم من رصيد العميل فقط."})
        mutable=request.data.copy(); mutable["payment_method"]="wallet"; request._full_data=mutable
        response=super().create(request,*args,**kwargs); order=self.get_queryset().select_for_update().get(order_number=response.data.get("order_number")); address=order.shipping_address or {}; city_id=address.get("city_id"); city=City.objects.filter(pk=city_id,is_active=True).first() if city_id else None
        if city_id and not city: raise ValidationError({"shipping_address":{"city_id":"المدينة غير صالحة."}})
        office_fee=Decimal("0.00")
        if city:
            office=MarketplaceOffice.objects.filter(city=city,is_active=True).first()
            if office: office_fee=office.office_fee
        vendor_shipping_total=Decimal("0.00")
        for vendor_order in order.vendor_orders.select_for_update().select_related("vendor"):
            fee=Decimal("0.00")
            if city:
                rule=VendorCityShipping.objects.filter(vendor=vendor_order.vendor,city=city,is_active=True).first(); fee=rule.fee if rule else city.shipping_fee
            vendor_order.shipping_fee=fee; vendor_order.total=max(Decimal("0.00"),vendor_order.subtotal-vendor_order.discount+fee); vendor_order.vendor_net=vendor_order.subtotal-vendor_order.commission+fee; vendor_order.save(update_fields=["shipping_fee","total","vendor_net","updated_at"]); vendor_shipping_total+=fee
        order.shipping_fee=vendor_shipping_total+office_fee; order.total=max(Decimal("0.00"),order.subtotal-order.discount+order.shipping_fee); order.metadata={**(order.metadata or {}),"shipping_source":"vendor_city","office_fee":str(office_fee),"vendor_shipping_fee":str(vendor_shipping_total)}; order.save(update_fields=["shipping_fee","total","metadata","updated_at"])
        payment=order.payment; payment.amount=order.total; payment.save(update_fields=["amount","updated_at"]); wallet=Wallet.objects.select_for_update().filter(user=request.user).first()
        if not wallet: raise ValidationError({"wallet":"لا توجد محفظة مرتبطة بالحساب."})
        if wallet.currency!=order.currency: raise ValidationError({"wallet":"عملة الرصيد لا تطابق عملة الطلب."})
        if wallet.is_locked or wallet.balance<order.total: raise ValidationError({"wallet":"الرصيد غير كافٍ لإتمام الطلب."})
        wallet.balance-=order.total; wallet.save(update_fields=["balance","updated_at"]); hold=WalletHold.objects.create(wallet=wallet,order=order,amount=order.total,note="مبلغ معلق حتى تأكيد العميل واعتماد الإدارة",metadata={"office_fee":str(office_fee),"vendor_shipping_fee":str(vendor_shipping_total)})
        WalletTransaction.objects.create(wallet=wallet,transaction_type=WalletTransaction.Types.PAYMENT,amount=-order.total,balance_after=wallet.balance,reference=f"ORDER-HOLD-{order.id}",note=f"حجز طلب {order.order_number}",metadata={"order_id":order.id,"hold_id":hold.id})
        payment.status=Payment.Status.AUTHORIZED; payment.provider="wallet"; payment.method="wallet"; payment.paid_at=timezone.now(); payment.metadata={**(payment.metadata or {}),"escrow_hold_id":hold.id}; payment.save(update_fields=["status","provider","method","paid_at","metadata","updated_at"])
        order.payment_status="authorized"; order.metadata={**(order.metadata or {}),"escrow":True,"customer_confirmed":False,"admin_released":False}; order.save(update_fields=["payment_status","metadata","updated_at"])
        return Response(order_response(order,request),status=response.status_code,headers=response.headers)

    @action(detail=True,methods=["post"])
    @transaction.atomic
    def confirm_received(self,request,pk=None):
        order=self.get_queryset().select_for_update().get(pk=pk)
        if order.customer_id!=request.user.id: raise PermissionDenied("لا تملك هذا الطلب")
        hold=WalletHold.objects.select_for_update().filter(order=order).first()
        if not hold or hold.status not in {WalletHold.Status.HELD,WalletHold.Status.PARTIAL}: raise ValidationError({"order":"لا يوجد مبلغ معلق لهذا الطلب."})
        order.metadata={**(order.metadata or {}),"customer_confirmed":True,"confirmed_at":timezone.now().isoformat()}; order.save(update_fields=["metadata","updated_at"]); return Response({"success":True,"status":"بانتظار اعتماد الإدارة"})

    @action(detail=True,methods=["post"])
    @transaction.atomic
    def admin_release(self,request,pk=None):
        if not(request.user.is_staff or request.user.role=="admin"): raise PermissionDenied("للمدير فقط")
        order=self.get_queryset().select_for_update().get(pk=pk); hold=WalletHold.objects.select_for_update().filter(order=order).first()
        if not hold: raise ValidationError({"order":"لا يوجد حجز مالي لهذا الطلب."})
        if not(order.metadata or {}).get("customer_confirmed"): raise ValidationError({"order":"يجب أن يؤكد العميل استلام الطلب أولاً."})
        remaining=hold.amount-hold.refunded_amount-hold.released_amount
        if remaining<=0:return Response({"success":True,"status":hold.status,"released_amount":str(hold.released_amount)})
        payout_total=Decimal("0.00")
        for payout in VendorPayout.objects.select_for_update().filter(order=order,status="pending"):
            payout_total+=payout.amount
            vendor_wallet,_=Wallet.objects.select_for_update().get_or_create(user=payout.vendor.owner,defaults={"currency":payout.currency})
            if vendor_wallet.currency!=payout.currency: raise ValidationError({"wallet":"عملة محفظة التاجر لا تطابق الطلب."})
            vendor_wallet.balance+=payout.amount; vendor_wallet.save(update_fields=["balance","updated_at"]); WalletTransaction.objects.create(wallet=vendor_wallet,transaction_type=WalletTransaction.Types.REWARD,amount=payout.amount,balance_after=vendor_wallet.balance,reference=f"PAYOUT-{payout.id}",note=f"إطلاق طلب {order.order_number}",metadata={"vendor_order_id":payout.vendor_order_id}); payout.status="paid"; payout.save(update_fields=["status","updated_at"])
        platform_amount=remaining-payout_total
        if not PlatformLedgerEntry.objects.filter(reference=f"ORDER-SETTLE-{order.id}").exists(): PlatformLedgerEntry.objects.create(order=order,entry_type="order_settlement",amount=platform_amount,currency=order.currency,reference=f"ORDER-SETTLE-{order.id}",metadata={"office_fee":(order.metadata or {}).get("office_fee","0"),"commission_and_adjustments":"platform remainder after vendor payouts","refunded":"%s"%hold.refunded_amount})
        hold.released_amount+=remaining; hold.status=WalletHold.Status.RELEASED if hold.refunded_amount==0 else WalletHold.Status.PARTIAL; hold.save(update_fields=["released_amount","status","updated_at"])
        order.metadata={**(order.metadata or {}),"admin_released":True,"released_at":timezone.now().isoformat()}; order.payment_status="paid"; order.save(update_fields=["metadata","payment_status","updated_at"])
        return Response({"success":True,"status":"released","released_amount":str(hold.released_amount),"vendor_payouts":str(payout_total),"platform_amount":str(platform_amount)})

    @action(detail=True,methods=["post"])
    @transaction.atomic
    def reject_item(self,request,pk=None):
        order=self.get_queryset().select_for_update().get(pk=pk)
        if request.user.role!="vendor": raise PermissionDenied("رفض القطعة متاح للتاجر فقط")
        vendor_order=order.vendor_orders.filter(vendor__owner=request.user).select_for_update().first()
        if not vendor_order: raise PermissionDenied("لا تملك هذا الطلب")
        item=order.items.filter(pk=request.data.get("order_item_id"),vendor=vendor_order.vendor).first()
        if not item: raise ValidationError({"order_item_id":"قطعة الطلب غير موجودة."})
        reason=str(request.data.get("reason","")).strip()
        if not reason: raise ValidationError({"reason":"سبب الرفض مطلوب."})
        decision,_=OrderItemDecision.objects.select_for_update().get_or_create(order_item=item)
        if decision.status==OrderItemDecision.Status.REJECTED: raise ValidationError({"order_item":"تم رفض القطعة مسبقًا."})
        decision.status=OrderItemDecision.Status.REJECTED; decision.reason=reason; decision.decided_by=request.user; decision.save(update_fields=["status","reason","decided_by","updated_at"]); hold=WalletHold.objects.select_for_update().filter(order=order).first()
        if not hold: raise ValidationError({"order":"لا يوجد مبلغ معلق لهذا الطلب."})
        refund=min(item.vendor_total,max(Decimal("0.00"),hold.amount-hold.refunded_amount)); wallet=Wallet.objects.select_for_update().get(user=order.customer); wallet.balance+=refund; wallet.save(update_fields=["balance","updated_at"]); WalletTransaction.objects.create(wallet=wallet,transaction_type=WalletTransaction.Types.REFUND,amount=refund,balance_after=wallet.balance,reference=f"REFUND-ITEM-{item.id}",note=f"استرداد قطعة مرفوضة من {order.order_number}",metadata={"order_item_id":item.id,"reason":reason}); hold.refunded_amount+=refund; hold.status=WalletHold.Status.REFUNDED if hold.refunded_amount>=hold.amount else WalletHold.Status.PARTIAL; hold.save(update_fields=["refunded_amount","status","updated_at"]); return Response({"success":True,"order_item_id":item.id,"status":"rejected","refund":str(refund),"reason":reason})
