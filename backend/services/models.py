import uuid

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone


class MainServiceCategory(models.Model):
    name = models.CharField(max_length=120, unique=True)
    slug = models.SlugField(max_length=120, unique=True)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=80, blank=True)
    sort_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["sort_order", "id"]
        verbose_name = "الفئة الرئيسية"
        verbose_name_plural = "الفئات الرئيسية"

    def __str__(self):
        return self.name


class ServiceCategory(models.Model):
    main_category = models.ForeignKey(MainServiceCategory, on_delete=models.PROTECT, related_name="categories")
    parent = models.ForeignKey("self", null=True, blank=True, on_delete=models.PROTECT, related_name="children")
    name = models.CharField(max_length=160)
    slug = models.SlugField(max_length=160)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=80, blank=True)
    sort_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["sort_order", "id"]
        constraints = [models.UniqueConstraint(fields=["main_category", "parent", "slug"], name="uniq_service_category_tree_slug")]
        verbose_name = "فئة الخدمة"
        verbose_name_plural = "فئات الخدمات"

    def __str__(self):
        return self.name


class Service(models.Model):
    class PricingModes(models.TextChoices):
        FIXED = "fixed", "سعر ثابت"
        AMOUNT = "amount", "مبلغ يحدده العميل"
        ITEM = "item", "حسب عنصر من الجدول"

    class ServiceKinds(models.TextChoices):
        QUERY = "query", "استعلام بدون خصم"
        CATALOG = "catalog", "كتالوج/عرض بدون خصم"
        PURCHASE = "purchase", "عملية مدفوعة"

    category = models.ForeignKey(ServiceCategory, on_delete=models.PROTECT, related_name="services")
    name = models.CharField(max_length=180)
    slug = models.SlugField(max_length=180)
    code = models.CharField(max_length=80, unique=True)
    description = models.TextField(blank=True)
    service_kind = models.CharField(max_length=12, choices=ServiceKinds.choices, default=ServiceKinds.PURCHASE)
    requires_balance = models.BooleanField(default=True)
    pricing_mode = models.CharField(max_length=12, choices=PricingModes.choices, default=PricingModes.FIXED)
    price = models.DecimalField(max_digits=18, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    min_amount = models.DecimalField(max_digits=18, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(0)])
    max_amount = models.DecimalField(max_digits=18, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(0)])
    currency = models.CharField(max_length=6, default="YER")
    request_schema = models.JSONField(default=dict, blank=True)
    response_schema = models.JSONField(default=dict, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    icon = models.CharField(max_length=80, blank=True)
    sort_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["sort_order", "id"]
        constraints = [models.UniqueConstraint(fields=["category", "slug"], name="uniq_service_category_slug")]
        indexes = [models.Index(fields=["category", "is_active"], name="svc_category_active_idx")]
        verbose_name = "الخدمة"
        verbose_name_plural = "الخدمات"

    def __str__(self):
        return self.name


class ServiceField(models.Model):
    class FieldTypes(models.TextChoices):
        TEXT = "text", "نص"
        NUMBER = "number", "رقم"
        DECIMAL = "decimal", "رقم عشري"
        SELECT = "select", "اختيار"
        BOOLEAN = "boolean", "نعم/لا"
        EMAIL = "email", "بريد إلكتروني"
        JSON = "json", "بيانات JSON"

    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name="fields")
    key = models.SlugField(max_length=80)
    label = models.CharField(max_length=160)
    field_type = models.CharField(max_length=12, choices=FieldTypes.choices, default=FieldTypes.TEXT)
    required = models.BooleanField(default=True)
    secret = models.BooleanField(default=False)
    default_value = models.JSONField(null=True, blank=True)
    choices = models.JSONField(default=list, blank=True)
    validation = models.JSONField(default=dict, blank=True)
    sort_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["sort_order", "id"]
        constraints = [models.UniqueConstraint(fields=["service", "key"], name="uniq_service_field_key")]

    def __str__(self):
        return f"{self.service.code}:{self.key}"


class ProviderConnection(models.Model):
    class Types(models.TextChoices):
        SANAACASH = "sanaacash", "يمن روبوت / صنعاء كاش"
        HTTP_JSON = "http_json", "HTTP JSON"
        MANUAL = "manual", "تشغيل يدوي"

    name = models.CharField(max_length=160, unique=True)
    code = models.SlugField(max_length=100, unique=True)
    connection_type = models.CharField(max_length=20, choices=Types.choices, default=Types.SANAACASH)
    base_url = models.URLField(max_length=500, blank=True)
    userid = models.CharField(max_length=160, blank=True)
    domain_name = models.CharField(max_length=255, blank=True)
    username = models.CharField(max_length=160, blank=True)
    password_encrypted = models.TextField(blank=True)
    headers = models.JSONField(default=dict, blank=True)
    timeout_seconds = models.PositiveIntegerField(default=20)
    max_retries = models.PositiveIntegerField(default=0)
    metadata = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    def set_password(self, raw_password):
        from .security import encrypt_secret
        self.password_encrypted = encrypt_secret(raw_password or "")

    def get_password(self):
        from .security import decrypt_secret
        return decrypt_secret(self.password_encrypted)


class ProviderLink(models.Model):
    class Methods(models.TextChoices):
        GET = "GET", "GET"
        POST = "POST", "POST"
        PUT = "PUT", "PUT"

    class RequestEncodings(models.TextChoices):
        QUERY = "query", "Query parameters"
        FORM = "form", "Form body"
        JSON = "json", "JSON body"

    provider = models.ForeignKey(ProviderConnection, on_delete=models.PROTECT, related_name="links")
    name = models.CharField(max_length=180)
    code = models.SlugField(max_length=120, unique=True)
    operation = models.CharField(max_length=80, blank=True)
    path_template = models.CharField(max_length=500)
    http_method = models.CharField(max_length=8, choices=Methods.choices, default=Methods.GET)
    request_encoding = models.CharField(max_length=10, choices=RequestEncodings.choices, default=RequestEncodings.QUERY)
    fixed_params = models.JSONField(default=dict, blank=True)
    field_map = models.JSONField(default=dict, blank=True)
    headers = models.JSONField(default=dict, blank=True)
    success_codes = models.JSONField(default=list, blank=True)
    pending_codes = models.JSONField(default=list, blank=True)
    status_path_template = models.CharField(max_length=500, blank=True)
    status_params = models.JSONField(default=dict, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    priority = models.PositiveIntegerField(default=100)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["priority", "id"]
        indexes = [models.Index(fields=["provider", "is_active", "priority"], name="svc_link_provider_priority_idx")]

    def __str__(self):
        return self.name


class ServiceDistribution(models.Model):
    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name="distributions")
    provider_link = models.ForeignKey(ProviderLink, on_delete=models.PROTECT, related_name="distributions")
    priority = models.PositiveIntegerField(default=100)
    conditions = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["priority", "id"]
        constraints = [models.UniqueConstraint(fields=["service", "provider_link"], name="uniq_service_distribution_link")]
        indexes = [models.Index(fields=["service", "is_active", "priority"], name="svc_dist_service_priority_idx")]


class ServiceOption(models.Model):
    """Generic provider catalog row for services whose PDF table supplies arbitrary codes/numbers."""
    service = models.ForeignKey(Service, on_delete=models.PROTECT, related_name="options")
    name = models.CharField(max_length=180)
    external_code = models.CharField(max_length=120, blank=True)
    provider_num = models.CharField(max_length=120, blank=True)
    price = models.DecimalField(max_digits=18, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    currency = models.CharField(max_length=6, default="YER")
    metadata = models.JSONField(default=dict, blank=True)
    sort_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["sort_order", "id"]
        constraints = [models.UniqueConstraint(fields=["service", "external_code", "provider_num", "name"], name="uniq_service_option_identity")]
        indexes = [models.Index(fields=["service", "is_active"], name="svc_option_active_idx")]

    def __str__(self):
        return f"{self.service.code}:{self.name}"


class TelecomDenomination(models.Model):
    service = models.ForeignKey(Service, on_delete=models.PROTECT, related_name="telecom_denominations")
    name = models.CharField(max_length=160)
    external_code = models.CharField(max_length=120)
    face_value = models.DecimalField(max_digits=18, decimal_places=2)
    sale_price = models.DecimalField(max_digits=18, decimal_places=2)
    payment_type = models.CharField(max_length=30, blank=True)
    line_type = models.CharField(max_length=30, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    sort_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["sort_order", "id"]
        indexes = [models.Index(fields=["service", "is_active"], name="svc_telco_denom_active_idx")]


class TelecomPlan(models.Model):
    service = models.ForeignKey(Service, on_delete=models.PROTECT, related_name="telecom_plans")
    name = models.CharField(max_length=180)
    external_code = models.CharField(max_length=120)
    price = models.DecimalField(max_digits=18, decimal_places=2)
    quota = models.DecimalField(max_digits=18, decimal_places=3, null=True, blank=True)
    quota_unit = models.CharField(max_length=20, blank=True)
    validity_days = models.PositiveIntegerField(null=True, blank=True)
    payment_type = models.CharField(max_length=30, blank=True)
    line_type = models.CharField(max_length=30, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    sort_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["sort_order", "id"]
        indexes = [models.Index(fields=["service", "is_active"], name="svc_telco_plan_active_idx")]


class GameProduct(models.Model):
    service = models.ForeignKey(Service, on_delete=models.PROTECT, related_name="game_products")
    name = models.CharField(max_length=180)
    external_code = models.CharField(max_length=120)
    price = models.DecimalField(max_digits=18, decimal_places=2)
    currency = models.CharField(max_length=6, default="YER")
    metadata = models.JSONField(default=dict, blank=True)
    sort_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["sort_order", "id"]
        indexes = [models.Index(fields=["service", "is_active"], name="svc_game_product_active_idx")]


class DigitalProduct(models.Model):
    service = models.ForeignKey(Service, on_delete=models.PROTECT, related_name="digital_products")
    name = models.CharField(max_length=180)
    external_code = models.CharField(max_length=120, blank=True)
    price = models.DecimalField(max_digits=18, decimal_places=2)
    currency = models.CharField(max_length=6, default="YER")
    validity_days = models.PositiveIntegerField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    sort_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["sort_order", "id"]


class ServiceRequestReference(models.Model):
    """Durable registry of every numeric provider transaction id ever allocated."""
    transid = models.PositiveBigIntegerField(unique=True)
    provider = models.ForeignKey("ProviderConnection", on_delete=models.PROTECT, related_name="request_references")
    transaction = models.ForeignKey("ServiceTransaction", null=True, blank=True, on_delete=models.SET_NULL, related_name="provider_references")
    request_kind = models.CharField(max_length=40, default="service")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [models.Index(fields=["provider", "created_at"], name="svc_ref_provider_created_idx")]


class ServiceTransaction(models.Model):
    class Status(models.TextChoices):
        ACCEPTED = "accepted", "مقبول ومُحجز"
        QUEUED = "queued", "بانتظار التنفيذ"
        PROCESSING = "processing", "قيد التنفيذ"
        PENDING_PROVIDER = "pending_provider", "قيد المعالجة لدى المزود"
        MANUAL_REVIEW = "manual_review", "يحتاج مراجعة تشغيلية"
        SUCCESS = "success", "ناجح"
        FAILED = "failed", "فاشل"
        REFUNDED = "refunded", "مُعاد الرصيد"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    customer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="service_transactions")
    service = models.ForeignKey(Service, on_delete=models.PROTECT, related_name="transactions")
    item_type = models.CharField(max_length=40, blank=True)
    item_id = models.PositiveBigIntegerField(null=True, blank=True)
    currency = models.CharField(max_length=6, default="YER")
    customer_amount = models.DecimalField(max_digits=18, decimal_places=2)
    payload = models.JSONField(default=dict, blank=True)
    mobile = models.CharField(max_length=40, blank=True)
    provider_link = models.ForeignKey(ProviderLink, null=True, blank=True, on_delete=models.PROTECT, related_name="transactions")
    provider_transid = models.PositiveBigIntegerField(null=True, blank=True, unique=True)
    provider_transaction_id = models.CharField(max_length=80, blank=True)
    provider_response = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=24, choices=Status.choices, default=Status.ACCEPTED)
    error_code = models.CharField(max_length=80, blank=True)
    error_message = models.TextField(blank=True)
    idempotency_key = models.CharField(max_length=180, unique=True, null=True, blank=True)
    reserved_journal_id = models.BigIntegerField(null=True, blank=True)
    settled_journal_id = models.BigIntegerField(null=True, blank=True)
    refund_journal_id = models.BigIntegerField(null=True, blank=True)
    webhook_secret_encrypted = models.TextField(blank=True)
    webhook_received_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["customer", "status", "created_at"], name="svc_tx_customer_status_idx"),
            models.Index(fields=["status", "created_at"], name="svc_tx_status_created_idx"),
        ]


class ServiceTask(models.Model):
    class Kinds(models.TextChoices):
        SUBMIT = "submit", "إرسال العملية"
        STATUS_CHECK = "status_check", "فحص حالة العملية"

    class Statuses(models.TextChoices):
        QUEUED = "queued", "في قائمة الانتظار"
        RUNNING = "running", "قيد التنفيذ"
        RETRY = "retry", "إعادة محاولة"
        DONE = "done", "مكتملة"
        FAILED = "failed", "فشلت"

    id = models.BigAutoField(primary_key=True)
    transaction = models.ForeignKey(ServiceTransaction, on_delete=models.CASCADE, related_name="tasks")
    kind = models.CharField(max_length=20, choices=Kinds.choices)
    status = models.CharField(max_length=12, choices=Statuses.choices, default=Statuses.QUEUED)
    provider_link = models.ForeignKey(ProviderLink, null=True, blank=True, on_delete=models.PROTECT, related_name="tasks")
    available_at = models.DateTimeField(default=timezone.now)
    attempts = models.PositiveIntegerField(default=0)
    max_attempts = models.PositiveIntegerField(default=3)
    last_error = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["available_at", "id"]
        indexes = [models.Index(fields=["status", "available_at", "id"], name="svc_task_queue_idx")]

    def __str__(self):
        return f"#{self.id} {self.get_kind_display()} {self.transaction_id}"
