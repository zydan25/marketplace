#!/usr/bin/env python3
"""Import the current Django SQLite database into the configured PostgreSQL database.

This is a one-time migration helper. It refuses to mix an existing application
 dataset into the target. After Django migrations create the target schema, any
migration-created rows in current application tables are cleared and replaced
with the data exported from the SQLite source.

Required environment:
  DATABASE_URL=postgresql://user:password@host:5432/database

Optional:
  SOURCE_SQLITE_DB=/absolute/path/to/db.sqlite3
  DB_SSLMODE=require|prefer|disable

Run from backend/:
  python scripts/import_sqlite_to_postgres.py
"""

from __future__ import annotations

import json
import os
import sqlite3
import sys
import tempfile
from pathlib import Path
from urllib.parse import urlparse

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
os.environ.setdefault("DISABLE_EMBEDDED_WORKER", "1")

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
SOURCE_SQLITE_DB = Path(
    os.getenv("SOURCE_SQLITE_DB", str(BASE_DIR / "db.sqlite3"))
).expanduser().resolve()

EXCLUDED_TABLES = {
    "django_migrations",
    "django_content_type",
    "auth_permission",
    "django_session",
    "django_admin_log",
}
EXCLUDED_LABELS = {
    "contenttypes",
    "auth.permission",
    "sessions",
    "admin.logentry",
}


def fail(message: str) -> "NoReturn":
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(1)


def sqlite_tables_and_counts(path: Path) -> dict[str, int]:
    db = sqlite3.connect(path)
    try:
        rows = db.execute(
            "SELECT name FROM sqlite_master "
            "WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
        ).fetchall()
        result: dict[str, int] = {}
        for (table_name,) in rows:
            result[table_name] = int(
                db.execute(f'SELECT COUNT(*) FROM "{table_name}"').fetchone()[0]
            )
        return result
    finally:
        db.close()


def postgres_table_counts(connection, table_names: set[str] | None = None) -> dict[str, int]:
    tables = connection.introspection.table_names()
    if table_names is not None:
        tables = [table for table in tables if table in table_names]
    counts: dict[str, int] = {}
    with connection.cursor() as cursor:
        for table_name in tables:
            quoted = connection.ops.quote_name(table_name)
            cursor.execute(f"SELECT COUNT(*) FROM {quoted}")
            counts[table_name] = int(cursor.fetchone()[0])
    return counts


def managed_table_names(apps) -> set[str]:
    return {
        model._meta.db_table
        for model in apps.get_models(include_auto_created=True)
        if model._meta.managed
        and not model._meta.proxy
        and model._meta.db_table not in EXCLUDED_TABLES
    }


def truncate_application_tables(connection, table_names: set[str]) -> None:
    """Clear only current Django-managed application tables before loaddata."""
    if not table_names:
        return
    existing = set(connection.introspection.table_names())
    tables = sorted(table_names & existing)
    if not tables:
        return
    with connection.cursor() as cursor:
        quoted = ", ".join(connection.ops.quote_name(table) for table in tables)
        cursor.execute(f"TRUNCATE TABLE {quoted} RESTART IDENTITY CASCADE")


def build_content_type_compatibility_map(source_connection, apps) -> dict[tuple[str, str], tuple[str, str]]:
    """Map legacy ContentType labels to current models that keep the same DB table.

    Several marketplace models were moved into domain apps while deliberately
    retaining their historical marketplace_* database tables. Existing users'
    permissions therefore still reference natural keys such as
    (marketplace, address), while the current ContentType is (promotions, address).
    """
    current_by_table: dict[str, tuple[str, str]] = {}
    for model in apps.get_models():
        if model._meta.managed and not model._meta.proxy:
            current_by_table.setdefault(
                model._meta.db_table,
                (model._meta.app_label, model._meta.model_name),
            )

    with source_connection.cursor() as cursor:
        cursor.execute("SELECT app_label, model FROM django_content_type")
        source_content_types = cursor.fetchall()

    compatibility: dict[tuple[str, str], tuple[str, str]] = {}
    for app_label, model_name in source_content_types:
        legacy_table = f"{app_label}_{model_name}".lower()
        current_key = current_by_table.get(legacy_table)
        source_key = (app_label, model_name)
        if current_key and current_key != source_key:
            compatibility[source_key] = current_key
    return compatibility


def rewrite_permission_natural_keys(
    fixture_path: Path,
    compatibility: dict[tuple[str, str], tuple[str, str]],
    target_connection,
) -> None:
    """Rewrite legacy User.user_permissions natural keys to current ContentTypes."""
    if not compatibility:
        return

    from django.contrib.auth.models import Permission

    with fixture_path.open("r", encoding="utf-8") as fixture_file:
        payload = json.load(fixture_file)

    changed = 0
    permission_keys: set[tuple[str, str, str]] = set()
    unmapped_legacy: set[tuple[str, str, str]] = set()

    for obj in payload:
        fields = obj.get("fields", {})
        permissions = fields.get("user_permissions")
        if not isinstance(permissions, list):
            continue

        rewritten_permissions = []
        for natural_key in permissions:
            if isinstance(natural_key, list) and len(natural_key) == 3:
                codename, app_label, model_name = natural_key
                source_ct = (app_label, model_name)
                target_ct = compatibility.get(source_ct)
                if target_ct:
                    natural_key = [codename, target_ct[0], target_ct[1]]
                    changed += 1
                    permission_keys.add(tuple(natural_key))
                else:
                    permission_keys.add(tuple(natural_key))
                    if app_label == "marketplace":
                        unmapped_legacy.add((codename, app_label, model_name))
            rewritten_permissions.append(natural_key)
        fields["user_permissions"] = rewritten_permissions

    missing_permissions: list[tuple[str, str, str]] = []
    for permission_key in sorted(permission_keys):
        codename, app_label, model_name = permission_key
        try:
            Permission.objects.using(target_connection.alias).get_by_natural_key(
                codename, app_label, model_name
            )
        except Permission.DoesNotExist:
            missing_permissions.append(permission_key)

    if unmapped_legacy:
        details = ", ".join(
            f"{codename}/{app_label}.{model_name}"
            for codename, app_label, model_name in sorted(unmapped_legacy)
        )
        fail(
            "SQLite user permissions reference legacy marketplace ContentTypes that "
            f"could not be mapped to current models: {details}"
        )

    if missing_permissions:
        details = ", ".join(
            f"{codename}/{app_label}.{model_name}"
            for codename, app_label, model_name in missing_permissions[:30]
        )
        fail(
            "Target PostgreSQL is missing permissions required by SQLite users: "
            f"{details}"
        )

    if changed:
        with fixture_path.open("w", encoding="utf-8") as fixture_file:
            json.dump(payload, fixture_file, ensure_ascii=False, indent=2)
        print(f"Rewrote {changed} legacy user-permission ContentType reference(s).")


def main() -> int:
    if not SOURCE_SQLITE_DB.is_file():
        fail(f"SQLite source database not found: {SOURCE_SQLITE_DB}")

    database_url = os.getenv("DATABASE_URL", "").strip()
    if not database_url:
        fail("DATABASE_URL is required for the PostgreSQL target.")
    if urlparse(database_url).scheme not in {"postgres", "postgresql"}:
        fail("DATABASE_URL must use postgres:// or postgresql://")

    source_counts_all = sqlite_tables_and_counts(SOURCE_SQLITE_DB)

    import django

    django.setup()

    from django.apps import apps
    from django.core.management import call_command
    from django.core.management.color import no_style
    from django.db import connections, transaction

    current_managed_tables = managed_table_names(apps)
    source_data_tables = {
        table: count
        for table, count in source_counts_all.items()
        if table in current_managed_tables
    }
    ignored_legacy_tables = sorted(
        table
        for table in source_counts_all
        if table not in current_managed_tables and table not in EXCLUDED_TABLES
    )
    source_total = sum(source_counts_all.values())
    source_data_total = sum(source_data_tables.values())

    print(f"SQLite source: {SOURCE_SQLITE_DB}")
    print(f"SQLite tables: {len(source_counts_all)}")
    print(f"SQLite total rows: {source_total}")
    print(f"Current Django-managed tables eligible for import: {len(source_data_tables)}")
    print(f"Rows eligible for import: {source_data_total}")
    if ignored_legacy_tables:
        print(
            "Legacy/unmanaged SQLite tables not imported:",
            ", ".join(ignored_legacy_tables),
        )

    source_db_settings = connections.databases["default"].copy()
    source_db_settings.update(
        {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": str(SOURCE_SQLITE_DB),
            "USER": "",
            "PASSWORD": "",
            "HOST": "",
            "PORT": "",
            "OPTIONS": {},
            "CONN_MAX_AGE": 0,
            "CONN_HEALTH_CHECKS": False,
        }
    )
    connections.databases["source"] = source_db_settings

    source_connection = connections["source"]
    target_connection = connections["default"]
    source_connection.ensure_connection()
    target_connection.ensure_connection()

    target_counts_before_migrate = postgres_table_counts(
        target_connection, current_managed_tables
    )
    nonempty_before_migrate = {
        table: count
        for table, count in target_counts_before_migrate.items()
        if count > 0
    }
    if nonempty_before_migrate:
        preview = ", ".join(
            f"{table}={count}" for table, count in sorted(nonempty_before_migrate.items())[:20]
        )
        fail(
            "PostgreSQL target already contains application data; refusing to mix "
            f"datasets. Existing rows: {preview}. Use a fresh database."
        )

    print("Applying Django migrations to the PostgreSQL target...")
    call_command("migrate", database="default", interactive=False, verbosity=1)

    # Migrate runs first so that the target contains the current ContentTypes and
    # permissions. This lets us rewrite legacy natural keys safely before loaddata.
    compatibility = build_content_type_compatibility_map(source_connection, apps)
    if compatibility:
        print("Legacy ContentType mappings detected:")
        for source_key, target_key in sorted(compatibility.items()):
            print(f"  {source_key[0]}.{source_key[1]} -> {target_key[0]}.{target_key[1]}")

    print("Preparing application tables for exact SQLite data import...")
    with transaction.atomic(using="default"):
        truncate_application_tables(target_connection, current_managed_tables)

    print("Exporting Django data from SQLite...")
    fixture_path = Path(
        tempfile.mkstemp(prefix="marketplace-migration-", suffix=".json")[1]
    )

    try:
        with fixture_path.open("w", encoding="utf-8") as fixture_file:
            command_kwargs = {
                "database": "source",
                "use_natural_foreign_keys": True,
                "use_natural_primary_keys": False,
                "indent": 2,
                "stdout": fixture_file,
            }
            for label in EXCLUDED_LABELS:
                command_kwargs.setdefault("exclude", []).append(label)
            call_command("dumpdata", **command_kwargs)

        rewrite_permission_natural_keys(fixture_path, compatibility, target_connection)

        print("Importing fixture into PostgreSQL...")
        with transaction.atomic(using="default"):
            call_command(
                "loaddata",
                str(fixture_path),
                database="default",
                verbosity=1,
            )

            print("Resetting PostgreSQL sequences...")
            models = [
                model
                for model in apps.get_models(include_auto_created=True)
                if model._meta.managed and not model._meta.proxy
            ]
            reset_sql = target_connection.ops.sequence_reset_sql(no_style(), models)
            with target_connection.cursor() as cursor:
                for statement in reset_sql:
                    cursor.execute(statement)

            print("Verifying row counts table-by-table before commit...")
            target_counts_after = postgres_table_counts(
                target_connection, current_managed_tables
            )
            mismatches: list[tuple[str, int, int | None]] = []
            for table, source_count in sorted(source_data_tables.items()):
                target_count = target_counts_after.get(table)
                if target_count != source_count:
                    mismatches.append((table, source_count, target_count))

            if mismatches:
                print("\nCOUNT MISMATCHES:")
                for table, source_count, target_count in mismatches:
                    print(
                        f"  {table}: SQLite={source_count}, PostgreSQL={target_count}"
                    )
                fail(
                    f"Verification failed: {len(mismatches)} table(s) do not match. "
                    "The PostgreSQL import transaction has been rolled back."
                )

        print("\nMigration verification successful.")
        print(f"Matched Django-managed tables: {len(source_data_tables)}")
        print(f"Matched application rows: {source_data_total}")
        print(
            "Excluded regenerated/ephemeral tables:",
            ", ".join(sorted(EXCLUDED_TABLES)),
        )
        return 0
    finally:
        try:
            fixture_path.unlink(missing_ok=True)
        except OSError:
            pass
        source_connection.close()
        target_connection.close()


if __name__ == "__main__":
    main()
