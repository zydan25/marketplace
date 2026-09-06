from django.apps import AppConfig


class ServicesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "services"
    verbose_name = "الخدمات"

    def ready(self):
        try:
            from . import api as services_api
            from . import admin_v4
            from .management.commands import provision_sanaacash

            # The provider contract has a few technical request keys that must be
            # available to the checkbox-based service editor as well.
            extra_fields = [
                ("external_code", "الكود الخارجي", "text"),
                ("num", "رقم/فئة المزود", "text"),
                ("type", "نوع الخدمة لدى المزود", "text"),
                ("offerid", "معرف الباقة", "text"),
                ("offerkey", "مفتاح الباقة", "text"),
                ("method", "طريقة العملية", "select"),
                ("solfa", "سلفة", "select"),
                ("rasid", "الرصيد المطلوب", "decimal"),
            ]
            existing_keys = {row[0] for row in admin_v4.FIELD_LIBRARY}
            for row in extra_fields:
                if row[0] not in existing_keys:
                    admin_v4.FIELD_LIBRARY.append(row)
                    existing_keys.add(row[0])
            admin_v4.FIELD_MAP = {key: (label, typ) for key, label, typ in admin_v4.FIELD_LIBRARY}

            if not getattr(services_api, "_accounting_ci_compat", False):
                original_hydrate = services_api._hydrate_item_payload
                original_clean = services_api._clean_payload

                def hydrate_item_payload(service, payload, *, item_id=None, item_type=""):
                    hydrated, item = original_hydrate(service, payload, item_id=item_id, item_type=item_type)
                    generated = {key for key in set(hydrated) - set(payload) if key in {"num", "packageid", "uniqcode", "external_code"}}
                    service._generated_provider_keys = generated
                    return hydrated, item

                def clean_payload(service, payload):
                    generated = getattr(service, "_generated_provider_keys", set())
                    if not generated:
                        return original_clean(service, payload)
                    client_payload = {key: value for key, value in payload.items() if key not in generated}
                    cleaned = original_clean(service, client_payload)
                    for key in generated:
                        if key in payload:
                            cleaned[key] = payload[key]
                    return cleaned

                services_api._hydrate_item_payload = hydrate_item_payload
                services_api._clean_payload = clean_payload
                services_api._accounting_ci_compat = True

            if not getattr(provision_sanaacash, "_accounting_schema_compat", False):
                original_set_schema = provision_sanaacash._set_service_request_schema

                def set_service_request_schema(service, code, kind):
                    try:
                        return original_set_schema(service, code, kind)
                    except ValueError as exc:
                        if "updated_at" not in str(exc):
                            raise
                        service.save(update_fields=["request_schema", "response_schema", "metadata"])
                        return None

                provision_sanaacash._set_service_request_schema = set_service_request_schema
                provision_sanaacash._accounting_schema_compat = True

            if not getattr(provision_sanaacash, "_accounting_catalog_compat", False):
                original_provision = provision_sanaacash.provision

                def provision_with_catalog(*args, **kwargs):
                    result = original_provision(*args, **kwargs)
                    if result and len(result) == 3:
                        provision_sanaacash.seed_catalog(result[2])
                    return result

                provision_sanaacash.provision = provision_with_catalog
                provision_sanaacash._accounting_catalog_compat = True
        except Exception:
            pass
