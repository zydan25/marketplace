# دليل ربط تطبيق العميل — Marketplace API v2

## 1. الأساسيات

Base URL:

`https://shopik.alattab.site`

المصادقة:

```http
Authorization: Token <TOKEN>
Content-Type: application/json
```

يوصى باستخدام HTTPS دائمًا، وعدم وضع أي كلمة مرور للمزود أو `token` أو `backpass` داخل تطبيق العميل.

نقطة وصف الـAPI:

`GET /api/v2/`

مخطط الـAPI:

`GET /api/v2/schema/`

عقد المحاسبة:

`GET /api/v2/accounting/contract/`

## 2. الحساب

### تسجيل الدخول

`POST /api/v2/accounts/login/`

```json
{
  "phone": "777777777",
  "password": "********"
}
```

### التسجيل

`POST /api/v2/accounts/register/`

```json
{
  "phone": "777777777",
  "password": "********",
  "first_name": "محمد",
  "middle_name": "علي",
  "third_name": "عبدالله",
  "last_name": "أحمد",
  "governorate": "صنعاء"
}
```

### المستخدم الحالي

`GET /api/v2/accounts/me/`

## 3. المبدأ الأساسي للخدمات

التطبيق لا يحتوي أكواد المزود أو أسعار المزود داخل الكود المصدري. التطبيق يجلب الكتالوج من الخادم ثم يرسل فقط:

- `service_id`
- `item_type`
- `item_id`
- بيانات الحقول الموجودة في الخدمة.

الخادم هو الذي يضيف `external_code` و`num` و`uniqcode` و`packageid` وكل مفاتيح المزود اللازمة حسب العنصر والربطية.

## 4. كتالوج الخدمات

`GET /api/v2/services/catalog/`

النتيجة تكون شجرة:

`main category -> category -> child categories -> service -> fields/items`

أنواع العناصر الممكنة:

```text
service_options
telecom_denominations
telecom_plans
game_products
digital_products
```

كل خدمة تحمل:

```json
{
  "id": 123,
  "code": "pubg",
  "name": "بوبجي",
  "service_kind": "purchase",
  "requires_balance": true,
  "pricing_mode": "item",
  "price": "0.00",
  "currency": "YER",
  "fields": [],
  "items": []
}
```

الـ`items` تعرض فقط البيانات الآمنة للتطبيق، مثل الاسم والسعر والتوفر والمعلومات الوظيفية. لا تعتمد على رقم المزود الداخلي لتنفيذ العملية.

لجلب خدمة واحدة:

`GET /api/v2/services/services/<SERVICE_ID>/`

## 5. الألعاب

يمكن تمثيل اللعبة كخدمة:

```text
الألعاب
  ├─ بوبجي
  │   └─ خدمة pubg
  │       ├─ GameProduct: 60 UC
  │       ├─ GameProduct: 325 UC
  │       └─ GameProduct: ...
  └─ فري فاير
      └─ خدمة freefire
```

حقول اللعبة النموذجية حسب عقد المزود:

```text
mobile
uniqcode
playerid
playername
zoneid
email
```

التطبيق يطلب `item_id` لعنصر اللعبة ويترك `uniqcode` للخادم.

مثال شراء:

```http
POST /api/v2/services/requests/
Authorization: Token <TOKEN>
Idempotency-Key: android-20260906-000001
```

```json
{
  "service_id": 123,
  "item_type": "game_products",
  "item_id": 456,
  "payload": {
    "mobile": "777777777",
    "playerid": "123456789",
    "playername": "Player",
    "zoneid": "1234"
  }
}
```

## 6. البطاقات والبرامج الرقمية

تستخدم:

```text
digital_products
```

ومن أمثلتها الخدمات التي يغطيها العقد، مثل Google Play وApp Store وRazer Gold وLikee وBigo وغيرها.

العنصر غير الموثق من حيث سعر التنفيذ أو mapping المزود يبقى في الكتالوج، لكن تكون `availability.available=false` ولا يسمح الخادم بشرائه حتى تكتمل بيانات الربط.

## 7. خدمات شركات الاتصالات

البنية المقترحة:

```text
الاتصالات
  ├─ يمن موبايل
  │   ├─ شحن فئة
  │   │   └─ TelecomDenomination
  │   ├─ باقات 4G
  │   │   └─ TelecomPlan
  │   └─ باقات فولتي
  │       └─ TelecomPlan
  ├─ يو
  │   ├─ رصيد
  │   └─ باقات
  ├─ سبأفون
  │   ├─ شحن
  │   └─ باقات
  └─ يمن فورجي
      ├─ باقات
      ├─ رصيد
      └─ تغيير باقة
```

لا يتم تثبيت هذه الفئات في تطبيق العميل. الخادم يعيدها في الكتالوج، ويمكن للإدارة إنشاء فئات جديدة دون إصدار نسخة جديدة من التطبيق.

## 8. إنشاء عملية خدمة

`POST /api/v2/services/requests/`

### رأس إلزامي للعمليات المدفوعة

```http
Idempotency-Key: <unique-request-key>
```

الـKey يجب أن يكون ثابتًا لنفس محاولة العملية عند إعادة إرسال الطلب بسبب timeout أو إعادة فتح التطبيق.

### Body

```json
{
  "service_id": 123,
  "item_type": "telecom_plans",
  "item_id": 456,
  "payload": {
    "mobile": "777777777"
  }
}
```

الاستجابة الأولية:

```json
{
  "id": "uuid",
  "service": "you-offer",
  "service_kind": "purchase",
  "status": "queued",
  "amount": "1500.00",
  "currency": "YER",
  "provider_transid": null,
  "provider_transaction_id": null,
  "error_code": null,
  "error_message": null
}
```

حالة `202` تعني أن العملية قُبلت وحُجز مبلغها وأدخلت قائمة التنفيذ، وليست تأكيدًا أن المزود نفذها بعد.

## 9. متابعة العملية

`GET /api/v2/services/requests/<UUID>/`

الحالات المهمة:

```text
accepted
queued
processing
pending_provider
manual_review
success
failed
refunded
```

`manual_review` تعني أن نتيجة المزود غير مؤكدة؛ لا تعتبر فشلًا ولا ينبغي للتطبيق أن يقول للعميل إن المبلغ أعيد حتى يرى `refunded`.

## 10. المحفظة وكشف الحساب

للاطلاع على ملخص المحفظة:

`GET /api/v2/accounting/wallets/me/balance/`

لكشف الحساب:

`GET /api/v2/accounting/wallets/me/statement/`

المصدر المالي الحقيقي هو دفتر `accounting`. واجهة المحفظة القديمة موجودة للتوافق ولا ينبغي للتطبيق الاعتماد على حقل balance قديم كمصدر مستقل.

## 11. التحويل والهدية

التحويل:

`POST /api/v2/accounting/transfers/`

الهدية:

`POST /api/v2/accounting/gifts/`

مثال:

```http
Idempotency-Key: mobile-transfer-000001
```

```json
{
  "recipient": "777777778",
  "amount": "500.00",
  "currency": "YER",
  "note": "هدية"
}
```

لا تستخدم مسارًا مخصصًا لتعديل رصيد المستلم مباشرة.

## 12. الطلبات العادية

مسارات الطلبات الأساسية تحت:

`/api/v2/orders/`

العميل يرسل معرفات المنتجات والكميات، بينما الخادم يعيد حساب الأسعار والمخزون والشحن والعمولات ويعالج الحجز المالي.

## 13. التعامل مع الشبكة

إذا أعاد الخادم `pending_provider` أو `manual_review` فلا تعيد إرسال عملية مالية جديدة بمفتاح Idempotency مختلف.

عند timeout استخدم نفس `Idempotency-Key` واستعلم عن:

`GET /api/v2/services/requests/<UUID>/`

حتى تتضح النتيجة.

## 14. الأمان

ممنوع من تطبيق العميل:

```text
Provider password
Provider username
Provider userid
Provider token
backpass
ProviderLink path
ProviderLink field_map
```

هذه كلها بيانات خادمية فقط.

## 15. دورة عملية ناجحة

```text
App
 ↓
GET catalog
 ↓
اختيار service/item
 ↓
POST request + Idempotency-Key
 ↓
Server validates payload
 ↓
Server calculates amount
 ↓
Accounting reservation
 ↓
Queued task
 ↓
Provider
 ↓
Success / Pending
 ↓
Settlement
 ↓
GET request status
 ↓
wallet balance + statement
```

## 16. دورة timeout آمنة

```text
App POST
 ↓
Server reserves
 ↓
Provider may receive request
 ↓
timeout
 ↓
status=pending_provider
 ↓
status endpoint / webhook
 ↓
Success => settlement
Ban/failure => refund
Ambiguous => manual_review
```

بهذا لا يفقد العميل المبلغ آليًا ولا تحدث عملية ثانية بسبب إعادة الإرسال.
