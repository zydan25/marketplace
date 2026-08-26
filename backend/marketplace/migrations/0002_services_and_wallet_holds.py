from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
from decimal import Decimal


def forwards(apps, schema_editor):
    Service = apps.get_model("marketplace", "Service")
    for service in Service.objects.all():
        if not service.slug:
            base = service.name.replace(" ", "-") or "service"
            service.slug = f"{base}-{service.pk}"
            service.save(update_fields=["slug"])


class Migration(migrations.Migration):
    dependencies = [("marketplace", "0001_initial")]
    operations = [
        migrations.CreateModel(
            name="WalletHold",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("amount", models.DecimalField(decimal_places=2, max_digits=14)),
                ("released_amount", models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=14)),
                ("refunded_amount", models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=14)),
                ("status", models.CharField(choices=[("held", "معلق"), ("released", "مطلق"), ("refunded", "مسترد"), ("partial", "مسترد جزئيًا"), ("cancelled", "ملغي")], default="held", max_length=20)),
                ("note", models.CharField(blank=True, max_length=255)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("order", models.OneToOneField(on_delete=django.db.models.deletion.PROTECT, related_name="wallet_hold", to="marketplace.order")),
                ("wallet", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="holds", to="marketplace.wallet")),
            ],
        ),
        migrations.CreateModel(
            name="ServiceCategory",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("name", models.CharField(max_length=160)),
                ("image", models.ImageField(blank=True, null=True, upload_to="services/categories/")),
                ("description", models.TextField(blank=True)),
                ("sort_order", models.PositiveIntegerField(default=0)),
                ("is_active", models.BooleanField(default=True)),
                ("parent", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="children", to="marketplace.servicecategory")),
            ],
            options={"ordering": ["sort_order", "name", "id"], "constraints": [models.UniqueConstraint(fields=("parent", "name"), name="uniq_service_category_name_per_parent")]},
        ),
        migrations.CreateModel(
            name="Service",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("name", models.CharField(max_length=220)),
                ("slug", models.SlugField(blank=True, max_length=250, unique=True)),
                ("image", models.ImageField(blank=True, null=True, upload_to="services/")),
                ("banner", models.ImageField(blank=True, null=True, upload_to="services/banners/")),
                ("description", models.TextField(blank=True)),
                ("price", models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=14)),
                ("currency", models.CharField(default="YER", max_length=6)),
                ("is_active", models.BooleanField(default=True)),
                ("is_featured", models.BooleanField(default=False)),
                ("sort_order", models.PositiveIntegerField(default=0)),
                ("config", models.JSONField(blank=True, default=dict)),
                ("category", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="services", to="marketplace.servicecategory")),
            ],
            options={"ordering": ["sort_order", "name", "id"]},
        ),
        migrations.CreateModel(
            name="ServiceField",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("key", models.SlugField(max_length=100)),
                ("label", models.CharField(max_length=180)),
                ("field_type", models.CharField(choices=[("text", "نص"), ("textarea", "وصف"), ("number", "رقم"), ("phone", "هاتف"), ("date", "تاريخ"), ("select", "اختيار"), ("multiselect", "اختيار متعدد"), ("image", "رفع صورة"), ("file", "رفع ملف"), ("checkbox", "مربع اختيار")], default="text", max_length=30)),
                ("placeholder", models.CharField(blank=True, max_length=220)),
                ("help_text", models.CharField(blank=True, max_length=300)),
                ("is_required", models.BooleanField(default=False)),
                ("options", models.JSONField(blank=True, default=list)),
                ("sort_order", models.PositiveIntegerField(default=0)),
                ("service", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="fields", to="marketplace.service")),
            ],
            options={"ordering": ["sort_order", "id"], "constraints": [models.UniqueConstraint(fields=("service", "key"), name="uniq_service_field_key")]},
        ),
        migrations.CreateModel(
            name="ServiceSubmission",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("amount", models.DecimalField(decimal_places=2, max_digits=14)),
                ("currency", models.CharField(default="YER", max_length=6)),
                ("data", models.JSONField(blank=True, default=dict)),
                ("status", models.CharField(choices=[("pending", "قيد التنفيذ"), ("processing", "قيد المعالجة"), ("completed", "مكتمل"), ("rejected", "مرفوض"), ("refunded", "مسترد")], default="pending", max_length=20)),
                ("notes", models.TextField(blank=True)),
                ("reference", models.CharField(max_length=80, unique=True)),
                ("customer", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="service_submissions", to=settings.AUTH_USER_MODEL)),
                ("service", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="submissions", to="marketplace.service")),
            ],
        ),
        migrations.RunPython(forwards, migrations.RunPython.noop),
    ]
