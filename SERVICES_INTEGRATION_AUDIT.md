# Services Integration Audit

## Scope

Reviewed on branch `feat/api-legacy-integration-cleanup`:

- Django service catalog, provider abstraction, service request execution and admin templates.
- `flutter-katolin` customer app service flow and Retrofit boundary.
- Supplied Sanaacash API PDF.
- Supplied legacy MySQL backup and its service/catalog tables.
- Supplied legacy UI screenshots.

## Decisions

### Provider boundary

The customer app talks only to Django `/api/v2/services/*`. Sanaacash is an internal provider behind `ProviderConnection`, `ProviderLink` and `ServiceDistribution`.

### Service hierarchy

`MainServiceCategory -> ServiceCategory -> child category -> Service -> item`

A service may have zero items when it is direct/amount based. Package/denomination/game services expose selectable items.

### Yemen Mobile

Ordinary balance is amount based: customer supplies mobile + amount. Package activation/query are separate services. Provider package codes are server-side values.

### Games and cards

Game network services are presented to customers as child categories below the games category. A selected package is a `GameProduct`; provider `uniqcode` is resolved by the backend and is not customer-authoritative.

### Legacy data

Service/catalog tables from the legacy DB are imported into the current typed catalog models. Legacy-only rows that cannot be matched safely to the current provider contract remain reviewable and unlinked instead of being executed accidentally.

Customer accounts, financial journals and payment history are not duplicated into service catalog tables; those domains remain in their own Django models.

## Customer API

- `GET /api/v2/services/catalog/`
- `GET /api/v2/services/services/<id>/`
- `POST /api/v2/services/requests/`
- `GET /api/v2/services/requests/<uuid>/`

The request endpoint uses idempotency and backend-side validation/reservation.

## Import

After deploying the branch, run a dry run first:

`python manage.py import_legacy_services /path/to/database_backup.sql.zip --dry-run`

Then run without `--dry-run` after reviewing the counts.

## Provider setup

Create/configure one Django provider connection with the current Sanaacash URL and credentials. Keep the password encrypted. The customer application must not contain these credentials.

Then provision service links and distributions using the existing Sanaacash provisioning command.

## Validation checklist

1. `python manage.py check`
2. Run the importer with `--dry-run` against the supplied backup.
3. Run migrations/checks in the deployment database.
4. Login to the customer app and load `/services/catalog/`.
5. Verify direct Yemen Mobile balance shows only mobile + amount.
6. Verify package services show selectable package items and required fields only.
7. Verify Free Fire/PUBG etc. show package rows from `GameProduct`.
8. Submit a paid request with a unique `Idempotency-Key` and verify one transaction/reservation.
9. Verify pending provider results stay pending until status/webhook confirmation.
10. Verify no provider secret appears in customer API JSON, APK source or app logs.

## Important limitation

This review modified source files directly in GitHub, but the repository was not locally checked out in the execution environment, so a real Gradle build and Django runtime test against the deployment database were not performed here. Run the validation checklist after pulling the branch into the deployment environment.
