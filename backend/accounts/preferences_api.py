from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.exceptions import ValidationError

from marketplace.models_extra import CurrencyRate
from .models import UserPreference


class PreferencesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        preference, _ = UserPreference.objects.get_or_create(user=request.user)
        rates = list(
            CurrencyRate.objects.filter(is_active=True).values(
                "base_currency", "target_currency", "rate"
            )
        )
        return Response(
            {
                "currency": preference.currency,
                "notifications_enabled": preference.notifications_enabled,
                "rates": rates,
            }
        )

    def patch(self, request):
        preference, _ = UserPreference.objects.get_or_create(user=request.user)
        currency = str(request.data.get("currency", preference.currency)).upper()
        if currency not in {"YER", "SAR", "USD"}:
            raise ValidationError({"currency": "العملة غير مدعومة"})
        preference.currency = currency
        if "notifications_enabled" in request.data:
            value = request.data.get("notifications_enabled")
            preference.notifications_enabled = (
                value
                if isinstance(value, bool)
                else str(value).lower() in {"1", "true", "yes"}
            )
        preference.save(update_fields=["currency", "notifications_enabled", "updated_at"])
        return Response(
            {
                "currency": preference.currency,
                "notifications_enabled": preference.notifications_enabled,
            }
        )
