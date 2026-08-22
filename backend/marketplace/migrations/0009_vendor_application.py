from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("marketplace", "0008_inventory_reservations_indexes"),
    ]

    operations = [
        migrations.CreateModel(
            name="VendorApplication",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("store_name", models.CharField(max_length=180)),
                ("description", models.TextField(blank=True)),
                ("phone", models.CharField(max_length=32)),
                ("address", models.CharField(blank=True, max_length=255)),
                ("documents", models.JSONField(blank=True, default=dict)),
                ("status", models.CharField(choices=[("pending", "قيد المراجعة"), ("approved", "مقبول"), ("rejected", "مرفوض")], default="pending", max_length=20)),
                ("review_note", models.TextField(blank=True)),
                ("reviewed_at", models.DateTimeField(blank=True, null=True)),
                ("applicant", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="vendor_application", to=settings.AUTH_USER_MODEL)),
                ("reviewed_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="vendor_applications_reviewed", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-created_at"]},
        ),
    ]
