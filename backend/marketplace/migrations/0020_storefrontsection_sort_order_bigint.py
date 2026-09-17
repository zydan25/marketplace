from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("marketplace", "0019_align_auditlog_state"),
    ]

    operations = [
        migrations.RunSQL(
            sql='ALTER TABLE "marketplace_storefrontsection" ALTER COLUMN "sort_order" TYPE bigint USING "sort_order"::bigint',
            reverse_sql='ALTER TABLE "marketplace_storefrontsection" ALTER COLUMN "sort_order" TYPE integer USING "sort_order"::integer',
        ),
    ]
