from django.apps import AppConfig


class ServicesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "services"
    verbose_name = "الخدمات"

    def ready(self):
        # Compatibility fixes for the current services contract.
        # Keep these narrow so existing catalog/service behavior remains unchanged.
        try:
            from . import api as services_api
            from .management.commands import provision_sanaacash

            original_hydrate = services_api._hydrate_item_payload

            def hydrate_item_payload(service, payload, *, item_id=None, item_type=""):
                hydrated, item = original_hydrate(
                    service,
                    payload,
                    item_id=item_id,
                    item_type=item_type,
                )
                declared = set(
                    service.fields.filter(is_active=True).values_list("key", flat=True)
                )
                # Provider-only values may be generated from a selected catalog item.
                # Keep them only when that field is explicitly part of the service contract.
                for key in {"num", "packageid", "uniqcode", "external_code"} - declared:
                    hydrated.pop(key, None)
                return hydrated, item

            services_api._hydrate_item_payload = hydrate_item_payload

            def set_service_request_schema(service, code, kind):
                service.request_schema = {
                    "type": "object",
                    "service_code": code,
                    "fields": [
                        f.key
                        for f in service.fields.filter(is_active=True).order_by("sort_order", "id")
                    ],
                    "async": True,
                }
                service.response_schema = {
                    "resultCode": "string",
                    "resultDesc": "string",
                    "provider_response": "object",
                }
                metadata = dict(service.metadata or {})
                metadata["no_wallet_charge"] = kind in {"query", "catalog"}
                service.metadata = metadata
                service.save(update_fields=["request_schema", "response_schema", "metadata"])

            provision_sanaacash._set_service_request_schema = set_service_request_schema
        except Exception:
            # Startup must not fail because an optional compatibility hook is unavailable.
            pass
