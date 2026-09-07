"""Process-safe, idempotent catalog bootstrap used after Django starts.

The PDF is represented by the canonical Python catalog modules. Bootstrap only
creates/updates records; it never deletes legacy rows and never writes provider
credentials. Product prices that are not part of the PDF remain sourced from
the imported catalog/legacy backup.
"""

import logging
import os
import threading

logger = logging.getLogger(__name__)
_lock = threading.Lock()
_bootstrapped = False


def _sync_plan_types(services):
    from .models import TelecomPlan, TelecomPlanType

    payment_labels = {
        "prepaid": ("prepaid", "دفع مسبق"),
        "postpaid": ("postpaid", "فوترة"),
        "paid": ("paid", "مدفوع"),
    }
    for service in services.values():
        plans = TelecomPlan.objects.filter(service=service, is_active=True)
        groups = {}
        for plan in plans:
            payment = (plan.payment_type or "other").strip().lower() or "other"
            line = (plan.line_type or "all").strip().lower() or "all"
            code = f"{payment}:{line}"[:80]
            base_name = payment_labels.get(payment, (payment, payment)).__getitem__(1)
            name = base_name if line in {"all", ""} else f"{base_name} - {plan.line_type}"
            groups.setdefault(code, []).append(plan)
        for index, (code, grouped_plans) in enumerate(groups.items()):
            plan_type, _ = TelecomPlanType.objects.update_or_create(
                service=service,
                code=code,
                defaults={
                    "name": name if (name := (grouped_plans[0].payment_type or "نوع آخر")) else "نوع آخر",
                    "description": grouped_plans[0].line_type or "",
                    "sort_order": index,
                    "is_active": True,
                },
            )
            if plan_type.name == grouped_plans[0].payment_type and grouped_plans[0].payment_type in payment_labels:
                plan_type.name = payment_labels[grouped_plans[0].payment_type][1]
                plan_type.save(update_fields=["name"])
            plan_type.plans.set(grouped_plans)


def bootstrap_service_catalog():
    """Run once per Python process, and only after the service tables exist."""
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
        except Exception:  # bootstrap must never prevent Django from starting
            logger.exception("Service catalog bootstrap failed; startup continues safely")
            return False
