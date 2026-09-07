"""Process-safe, idempotent service catalog bootstrap."""

import logging
import os
import threading

logger = logging.getLogger(__name__)
_lock = threading.Lock()
_bootstrapped = False


def _sync_plan_types(services):
    from .models import TelecomPlan, TelecomPlanType

    payment_labels = {
        "prepaid": "دفع مسبق",
        "postpaid": "فوترة",
        "paid": "مدفوع",
    }
    for service in services.values():
        grouped = {}
        for plan in TelecomPlan.objects.filter(service=service, is_active=True):
            payment = (plan.payment_type or "other").strip().lower() or "other"
            line = (plan.line_type or "all").strip().lower() or "all"
            grouped.setdefault(f"{payment}:{line}"[:80], []).append(plan)
        for index, (code, plans) in enumerate(grouped.items()):
            first = plans[0]
            payment = (first.payment_type or "other").strip().lower() or "other"
            line_name = first.line_type.strip() if first.line_type else ""
            name = payment_labels.get(payment, "نوع آخر")
            if line_name:
                name = f"{name} - {line_name}"
            plan_type, _ = TelecomPlanType.objects.update_or_create(
                service=service,
                code=code,
                defaults={
                    "name": name,
                    "description": line_name,
                    "sort_order": index,
                    "is_active": True,
                },
            )
            plan_type.plans.set(plans)


def bootstrap_service_catalog():
    """Run once per Python process after the services tables exist."""
    global _bootstrapped
    if _bootstrapped or os.getenv("SERVICE_CATALOG_BOOTSTRAP", "1") == "0":
        return False
    with _lock:
        if _bootstrapped or os.getenv("SERVICE_CATALOG_BOOTSTRAP", "1") == "0":
            return False
        try:
            from django.db import connection
            if "services_service" not in connection.introspection.table_names():
                return False
            from .catalog_games import GAMES_AND_CARDS
            from .management.commands.provision_sanaacash import provision, seed_catalog

            _, _, services = provision()
            seed_catalog(services)
            for code in GAMES_AND_CARDS:
                service = services.get(code)
                if service is not None:
                    metadata = dict(service.metadata or {})
                    metadata.update({"api_catalog": True, "catalog_code": code, "source": "api 1 (59).pdf"})
                    service.metadata = metadata
                    service.save(update_fields=["metadata"])
            _sync_plan_types(services)
            _bootstrapped = True
            logger.info("Service catalog bootstrap completed: %s services", len(services))
            return True
        except Exception:
            logger.exception("Service catalog bootstrap failed; startup continues safely")
            return False
