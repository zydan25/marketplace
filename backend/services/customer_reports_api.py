from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .api import _transaction_data
from .executor import _new_status_task, process_task
from .models import ServiceTask, ServiceTransaction


FINAL_STATES = {
    ServiceTransaction.Status.SUCCESS,
    ServiceTransaction.Status.FAILED,
    ServiceTransaction.Status.REFUNDED,
}
PENDING_STATES = {
    ServiceTransaction.Status.ACCEPTED,
    ServiceTransaction.Status.QUEUED,
    ServiceTransaction.Status.PROCESSING,
    ServiceTransaction.Status.PENDING_PROVIDER,
    ServiceTransaction.Status.MANUAL_REVIEW,
}


class CustomerServiceReportsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        status_filter = str(request.query_params.get("status") or "").strip()
        qs = (
            ServiceTransaction.objects.filter(customer=request.user)
            .exclude(service__service_kind=ServiceTransaction.service.field.remote_field.model.ServiceKinds.QUERY)
            .select_related("service")
            .order_by("-created_at")
        )
        if status_filter:
            qs = qs.filter(status=status_filter)
        qs = qs[:100]
        return Response({
            "count": len(qs),
            "results": [_transaction_data(tx) for tx in qs],
        })


class CustomerServiceProviderCheckAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        tx = get_object_or_404(
            ServiceTransaction.objects.select_related("service", "provider_link"),
            pk=pk,
            customer=request.user,
        )

        if tx.status in FINAL_STATES:
            return Response(_transaction_data(tx), status=200)
        if tx.status not in PENDING_STATES:
            return Response(_transaction_data(tx), status=200)

        task = (
            ServiceTask.objects.filter(
                transaction=tx,
                kind=ServiceTask.Kinds.STATUS_CHECK,
                status__in=[ServiceTask.Statuses.QUEUED, ServiceTask.Statuses.RETRY],
            )
            .select_related("provider_link__provider")
            .order_by("available_at", "id")
            .first()
        )

        if task is None:
            link = tx.provider_link
            if link is None:
                task = (
                    ServiceTask.objects.filter(transaction=tx, provider_link__isnull=False)
                    .select_related("provider_link__provider")
                    .order_by("-id")
                    .first()
                )
                link = task.provider_link if task else None
            if link is None:
                return Response({
                    "detail": "لا توجد ربطية مزود مرتبطة بهذه العملية لفحص حالتها.",
                    **_transaction_data(tx),
                }, status=409)
            if not link.status_path_template:
                return Response({
                    "detail": "المزوّد لا يملك مسار فحص حالة لهذه العملية.",
                    **_transaction_data(tx),
                }, status=409)
            task = _new_status_task(tx, link, delay=0, max_attempts=1)

        process_task(task.pk)
        tx.refresh_from_db()
        return Response(_transaction_data(tx), status=200)
