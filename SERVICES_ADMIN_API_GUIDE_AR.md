# دليل إدارة الخدمات والكتالوج — لوحة الخادم

## 1. الفكرة

لوحة الإدارة مبنية على طبقات قابلة للإضافة:

```text
الفئة الرئيسية
  ↓
فئة / فئة فرعية
  ↓
الخدمة
  ↓
حقول الإدخال
  ↓
العناصر / الباقات / الوحدات
  ↓
ProviderLink
  ↓
ServiceDistribution
```

لا يلزم إصدار تطبيق جديد عند إضافة لعبة أو برنامج أو باقة إذا كانت الخدمة الجديدة تستخدم نفس عقد الربط الموجود.

## 2. واجهة الإدارة API

كل مسارات الإدارة تحت:

`/api/v2/services/admin/catalog/`

وتحتاج:

```http
Authorization: Token <ADMIN_TOKEN>
Content-Type: application/json
```

يُقبل فقط المستخدم الإداري (`is_staff` أو `role=admin`).

### قراءة الوضع الحالي

`GET /api/v2/services/admin/catalog/`

يعيد:

```text
main_categories
categories
services
providers
links
distributions
```

## 3. إضافة فئة رئيسية

`POST /api/v2/services/admin/catalog/main/`

```json
{
  "name": "الألعاب",
  "slug": "games",
  "icon": "gamepad",
  "sort_order": 10,
  "is_active": true
}
```

أمثلة للفئات الرئيسية:

```text
الألعاب
aالبرامج والتطبيقات
الاتصالات
البطاقات الرقمية
الكهرباء والمياه
الخدمات العامة
```

## 4. فئة اللعبة أو شركة الاتصالات

`POST /api/v2/services/admin/catalog/category/`

```json
{
  "main_category_id": 1,
  "parent_id": null,
  "name": "بوبجي",
  "slug": "pubg",
  "icon": "pubg",
  "sort_order": 1,
  "is_active": true
}
```

يمكن إنشاء فئات فرعية:

```json
{
  "main_category_id": 1,
  "parent_id": 10,
  "name": "UC",
  "slug": "uc",
  "sort_order": 1,
  "is_active": true
}
```

وبالتالي يمكن تمثيل:

```text
الألعاب
└── بوبجي
    ├── UC
    ├── باقات خاصة
    └── عروض موسمية
```

## 5. خدمة

`POST /api/v2/services/admin/catalog/service/`

```json
{
  "category_id": 10,
  "name": "بوبجي",
  "code": "pubg",
  "slug": "pubg",
  "service_kind": "purchase",
  "requires_balance": true,
  "pricing_mode": "item",
  "currency": "YER",
  "is_active": true
}
```

أنواع الخدمة:

```text
query
catalog
purchase
```

وطرق التسعير:

```text
fixed
amount
item
```

## 6. حقول خدمة اللعبة

`POST /api/v2/services/admin/catalog/field/`

مثال:

```json
{
  "service_id": 123,
  "key": "playerid",
  "label": "رقم اللاعب",
  "field_type": "text",
  "required": true,
  "secret": false,
  "validation": {}
}
```

مثال حقول بوبجي:

```text
playerid
playername
zoneid
mobile
```

ومثال Google Play:

```text
email
mobile
country
```

ومثال خدمة يمن نت:

```text
customer_id
mobile
```

## 7. مورد / فئة / باقة

`POST /api/v2/services/admin/catalog/resource/`

الـ`kind` يمكن أن يكون:

```text
option
denom
plan
game
digital
```

### لعبة

```json
{
  "kind": "game",
  "service_id": 123,
  "name": "60 UC",
  "external_code": "PUBG-60",
  "price": "1500",
  "currency": "YER",
  "provider_uniqcode": "PUBG60",
  "provider_num": "",
  "provider_quantity": "100",
  "purchaseable": true
}
```

### باقة اتصالات

```json
{
  "kind": "plan",
  "service_id": 200,
  "name": "فورجي 10GB",
  "external_code": "4G-10",
  "price": "3500",
  "currency": "YER",
  "quota": "10",
  "quota_unit": "GB",
  "validity_days": 30,
  "payment_type": "new",
  "line_type": "4G",
  "provider_num": "10GB",
  "provider_packageid": "1234",
  "purchaseable": true
}
```

وهكذا يمكن إنشاء:

```text
يمن موبايل
├── شحن فئات
├── باقات 4G
│   ├── 2GB
│   ├── 5GB
│   └── 10GB
└── باقات فولتي
    ├── ...
```

## 8. ربط المزود

`POST /api/v2/services/admin/catalog/provider/`

البيانات الحساسة مثل كلمة المرور تُرسل إلى الخادم فقط وتُخزن مشفرة.

مثال:

```json
{
  "name": "Sanaacash الأول",
  "code": "sanaacash-1",
  "connection_type": "sanaacash",
  "base_url": "https://sanaacash.yrbso.net/api/yr/",
  "userid": "...",
  "username": "...",
  "password": "...",
  "timeout_seconds": 20,
  "is_active": true
}
```

## 9. ProviderLink

`POST /api/v2/services/admin/catalog/link/`

مثال لشراء لعبة:

```json
{
  "provider_id": 1,
  "name": "Sanaacash games/cards",
  "code": "games-cards",
  "operation": "games_cards",
  "path_template": "gameswcards",
  "http_method": "GET",
  "request_encoding": "query",
  "field_map": {
    "type": "service.code",
    "uniqcode": "{{uniqcode}}",
    "playerid": "{{playerid}}",
    "playername": "{{playername}}",
    "zoneid": "{{zoneid}}",
    "email": "{{email}}",
    "mobile": "{{mobile}}"
  },
  "success_codes": ["0"],
  "pending_codes": ["-2"],
  "priority": 10,
  "is_active": true
}
```

الخادم يولد `transid` ولا يسمح للتطبيق بإرساله كقيمة يختارها بحرية.

## 10. ربط كتالوج المزود تلقائيًا

يمكن تعريف داخل `ProviderLink.metadata`:

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
      "quantity": ["qty", "available"] ,
      "packageid": ["packageid", "package_id"]
    }
  }
}
```

ثم شغّل:

```bash
python manage.py sync_provider_catalog --provider sanaacash-1 --link you-catalog --dry-run
```

راجع النتيجة، ثم:

```bash
python manage.py sync_provider_catalog --provider sanaacash-1 --link you-catalog
```

ويمكن لاحقًا استخدام:

```bash
--prune
```

لتعطيل العناصر التي اختفت من رد المزود بدل حذفها من قاعدة البيانات.

## 11. ServiceDistribution

`POST /api/v2/services/admin/catalog/distribution/`

```json
{
  "service_id": 123,
  "provider_link_id": 1,
  "priority": 10,
  "conditions": {},
  "is_active": true
}
```

التنفيذ يختار الربطيات حسب الأولوية. عند خطأ مزود قطعي يمكن الانتقال إلى الربطية التالية. أما timeout أو نتيجة غير مؤكدة فلا تؤدي إلى failover تلقائي.

## 12. مزامنة كمية المزود

إذا أعاد المزود كمية متاحة، تُحفظ داخليًا ضمن metadata كـ`provider_quantity` ويعرض تطبيق العميل حالة التوفر فقط/الكمية بحسب ما تسمح به سياسة الخدمة.

لا يُسمح بجعل الكمية القديمة من SQL بديلًا عن كمية المزود الحالي.

## 13. قاعدة مهمة للأسعار

إذا كانت الخدمة مدفوعة ولم يرسل المزود سعرًا صالحًا، تُحفظ المادة في الكتالوج لكن:

```text
purchaseable = false
```

ولا يستطيع العميل تنفيذ عملية شراء حتى يضاف سعر بيع معتمد.

## 14. إنشاء لعبة جديدة من الصفر

```text
1. إنشاء Main Category = الألعاب
2. إنشاء Category = اسم اللعبة
3. إنشاء Service = كود اللعبة
4. إضافة ServiceFields
5. إنشاء ProviderLink أو استخدام رابط games_cards
6. إضافة ServiceDistribution
7. إضافة GameProduct لكل فئة/وحدة
8. وضع provider_uniqcode والربط الصحيح
9. تحديد السعر
10. اختبار العملية
11. تفعيل is_active
```

## 15. إنشاء برنامج جديد

نفس الدورة، لكن تحت:

```text
البرامج والتطبيقات
└── اسم البرنامج
    └── Service
```

## 16. إنشاء باقات جديدة

لا توجد حاجة لتعديل تطبيق العميل. أضف `TelecomPlan` عبر واجهة `resource` أو استخدم مزامنة الكتالوج، ثم سيظهر العنصر تلقائيًا في:

```text
GET /api/v2/services/catalog/
```

## 17. الواجهة البشرية

تم الإبقاء على لوحة الإدارة التي تعتمد على أقسام:

```text
نظرة عامة
الفئات الرئيسية
الفئات
الخدمات
الحقول
الموارد
المزودون
الربطيات
التوزيع
العمليات
```

مع مسارات aliases للروابط القديمة حتى لا تنكسر الواجهة عند الانتقال إلى الكتالوج الديناميكي.
