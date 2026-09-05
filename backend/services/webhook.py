from django.db import transaction
from django.http import JsonResponse
from django.utils import timezone
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView

from .accounting_bridge import refund_service, settle_service
from .models import ServiceTransaction
from .security import decrypt_secret


class SanaacashWebhookAPIView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    @transaction.atomic
    def get(self, request):
        transid = str(request.query_params.get("transid") or "").strip()
        backpass = str(request.query_params.get("backpass") or "")
        action = str(request.query_params.get("action") or "").strip().lower()
        message = str(request.query_params.get("message") or "")[:1000]
        if not transid or not backpass or action not in {"done", "ban"}:
            return JsonResponse({"resultCode": "10", "message": "invalid webhook payload"}, status=400)
        tx = ServiceTransaction.objects.select_for_update().filter(provider_transaction_id=transid).order_by("-created_at").first()
        if not tx or not tx.webhook_secret_encrypted:
            return JsonResponse({"resultCode": "11", "message": "unknown transaction"}, status=404)
        try:
            expected = decrypt_secret(tx.webhook_secret_encrypted)
        except RuntimeError:
            return JsonResponse({"resultCode": "12", "message": "webhook secret unavailable"}, status=500)
        if not expected or not backpass or not secrets_equal(expected, backpass):
            return JsonResponse({"resultCode": "13", "message": "invalid backpass"}, status=403)
        if tx.status in {ServiceTransaction.Status.SUCCESS, ServiceTransaction.Status.REFUNDED}:
            return JsonResponse({"resultCode": "0", "message": "already finalized"})
        tx.webhook_received_at = timezone.now()
        tx.provider_response = {**(tx.provider_response or {}), "webhook": {"action": action, "message": message}}
        if action == "done":
            journal = settle_service(tx)
            tx.status = ServiceTransaction.Status.SUCCESS
            tx.settled_journal_id = journal.pk
            tx.completed_at = timezone.now()
        else:
            journal = refund_service(tx)
            tx.status = ServiceTransaction.Status.REFUNDED
            tx.refund_journal_id = journal.pk
            tx.error_code = "PROVIDER_BAN"
            tx.error_message = message
            tx.completed_at = timezone.now()
        tx.save(update_fields=["status", "settled_journal_id", "refund_journal_id", "error_code", "error_message", "provider_response", "webhook_received_at", "completed_at", "updated_at"])
        return JsonResponse({"resultCode": "0", "message": "updated"})


def secrets_equal(left, right):
    import hmac
    return hmac.compare_digest(left.encode("utf-8"), right.encode("utf-8"))
