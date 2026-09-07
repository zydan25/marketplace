from decimal import Decimal, InvalidOperation
from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from .wifi_accounting import settle_wifi_sale
from .wifi_cards import WifiCard
from .wifi_denominations import WifiDenomination
from .wifi_networks import WifiNetwork
from django.utils import timezone


def network_data(network):
    return {
        "id": str(network.id), "name": network.name, "location": network.location,
        "management_percent": str(network.management_percent), "description": network.description,
        "owner_name": network.owner.get_full_name() or network.owner.phone or network.owner.username,
        "owner_phone": getattr(network.owner, "phone", ""), "latitude": str(network.latitude) if network.latitude is not None else None,
        "longitude": str(network.longitude) if network.longitude is not None else None,
        "denominations": [
            {
                "id": str(d.id), "name": d.name, "number": d.denomination_number,
                "face_value": str(d.face_value), "sale_price": str(d.sale_price),
                "available_cards": d.cards.filter(status=WifiCard.Status.AVAILABLE).count(),
            }
            for d in network.denominations.filter(is_active=True).order_by("face_value", "id")
        ],
    }


class WifiNetworksAPIView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        networks = WifiNetwork.objects.filter(is_active=True).select_related("owner").prefetch_related("denominations__cards")
        return Response({"version": "1", "networks": [network_data(n) for n in networks]})


class WifiPurchaseAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        denomination = get_object_or_404(WifiDenomination.objects.select_related("network__owner"), pk=request.data.get("denomination_id"), is_active=True, network__is_active=True)
        card = WifiCard.objects.select_for_update().filter(denomination=denomination, status=WifiCard.Status.AVAILABLE).order_by("id").first()
        if not card:
            return Response({"detail": "لا يوجد كرت متاح لهذه الفئة حالياً."}, status=409)
        try:
            expected = Decimal(str(request.data.get("amount", denomination.sale_price))).quantize(Decimal("0.01"))
        except (InvalidOperation, TypeError, ValueError):
            return Response({"detail": "المبلغ غير صالح."}, status=400)
        price = Decimal(denomination.sale_price).quantize(Decimal("0.01"))
        if expected != price:
            return Response({"detail": "السعر تغير؛ أعد تحميل الفئة قبل الشراء."}, status=409)
        entry, owner_amount, fee = settle_wifi_sale(card, request.user, created_by=request.user)
        card.status = WifiCard.Status.SOLD
        card.sold_to = request.user
        card.sold_at = timezone.now()
        card.sale_journal_id = entry.pk
        card.save(update_fields=["status", "sold_to", "sold_at", "sale_journal_id", "updated_at"])
        return Response({
            "id": str(card.id), "card_number": card.card_number, "pin": card.pin,
            "network_name": denomination.network.name, "denomination": denomination.name,
            "face_value": str(denomination.face_value), "price": str(price), "owner_amount": str(owner_amount),
            "management_fee": str(fee), "journal": entry.number, "sold_at": card.sold_at.isoformat(),
        }, status=201)


class WifiMyCardsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        cards = WifiCard.objects.filter(sold_to=request.user, status=WifiCard.Status.SOLD).select_related("denomination__network").order_by("-sold_at", "-id")
        return Response({"cards": [
            {"id": str(c.id), "network_name": c.denomination.network.name, "denomination_title": c.denomination.name,
             "price": str(c.denomination.sale_price), "pin_code": c.pin, "serial_number": c.card_number,
             "purchase_date": c.sold_at.isoformat() if c.sold_at else "", "duration": "", "data_quota": "",
             "owner_phone": getattr(c.denomination.network.owner, "phone", "")}
            for c in cards
        ]})
