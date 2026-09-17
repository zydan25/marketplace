from django.db import migrations


def noop_migration(apps, schema_editor):
    # The real field transition is owned by storefront.0003 now that
    # StorefrontSection lives in the storefront app. Keeping this historical
    # migration as a no-op avoids PostgreSQL-only SQL breaking SQLite CI.
    return None


class Migration(migrations.Migration):
    dependencies = [
        ("marketplace", "0019_align_auditlog_state"),
    ]

    operations = [
        migrations.RunPython(noop_migration, reverse_code=migrations.RunPython.noop),
    ]
