from __future__ import annotations

import json
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from .models import ProviderLink, ServiceTask, ServiceTransaction

# ...

def process_task(task_id=None):
    now = timezone.now()
    if task_id is None:
        with transaction.atomic():
            _recover_stale_tasks(now)
    with transaction.atomic():
        # provider_link is nullable. Lock only ServiceTask rows so PostgreSQL
        # does not attempt FOR UPDATE on the nullable outer-joined relation.
        qs = ServiceTask.objects.select_for_update(of=("self",)).select_related(
            "transaction__service", "provider_link__provider"
        )
        if task_id is not None:
            task = qs.get(pk=task_id)
            if task.status not in {ServiceTask.Statuses.QUEUED, ServiceTask.Statuses.RETRY}:
                return task
        else:
            task = qs.filter(
                status__in=[ServiceTask.Statuses.QUEUED, ServiceTask.Statuses.RETRY],
                available_at__lte=now,
            ).order_by("available_at", "id").first()
            if not task:
                return None
        task.status = ServiceTask.Statuses.RUNNING
        task.attempts += 1
        task.started_at = now
        task.save(update_fields=["status", "attempts", "started_at"])

    tx = ServiceTransaction.objects.select_related("service").get(pk=task.transaction_id)
    if tx.status in {ServiceTransaction.Status.SUCCESS, ServiceTransaction.Status.REFUNDED, ServiceTransaction.Status.FAILED, ServiceTransaction.Status.MANUAL_REVIEW}:
        task.status = ServiceTask.Statuses.DONE
        task.finished_at = timezone.now()
        task.save(update_fields=["status", "finished_at"])
        return task
