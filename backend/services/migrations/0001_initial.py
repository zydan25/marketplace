from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.core.validators
import uuid


def seed_main_categories(apps, schema_editor):
    MainServiceCategory = apps.get_model("services", "MainServiceCategory")
    for name, slug, icon, order in [
        ("التسديدات", "payments", "receipt", 10),
        ("الألعاب", "games", "gamepad", 20),
        ("البرامج", "software", "apps", 30),
    ]:
        MainServiceCategory.objects.get_or_create(slug=slug, defaults={"name": name, "icon": icon, "sort_order": order})


class Migration(migrations.Migration):
    initial = True
    dependencies = [("marketplace", "0001_initial")]
    operations = [
        migrations.CreateModel(name="MainServiceCategory", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("name", models.CharField(max_length=120, unique=True)),
            ("slug", models.SlugField(max_length=120, unique=True)),
            ("description", models.TextField(blank=True)),
            ("icon", models.CharField(blank=True, max_length=80)),
            ("sort_order", models.PositiveIntegerField(default=0)),
            ("is_active", models.BooleanField(default=True)),
        ], options={"ordering": ["sort_order", "id"], "verbose_name": "الفئة الرئيسية", "verbose_name_plural": "الفئات الرئيسية"}),
        migrations.CreateModel(name="ServiceCategory", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("name", models.CharField(max_length=160)),
            ("slug", models.SlugField(max_length=160)),
            ("description", models.TextField(blank=True)),
            ("icon", models.CharField(blank=True, max_length=80)),
            ("sort_order", models.PositiveIntegerField(default=0)),
            ("is_active", models.BooleanField(default=True)),
            ("main_category", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="categories", to="services.mainservicecategory")),
            ("parent", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="children", to="services.servicecategory")),
        ], options={"ordering": ["sort_order", "id"], "verbose_name": "فئة الخدمة", "verbose_name_plural": "فئات الخدمات"}),
        migrations.CreateModel(name="ProviderConnection", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("name", models.CharField(max_length=160, unique=True)), ("code", models.SlugField(max_length=100, unique=True)),
            ("connection_type", models.CharField(choices=[("sanaacash", "يمن روبوت / صنعاء كاش"), ("http_json", "HTTP JSON"), ("manual", "تشغيل يدوي")], default="sanaacash", max_length=20)),
            ("base_url", models.URLField(blank=True, max_length=500)), ("userid", models.CharField(blank=True, max_length=160)), ("domain_name", models.CharField(blank=True, max_length=255)),
            ("username", models.CharField(blank=True, max_length=160)), ("password_encrypted", models.TextField(blank=True)), ("headers", models.JSONField(blank=True, default=dict)),
            ("timeout_seconds", models.PositiveIntegerField(default=20)), ("max_retries", models.PositiveIntegerField(default=0)), ("metadata", models.JSONField(blank=True, default=dict)),
            ("is_active", models.BooleanField(default=True)), ("created_at", models.DateTimeField(auto_now_add=True)), ("updated_at", models.DateTimeField(auto_now=True)),
        ], options={"ordering": ["name"]}),
        migrations.CreateModel(name="Service", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("name", models.CharField(max_length=180)), ("slug", models.SlugField(max_length=180)), ("code", models.CharField(max_length=80, unique=True)), ("description", models.TextField(blank=True)),
            ("pricing_mode", models.CharField(choices=[("fixed", "سعر ثابت"), ("amount", "مبلغ يحدده العميل"), ("item", "حسب عنصر من الجدول")], default="fixed", max_length=12)),
            ("price", models.DecimalField(decimal_places=2, default=0, max_digits=18, validators=[django.core.validators.MinValueValidator(0)])),
            ("min_amount", models.DecimalField(blank=True, decimal_places=2, max_digits=18, null=True, validators=[django.core.validators.MinValueValidator(0)])),
            ("max_amount", models.DecimalField(blank=True, decimal_places=2, max_digits=18, null=True, validators=[django.core.validators.MinValueValidator(0)])),
            ("currency", models.CharField(default="YER", max_length=6)), ("request_schema", models.JSONField(blank=True, default=dict)), ("response_schema", models.JSONField(blank=True, default=dict)),
            ("metadata", models.JSONField(blank=True, default=dict)), ("icon", models.CharField(blank=True, max_length=80)), ("sort_order", models.PositiveIntegerField(default=0)), ("is_active", models.BooleanField(default=True)),
            ("category", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="services", to="services.servicecategory")),
        ], options={"ordering": ["sort_order", "id"], "verbose_name": "الخدمة", "verbose_name_plural": "الخدمات"}),
        migrations.CreateModel(name="ServiceField", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")), ("key", models.SlugField(max_length=80)), ("label", models.CharField(max_length=160)),
            ("field_type", models.CharField(choices=[("text", "نص"), ("number", "رقم"), ("decimal", "رقم عشري"), ("select", "اختيار"), ("boolean", "نعم/لا"), ("email", "بريد إلكتروني"), ("json", "بيانات JSON")], default="text", max_length=12)),
            ("required", models.BooleanField(default=True)), ("secret", models.BooleanField(default=False)), ("default_value", models.JSONField(blank=True, null=True)), ("choices", models.JSONField(blank=True, default=list)), ("validation", models.JSONField(blank=True, default=dict)), ("sort_order", models.PositiveIntegerField(default=0)), ("is_active", models.BooleanField(default=True)),
            ("service", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="fields", to="services.service")),
        ], options={"ordering": ["sort_order", "id"]}),
        migrations.CreateModel(name="ProviderLink", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("name", models.CharField(max_length=180)), ("code", models.SlugField(max_length=120, unique=True)), ("operation", models.CharField(blank=True, max_length=80)), ("path_template", models.CharField(max_length=500)),
            ("http_method", models.CharField(choices=[("GET", "GET"), ("POST", "POST"), ("PUT", "PUT")], default="GET", max_length=8)), ("fixed_params", models.JSONField(blank=True, default=dict)), ("field_map", models.JSONField(blank=True, default=dict)),
            ("headers", models.JSONField(blank=True, default=dict)), ("success_codes", models.JSONField(blank=True, default=list)), ("pending_codes", models.JSONField(blank=True, default=list)), ("status_path_template", models.CharField(blank=True, max_length=500)), ("status_params", models.JSONField(blank=True, default=dict)), ("metadata", models.JSONField(blank=True, default=dict)),
            ("priority", models.PositiveIntegerField(default=100)), ("is_active", models.BooleanField(default=True)), ("created_at", models.DateTimeField(auto_now_add=True)), ("updated_at", models.DateTimeField(auto_now=True)),
            ("provider", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="links", to="services.providerconnection")),
        ], options={"ordering": ["priority", "id"]}),
        migrations.CreateModel(name="ServiceDistribution", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")), ("priority", models.PositiveIntegerField(default=100)), ("conditions", models.JSONField(blank=True, default=dict)), ("is_active", models.BooleanField(default=True)), ("created_at", models.DateTimeField(auto_now_add=True)),
            ("provider_link", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="distributions", to="services.providerlink")), ("service", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="distributions", to="services.service")),
        ], options={"ordering": ["priority", "id"]}),
        migrations.CreateModel(name="TelecomDenomination", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")), ("name", models.CharField(max_length=160)), ("external_code", models.CharField(max_length=120)), ("face_value", models.DecimalField(decimal_places=2, max_digits=18)), ("sale_price", models.DecimalField(decimal_places=2, max_digits=18)), ("payment_type", models.CharField(blank=True, max_length=30)), ("line_type", models.CharField(blank=True, max_length=30)), ("metadata", models.JSONField(blank=True, default=dict)), ("sort_order", models.PositiveIntegerField(default=0)), ("is_active", models.BooleanField(default=True)), ("service", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="telecom_denominations", to="services.service")),
        ], options={"ordering": ["sort_order", "id"]}),
        migrations.CreateModel(name="TelecomPlan", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")), ("name", models.CharField(max_length=180)), ("external_code", models.CharField(max_length=120)), ("price", models.DecimalField(decimal_places=2, max_digits=18)), ("quota", models.DecimalField(blank=True, decimal_places=3, max_digits=18, null=True)), ("quota_unit", models.CharField(blank=True, max_length=20)), ("validity_days", models.PositiveIntegerField(blank=True, null=True)), ("payment_type", models.CharField(blank=True, max_length=30)), ("line_type", models.CharField(blank=True, max_length=30)), ("metadata", models.JSONField(blank=True, default=dict)), ("sort_order", models.PositiveIntegerField(default=0)), ("is_active", models.BooleanField(default=True)), ("service", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="telecom_plans", to="services.service")),
        ], options={"ordering": ["sort_order", "id"]}),
        migrations.CreateModel(name="GameProduct", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")), ("name", models.CharField(max_length=180)), ("external_code", models.CharField(max_length=120)), ("price", models.DecimalField(decimal_places=2, max_digits=18)), ("currency", models.CharField(default="YER", max_length=6)), ("metadata", models.JSONField(blank=True, default=dict)), ("sort_order", models.PositiveIntegerField(default=0)), ("is_active", models.BooleanField(default=True)), ("service", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="game_products", to="services.service")),
        ], options={"ordering": ["sort_order", "id"]}),
        migrations.CreateModel(name="DigitalProduct", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")), ("name", models.CharField(max_length=180)), ("external_code", models.CharField(blank=True, max_length=120)), ("price", models.DecimalField(decimal_places=2, max_digits=18)), ("currency", models.CharField(default="YER", max_length=6)), ("validity_days", models.PositiveIntegerField(blank=True, null=True)), ("metadata", models.JSONField(blank=True, default=dict)), ("sort_order", models.PositiveIntegerField(default=0)), ("is_active", models.BooleanField(default=True)), ("service", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="digital_products", to="services.service")),
        ], options={"ordering": ["sort_order", "id"]}),
        migrations.CreateModel(name="ServiceTransaction", fields=[
            ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)), ("item_type", models.CharField(blank=True, max_length=40)), ("item_id", models.PositiveBigIntegerField(blank=True, null=True)), ("currency", models.CharField(default="YER", max_length=6)), ("customer_amount", models.DecimalField(decimal_places=2, max_digits=18)), ("payload", models.JSONField(blank=True, default=dict)), ("mobile", models.CharField(blank=True, max_length=40)), ("provider_transaction_id", models.CharField(blank=True, max_length=80)), ("provider_response", models.JSONField(blank=True, default=dict)),
            ("status", models.CharField(choices=[("accepted", "مقبول ومُحجز"), ("queued", "بانتظار التنفيذ"), ("processing", "قيد التنفيذ"), ("pending_provider", "قيد المعالجة لدى المزود"), ("success", "ناجح"), ("failed", "فاشل"), ("refunded", "مُعاد الرصيد")], default="accepted", max_length=24)),
            ("error_code", models.CharField(blank=True, max_length=80)), ("error_message", models.TextField(blank=True)), ("idempotency_key", models.CharField(blank=True, max_length=180, null=True, unique=True)), ("reserved_journal_id", models.BigIntegerField(blank=True, null=True)), ("settled_journal_id", models.BigIntegerField(blank=True, null=True)), ("refund_journal_id", models.BigIntegerField(blank=True, null=True)), ("created_at", models.DateTimeField(auto_now_add=True)), ("updated_at", models.DateTimeField(auto_now=True)), ("completed_at", models.DateTimeField(blank=True, null=True)),
            ("customer", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="service_transactions", to=settings.AUTH_USER_MODEL)), ("provider_link", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="transactions", to="services.providerlink")), ("service", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="transactions", to="services.service")),
        ], options={"ordering": ["-created_at"]}),
        migrations.CreateModel(name="ServiceTask", fields=[
            ("id", models.BigAutoField(primary_key=True, serialize=False)), ("kind", models.CharField(choices=[("submit", "إرسال العملية"), ("status_check", "فحص حالة العملية")], max_length=20)), ("status", models.CharField(choices=[("queued", "في قائمة الانتظار"), ("running", "قيد التنفيذ"), ("retry", "إعادة محاولة"), ("done", "مكتملة"), ("failed", "فشلت")], default="queued", max_length=12)), ("available_at", models.DateTimeField()), ("attempts", models.PositiveIntegerField(default=0)), ("max_attempts", models.PositiveIntegerField(default=3)), ("last_error", models.TextField(blank=True)), ("metadata", models.JSONField(blank=True, default=dict)), ("started_at", models.DateTimeField(blank=True, null=True)), ("finished_at", models.DateTimeField(blank=True, null=True)), ("created_at", models.DateTimeField(auto_now_add=True)),
            ("provider_link", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="tasks", to="services.providerlink")), ("transaction", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="tasks", to="services.servicetransaction")),
        ], options={"ordering": ["available_at", "id"]}),
        migrations.AddConstraint(model_name="servicecategory", constraint=models.UniqueConstraint(fields=["main_category", "parent", "slug"], name="uniq_service_category_tree_slug")),
        migrations.AddConstraint(model_name="service", constraint=models.UniqueConstraint(fields=["category", "slug"], name="uniq_service_category_slug")),
        migrations.AddConstraint(model_name="servicefield", constraint=models.UniqueConstraint(fields=["service", "key"], name="uniq_service_field_key")),
        migrations.AddConstraint(model_name="servicedistribution", constraint=models.UniqueConstraint(fields=["service", "provider_link"], name="uniq_service_distribution_link")),
        migrations.RunPython(seed_main_categories, migrations.RunPython.noop),
        migrations.AddIndex(model_name="servicecategory", index=models.Index(fields=["main_category", "is_active"], name="svc_cat_main_active_idx")),
        migrations.AddIndex(model_name="providerlink", index=models.Index(fields=["provider", "is_active", "priority"], name="svc_link_provider_priority_idx")),
        migrations.AddIndex(model_name="servicedistribution", index=models.Index(fields=["service", "is_active", "priority"], name="svc_dist_service_priority_idx")),
        migrations.AddIndex(model_name="servicetransaction", index=models.Index(fields=["customer", "status", "created_at"], name="svc_tx_customer_status_idx")),
        migrations.AddIndex(model_name="servicetransaction", index=models.Index(fields=["status", "created_at"], name="svc_tx_status_created_idx")),
        migrations.AddIndex(model_name="servicetask", index=models.Index(fields=["status", "available_at", "id"], name="svc_task_queue_idx")),
    ]
