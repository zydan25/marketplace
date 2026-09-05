from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from .accounting_bridge import refund_service, settle_service
from .models import ServiceDistribution, ServiceTask, ServiceTransaction
from .provider import ProviderClient


def _next_route(service, *, after_priority=None, exclude=None):
    qs = ServiceDistribution.objects.select_related("provider_link__provider").filter(service=service, is_active=True, provider_link__is_active=True, provider_link__provider__is_active=True).order_by("priority", "id")
    if after_priority is not None:
        qs = qs.filter(priority__gt=after_priority)
    if exclude:
        qs = qs.exclude(provider_link_id__in=exclude)
    return qs.first()


def _used_links(tx):
    return [int(x) for x in (tx.metadata or {}).get("used_provider_links", []) if str(x).isdigit()]


def _remember_link(tx, link_id):
    data = dict(tx.metadata or {})
    used = set(_used_links(tx))
    used.add(int(link_id))
    data["used_provider_links"] = sorted(used)
    tx.metadata = data


def _complete_success(tx):
    with transaction.atomic():
        tx = ServiceTransaction.objects.select_for_update().get(pk=tx.pk)
        if tx.status == ServiceTransaction.Status.SUCCESS:
            return tx
        journal = settle_service(tx)
        tx.status = ServiceTransaction.Status.SUCCESS
        tx.settled_journal_id = journal.pk
        tx.completed_at = timezone.now()
        tx.save(update_fields=["status", "settled_journal_id", "completed_at", "updated_at"])
        return tx


def _complete_failure(tx, *, code="", message="", refund=True):
    with transaction.atomic():
        tx = ServiceTransaction.objects.select_for_update().get(pk=tx.pk)
        if tx.status == ServiceTransaction.Status.REFUNDED:
            return tx
        journal = refund_service(tx) if refund else None
        tx.status = ServiceTransaction.Status.REFUNDED if refund else ServiceTransaction.Status.FAILED
        tx.refund_journal_id = journal.pk if journal else None
        tx.error_code = str(code or "")
        tx.error_message = str(message or "")
        tx.completed_at = timezone.now()
        tx.save(update_fields=["status", "refund_journal_id", "error_code", "error_message", "completed_at", "updated_at"])
        return tx


def _new_status_task(tx, provider_link):
    if not provider_link.status_path_template:
        return None
    return ServiceTask.objects.create(transaction=tx, kind=ServiceTask.Kinds.STATUS_CHECK, provider_link=provider_link, available_at=timezone.now() + timedelta(seconds=8), max_attempts=30, metadata={"poll_seconds": 8})


def process_task(task_id=None):
    now = timezone.now()
    with transaction.atomic():
        qs = ServiceTask.objects.select_for_update().select_related("transaction__service", "provider_link__provider")
        if task_id is not None:
            task = qs.get(pk=task_id)
            if task.status not in {ServiceTask.Statuses.QUEUED, ServiceTask.Statuses.RETRY}:
                return task
        else:
            task = qs.filter(status__in=[ServiceTask.Statuses.QUEUED, ServiceTask.Statuses.RETRY], available_at__lte=now).order_by("available_at", "id").first()
            if not task:
                return None
        task.status = ServiceTask.Statuses.RUNNING
        task.attempts += 1
        task.started_at = now
        task.save(update_fields=["status", "attempts", "started_at"])

    tx = ServiceTransaction.objects.select_related("service").get(pk=task.transaction_id)
    if tx.status in {ServiceTransaction.Status.SUCCESS, ServiceTransaction.Status.REFUNDED}:
        task.status = ServiceTask.Statuses.DONE
        task.finished_at = timezone.now()
        task.save(update_fields=["status", "finished_at"])
        return task

    link = task.provider_link
    if not link:
        dist = _next_route(tx.service, exclude=_used_links(tx))
        if not dist:
            _complete_failure(tx, code="NO_ROUTE", message="لا توجد ربطية فعالة لهذه الخدمة.")
            task.status = ServiceTask.Statuses.FAILED
            task.last_error = "NO_ROUTE"
            task.finished_at = timezone.now()
            task.save(update_fields=["status", "last_error", "finished_at"])
            return task
        link = dist.provider_link
        task.provider_link = link
        task.save(update_fields=["provider_link"])
    if link.pk not in _used_links(tx):
        _remember_link(tx, link.pk)
    tx.provider_link = link
    tx.provider_transaction_id = tx.provider_transaction_id or f"SVC-{str(tx.id).replace('-', '')[:24]}"
    if task.kind == ServiceTask.Kinds.SUBMIT:
        tx.status = ServiceTransaction.Status.PROCESSING
    tx.save(update_fields=["provider_link", "provider_transaction_id", "metadata", "status", "updated_at"])

    if task.kind == ServiceTask.Kinds.STATUS_CHECK and not link.status_path_template:
        _complete_failure(tx, code="NO_STATUS_ROUTE", message="الربطية أعادت Pending لكنها لا تحتوي مسارًا لفحص حالة العملية.")
        task.status = ServiceTask.Statuses.FAILED
        task.last_error = "NO_STATUS_ROUTE"
        task.finished_at = timezone.now()
        task.save(update_fields=["status", "last_error", "finished_at"])
        return task

    result = ProviderClient(link.provider).call(link, tx, status_check=task.kind == ServiceTask.Kinds.STATUS_CHECK)
    tx.provider_response = result.response

    if result.success:
        tx.save(update_fields=["provider_response", "updated_at"])
        _complete_success(tx)
        task.status = ServiceTask.Statuses.DONE
        task.finished_at = timezone.now()
        task.save(update_fields=["status", "finished_at"])
        return task

    if result.pending:
        tx.status = ServiceTransaction.Status.PENDING_PROVIDER
        tx.save(update_fields=["status", "provider_response", "updated_at"])
        task.status = ServiceTask.Statuses.DONE
        task.finished_at = timezone.now()
        task.save(update_fields=["status", "finished_at"])
        if task.kind == ServiceTask.Kinds.SUBMIT:
            if _new_status_task(tx, link) is None:
                task.last_error = "PENDING_WITHOUT_STATUS_ROUTE"
                task.save(update_fields=["last_error"])
        elif task.attempts < task.max_attempts:
            _new_status_task(tx, link)
        else:
            _complete_failure(tx, code=result.code, message=result.description)
        return task

    tx.error_code = result.code
    tx.error_message = result.description
    tx.save(update_fields=["provider_response", "error_code", "error_message", "updated_at"])

    if task.kind == ServiceTask.Kinds.SUBMIT:
        dist = _next_route(tx.service, after_priority=link.priority, exclude=_used_links(tx))
        if dist:
            task.status = ServiceTask.Statuses.QUEUED
            task.provider_link = dist.provider_link
            task.available_at = timezone.now()
            task.last_error = result.description
            task.save(update_fields=["status", "provider_link", "available_at", "last_error"])
            _remember_link(tx, dist.provider_link_id)
            tx.provider_link = dist.provider_link
            tx.provider_transaction_id = ""
            tx.status = ServiceTransaction.Status.QUEUED
            tx.save(update_fields=["provider_link", "provider_transaction_id", "metadata", "status", "updated_at"])
            return task

    if task.attempts < task.max_attempts:
        task.status = ServiceTask.Statuses.RETRY
        task.available_at = timezone.now() + timedelta(seconds=min(120, 10 * task.attempts))
        task.last_error = result.description
        task.save(update_fields=["status", "available_at", "last_error"])
        tx.status = ServiceTransaction.Status.PROCESSING
        tx.save(update_fields=["status", "updated_at"])
        return task

    _complete_failure(tx, code=result.code, message=result.description)
    task.status = ServiceTask.Statuses.FAILED
    task.last_error = result.description
    task.finished_at = timezone.now()
    task.save(update_fields=["status", "last_error", "finished_at"])
    return task
