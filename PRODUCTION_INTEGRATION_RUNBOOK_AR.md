# Runbook تشغيل الإنتاج — Marketplace / Services

## 1. قبل النشر

خذ نسخة احتياطية من قاعدة البيانات واحتفظ بها خارج مسار التطبيق. لا تنفذ أي ترحيل مالي على قاعدة الإنتاج دون نسخة احتياطية قابلة للاسترجاع.

تحقق من:

```bash
git status
git rev-parse HEAD
python manage.py check
python manage.py check --deploy
python manage.py makemigrations --check
python manage.py showmigrations
```

## 2. تثبيت التغييرات والمهاجرات

بعد تحديث الكود:

```bash
cd /home/root/projects/marketplace/backend
source venv/bin/activate
pip install -r requirements.txt
python manage.py makemigrations --check
python manage.py migrate --plan
python manage.py migrate --noinput
```

في هذه المجموعة من التغييرات لم تتم إضافة تغييرات schema جديدة لكل منطق المحاسبة/الكتالوج الذي أضيف في الملفات الخدمية؛ CI يتحقق من `makemigrations --check` ثم ينفذ `migrate`.

## 3. نسخة SQL القديمة

افتح نسخة قاعدة البيانات القديمة ثم مرر ملف SQL غير المضغوط إلى:

```bash
python manage.py import_legacy_catalog --sql /path/to/legacy.sql
```

ولتنظيم الألعاب والبرامج بعد الاستيراد:

```bash
python manage.py normalize_legacy_catalog_hierarchy
```

ثم:

```bash
python manage.py audit_service_catalog --fail
python manage.py audit_production_routes --strict
```

## 4. نتيجة تدقيق نسخة SQL الفعلية

النسخة القديمة التي تم فحصها تحتوي على:

```text
245 operationsgroups
224 مجموعات ألعاب
2541 gameunits
40 servicescardstbl
55 mtnoffers
71 sabaoffers
9 sbayoffers
9 whyoffers
6 adenet
6 yem4g
```

كما أن جميع وحدات `gameunits` لديها `uniq_code`، لكن أسعار `unit_price` القديمة ليست المصدر المناسب لتفعيل عمليات شراء حديثة دون مراجعة؛ أغلب السعر موجود كـUSD بمعدل قديم 560 YER، ووحدة واحدة بلا سعر صالح.

هناك أيضًا مجموعات ألعاب قديمة بلا `gameunits`. لا يجب إنشاء فئات شراء وهمية لها.

التقرير المفصل الناتج من النسخة الفعلية محفوظ محليًا باسم:

`LEGACY_CATALOG_SQL_AUDIT_AR.md`

## 5. قاعدة تفعيل الألعاب والبرامج

الاستيراد يفرق بين:

```text
الألعاب
البرامج والتطبيقات
البطاقات الرقمية
```

الوحدة القديمة غير الموثقة في عقد المزود لا تُفعل آليًا للشراء.

لا تستخدم `gameunits.link_id` القديم كأنه `provider_num` لمجرد أنه يحمل رقمًا. البيانات القديمة تُحفظ كمرجع تاريخي، أما رقم المزود الفعلي فيأتي من ProviderLink/عقد المزود أو من مزامنة موثقة.

## 6. إعداد المزود

أنشئ ProviderConnection:

```text
code
name
connection_type
base_url
userid
username
password
headers
timeout_seconds
max_retries
```

كلمة المرور تُخزن مشفرة.

في الإنتاج يجب أن يكون عنوان Sanaacash HTTPS.

ثم أنشئ ProviderLink لكل عملية:

```text
operation
path_template
http_method
request_encoding
fixed_params
field_map
success_codes
pending_codes
status_path_template
status_params
priority
```

## 7. فحص الربطيات

```bash
python manage.py audit_production_routes --strict --provider sanaacash-1
```

يجب ألا توجد خدمة مدفوعة فعالة بدون:

```text
ProviderConnection فعال
ProviderLink فعال
ServiceDistribution فعال
```

## 8. مزامنة كتالوج المزود

للربطية التي تحتوي:

```json
{
  "catalog": {
    "enabled": true,
    "service_code": "you-offer",
    "item_type": "telecom_plans",
    "response_path": "data.offers",
    "fields": {
      "name": ["name", "title"],
      "external_code": ["id", "code"],
      "provider_num": ["num", "number"],
      "price": ["price", "amount"],
      "quantity": ["qty", "available"],
      "packageid": ["packageid", "package_id"]
    }
  }
}
```

نفذ أولًا:

```bash
python manage.py sync_provider_catalog --provider sanaacash-1 --link you-catalog --dry-run
```

ثم بعد المراجعة:

```bash
python manage.py sync_provider_catalog --provider sanaacash-1 --link you-catalog
```

`--prune` لا يحذف الصفوف، بل يعطل الصفوف التي اختفت من رد المزود.

## 9. تشغيل Worker باستمرار

انسخ الوحدة:

```bash
bash deploy/install_services_worker.sh /home/root/projects/marketplace/backend
```

أو يدويًا:

```bash
systemctl daemon-reload
systemctl enable --now marketplace-services-worker.service
systemctl status marketplace-services-worker.service
journalctl -u marketplace-services-worker.service -f
```

العامل يعيد المحاولات، يتعامل مع SIGTERM، ويستعيد المهام التي ظلت `RUNNING` أكثر من 10 دقائق.

## 10. اختبار Webhook

اختبر على بيئة اختبار أولًا:

```bash
curl -i 'https://shopik.alattab.site/api/v2/services/webhook/sanaacash/?action=done&backpass=TEST_SECRET&transid=12345'
```

ولـban:

```bash
curl -i 'https://shopik.alattab.site/api/v2/services/webhook/sanaacash/?action=ban&backpass=TEST_SECRET&transid=12345&message=test'
```

يجب أن يرفض السر الخاطئ بـ403.

Webhook لعملية مدفوعة لا تحتوي `reserved_journal_id` ينتقل إلى `manual_review` ولا ينشئ استردادًا أو تسوية آلية.

إعادة نفس Webhook بعد نجاح/استرداد العملية آمنة ولا تنشئ قيدًا ثانيًا.

## 11. اختبار Network Failure

اختبر بطريقتين:

```text
Connection timeout
HTTP 500
```

النتيجة المتوقعة:

```text
pending_provider / manual_review
```

وليس:

```text
refund + failover
```

لأن الشبكة لا تثبت أن المزود لم ينفذ العملية.

## 12. اختبار Pending

إذا رد المزود:

```text
resultCode = -2
```

يجب أن تصبح العملية:

```text
pending_provider
```

ويتم إنشاء مهمة `STATUS_CHECK` عند وجود مسار حالة.

إذا لم يوجد مسار حالة، تصبح:

```text
manual_review
```

## 13. اختبار Idempotency

أرسل نفس الطلب مرتين بنفس:

```http
Idempotency-Key: test-request-001
```

المتوقع:

```text
عملية مالية واحدة
ServiceTransaction واحدة
Journal واحد
```

أما استخدام نفس المفتاح لمبلغ أو خدمة مختلفة فيرجع:

```http
409 Conflict
```

## 14. اختبار تطابق المحفظة وكشف الحساب

بعد كل عملية:

```bash
python manage.py audit_financial_integrity --fail-on-mismatch --strict
```

وعبر API العميل:

```text
GET /api/v2/accounting/wallets/me/balance/
GET /api/v2/accounting/wallets/me/statement/
```

القيمة التي يعرضها التطبيق يجب أن تأتي من `accounting` وليس من حقل `finance.Wallet.balance` كرصيد مستقل.

## 15. العمليات المالية المقبولة

```text
شحن/تسوية إدارية
تحويل
هدية
حجز خدمة
نجاح خدمة
استرداد خدمة
حجز طلب
تحرير مستحق التاجر
حجز السحب
دفع السحب
رفض السحب
```

كلها تمر عبر قيود محاسبية قابلة للتدقيق.

## 16. إضافة لعبة جديدة بعد الإنتاج

لا تعدل الكود.

من لوحة الإدارة:

```text
الألعاب
→ فئة اللعبة
→ Service
→ ServiceField
→ GameProduct
→ ProviderLink
→ ServiceDistribution
```

ضع السعر وكود الفئة/`uniqcode` الموثق فقط، ثم جرّب العملية قبل التفعيل.

## 17. إضافة باقة جديدة

```text
الاتصالات
→ الشركة
→ نوع الباقات
→ Service / TelecomPlan
```

مثال:

```text
يمن موبايل
  ├─ 4G
  ├─ فولتي
  ├─ باقات بيانات
  └─ عروض أخرى
```

لا يحتاج التطبيق إلى تحديث، لأن `GET /api/v2/services/catalog/` يجلب البنية الجديدة ديناميكيًا.

## 18. إضافة برنامج جديد

```text
البرامج والتطبيقات
→ اسم البرنامج
→ Service
→ الحقول
→ الموارد
→ الربطية
→ التوزيع
```

## 19. قبول/رفض العنصر

أي مورد بدون:

```text
سعر بيع صالح
كود مزود صحيح
ProviderLink صالح
```

يجب أن يبقى:

```text
purchaseable=false
```

حتى لا يستطيع العميل دفع المال مقابل عنصر لا يمكن تنفيذه بثقة.

## 20. نشر آمن

التسلسل الموصى به:

```text
Backup
↓
Deploy code
↓
check
↓
makemigrations --check
↓
migrate
↓
audit catalog
↓
audit production routes
↓
worker status
↓
webhook test
↓
idempotency test
↓
financial audit
↓
frontend smoke test
```

لا تطلق عمليات مالية حقيقية من شاشة الإدارة لمجرد أن `catalog` يظهر؛ يجب أولًا اجتياز فحص الربط والتسعير والتوفر واختبار مزود فعلي على بيئة مناسبة.
