from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("marketplace", "0018_complete_domain_separation"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.AlterModelOptions(
                    name="auditlog",
                    options={
                        "verbose_name": "سجل تدقيق",
                        "verbose_name_plural": "سجلات التدقيق",
                    },
                ),
                migrations.AlterModelTable(
                    name="auditlog",
                    table="marketplace_auditlog",
                ),
            ],
        )
    ]
