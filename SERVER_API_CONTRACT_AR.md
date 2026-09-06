# عقد API الخادم — Marketplace / Services Platform

## 1. الهدف

هذا الملف هو العقد المقترح للربط بين تطبيق العميل وخادم Marketplace. التطبيق لا ينفذ عمليات التسديد أو الألعاب أو الباقات بنفسه؛ بل يرسل أمرًا إلى الخادم، والخادم يختار الخدمة والباقة والربطية والمزود، يحجز المبلغ محاسبيًا، ينفذ العملية، يتابع حالة المزود، ثم يسوي القيد أو يعيد الحجز عند الفشل.

المصدر الخارجي للخدمات هو عقد Sanaacash الموجود في `api 1 (59).pdf`. العقد يحدد token بصيغة MD5، و`transid` فريد، وحالات `resultCode=0` للنجاح و`-2` للمعالجة، وأكواد `10xx` للأخطاء، كما يحدد webhook بقيمتي `done` و`ban`.

## 2. قاعدة البيانات المرجعية التي تمت المقارنة معها

نسخة SQL المرجعية تحتوي على 187 جدولًا، ومن أهم الجداول القديمة:

- `clients` — العملاء والوكلاء وخصائص API.
- `balancetbl` — الرصيد المباشر لكل عميل.
- `operations` و`operationsgroups` — الخدمات والمجموعات.
- `operationsitems` — سجل تنفيذ العمليات.
- `gameunits` — 2541 وحدة لعبة/شحن في النسخة المرفقة.
- `servicescardstbl` — 40 خدمة بطاقة رقمية.
- `mtntbl`, `mtnoffers` — فئات وباقات يو.
- `sabatbl`, `sabaoffers` — فئات وباقات سبأفون.
- `sbaytbl`, `sbayoffers` — خدمات سبأفون الجنوب.
- `whytbl`, `whyoffers` — خدمات وباقات واي.
- `adenettbl` — باقات عدن نت.
- `yemfgtbl` — باقات يمن فورجي.
- `transferintbl` — تحويلات بين العملاء.
- `paids` و`paidstbl` — دفعات/تسويات العملاء.
- `sources` — الحسابات/المصادر المالية القديمة.
- `pricestbl`, `percentstblnew` — التسعير والنسب والعمولات.
- `settings` — إعدادات التشغيل القديمة.

لا يجب نقل هذه الجداول حرفيًا إلى النظام الجديد؛ المطلوب نقل منطقها إلى نماذج Django طبيعية مع الاحتفاظ بالمعرفات الخارجية في `metadata`.

## 3. API العام للتطبيق

Base URL:

`https://shopik.alattab.site`

Authentication:

`Authorization: Token <TOKEN>`

Content-Type:

`application/json`

### تسجيل الدخول

`POST /api/auth/login/`

```json
{
  "phone": "777777777",
  "password": "********"
}
```

الاستجابة:

```json
{
  "token": "...",
  "user": {
    "id": 1,
    "phone": "777777777",
    "role": "customer"
  }
}
```

### التسجيل

`POST /api/auth/register/`

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

## 4. كتالوج الخدمات

`GET /api/v2/services/catalog/`

يعيد شجرة:

`main category -> category -> service -> fields/items`

لا يضع التطبيق أسعارًا أو أكواد مزود ثابتة داخل الكود. يجب أن يأخذها من هذا الكتالوج.

كل خدمة تحتوي على:

- `id`
- `code`
- `name`
- `service_kind`
- `requires_balance`
- `pricing_mode`
- `price`
- `currency`
- `min_amount`
- `max_amount`
- `fields`
- `items`

## 5. إرسال أي عملية خدمة

`POST /api/v2/services/requests/`

يفضل إرسال:

```http
Idempotency-Key: mobile-20260906-000001
```

Body عام:

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

الخادم هو المسؤول عن:

1. التأكد من أن الخدمة فعالة.
2. التأكد من أن العنصر تابع للخدمة وفعال.
3. ملء `external_code` و`num` و`uniqcode` و`packageid` من الكتالوج عند الحاجة.
4. التحقق من الحقول.
5. تحديد مبلغ العملية.
6. إنشاء `ServiceTransaction`.
7. حجز المبلغ في المحاسبة.
8. وضع `ServiceTask` في قائمة التنفيذ.
9. اختيار `ProviderLink`.
10. إنشاء `transid` رقمي فريد.
11. إرسال العملية للمزود.
12. متابعة `pending` عبر status endpoint أو webhook.
13. تسوية القيد عند النجاح أو إعادة المبلغ عند الفشل.

الاستجابة الأولية تكون عادة HTTP 202:

```json
{
  "id": "uuid",
  "service": "yem-offer-bill",
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

## 6. الاستعلام عن عملية

`GET /api/v2/services/requests/<uuid>/`

الحالات:

- `accepted` — تم قبول العملية وحجز المبلغ.
- `queued` — في قائمة التنفيذ.
- `processing` — الخادم ينفذها.
- `pending_provider` — المزود لم يحسمها بعد.
- `manual_review` — نتيجة الشبكة غير مؤكدة ولا يجوز رد المال آليًا.
- `success` — ناجحة وتمت التسوية.
- `failed` — فاشلة.
- `refunded` — فاشلة وتم رد المبلغ.

## 7. Webhook المزود

`GET /api/v2/services/webhook/sanaacash/`

المزود يرسل:

`action=done|ban`

`backpass=<secret>`

`transid=<numeric transid>`

`message=<optional message>`

عند `done`:

- التحقق من `backpass`.
- العثور على العملية بـ `transid`.
- منع التحديث إذا كانت نهائية.
- ترحيل قيد التسوية.
- تغيير الحالة إلى `success`.

عند `ban`:

- التحقق من `backpass`.
- تسجيل سبب الإلغاء.
- رد المبلغ المحجوز.
- تغيير الحالة إلى `refunded`.

## 8. Token الخاص بالمزود

العقد القديم يحدد:

```text
hashPassword = md5(Password)
token = md5(hashPassword + transid + Username + mobile)
```

الخادم الحالي يطبق هذه الخوارزمية داخل `ProviderClient.sanaacash_token`.

يجب عدم نقل كلمة مرور المزود إلى تطبيق العميل.

## 9. خدمات Sanaacash التي يجب أن يدعمها الخادم

### يمن موبايل

- استعلام الرصيد: `yem?action=query`
- تسديد رصيد: `yem?action=bill`
- استعلام الباقات: `yem?action=queryoffer`
- تفعيل باقة: `yem?action=billoffer`
- تسديد وتفعيل الباقة في عملية واحدة: `offeryem?action=billoffer`

الحقول المهمة:

- `mobile`
- `amount`
- `offerid`
- `offerkey`
- `method=New|Renew|Remove`
- `solfa=Y|N`

### يمن نت

- ADSL: `post?action=bill&type=adsl`
- الهاتف الثابت: `post?action=bill&type=line`
- الاستعلام: `post?action=query`

رقم الاشتراك في العقد 8 أرقام.

### واي

- `why?action=bill`
- رصيد: `num` + `rasid`
- باقة: `num` + `packageid`

### يو / MTN

- رصيد مفتوح: `mtn?action=bill&israsid=1`
- فئة شحن: `mtn?action=bill`
- باقة: `mtnoffer`

### سبأفون

- شحن: `sabaphone?action=bill`
- باقات: `sabaoffer`
- وحدات: `sabaunits`

### سبأفون الجنوب

- باقات: `sbayoffer`
- شحن: `sbay?action=bill`

### الجملة

- `sabagomla`
- `mtngomla`
- `mobilegomla`

### يمن فورجي

`yem4g?action=bill`

القيم:

- `type=1` باقة.
- `type=2` رصيد.
- `type=3` تغيير باقة.

والاستعلام:

`yem4g?action=query`

### الكهرباء والماء

Endpoint:

`electwater`

الكهرباء:

- `action=query&act=elect`
- `action=bill&act=elect`

الماء:

- `action=query&act=water`
- `action=bill&act=water`

الحقول:

- `customer_id`
- `placeid`
- `mobile`
- `amount` عند التسديد.

العقد يذكر أن هذه العمليات تستخدم POST مع body من نوع form للمعرفات والبيانات الخاصة بالعداد.

## 10. الألعاب والبطاقات الرقمية

العقد الخارجي يستخدم endpoint:

`GET /api/yr/gameswcards`

الحقول:

- `type` — كود الخدمة.
- `uniqcode` — كود الفئة الموحد.
- `playerid` — رقم اللاعب.
- `playername` — اسم اللاعب.
- `zoneid` — Zone ID.
- `email` — البريد.
- `mobile` — رقم الهاتف.

الألعاب المذكورة صراحة في العقد:

- `pubg`
- `freefire`
- `legends`
- `loardstelmble`
- `clashroial`
- `genshmbacket`
- `clashofclanz`
- `newstatepobg`
- `praolstars`
- `hidadijwaher`
- `ddihadi`
- `calloffdyoty`
- `pompitch`

كما توجد بطاقات/خدمات رقمية:

- `googleplayusa`
- `googleplaykorea`
- `appstore`
- `beinconnect`
- `razergold`
- `crossfire`
- `plastationusa`
- `plastationsar`
- `visacard`
- `mastercard`
- `likee`
- `bigolive`

### نقطة مهمة في النسخة الاحتياطية

قاعدة البيانات القديمة تحتوي على 224 مجموعة ألعاب تقريبًا، و2541 وحدة في `gameunits`، أي أن الكتالوج القديم أوسع بكثير من قائمة الألعاب الصريحة في ملف API. لذلك أضيف في المشروع أمر:

`python manage.py import_legacy_catalog --sql /path/to/legacy.sql`

ليحوّل مجموعات الألعاب والوحدات القديمة إلى `Service` و`GameProduct` بدل حصر النظام في الـ13 لعبة الموجودة في عقد PDF فقط.

هذا يحافظ على منطق النظام القديم مع بقاء التنفيذ عبر endpoint الحديث `gameswcards`.

## 11. الباقات والفئات

الباقة ليست مبلغًا مرسلًا من التطبيق فقط.

الصحيح:

1. التطبيق يطلب الكتالوج.
2. المستخدم يختار `item_id`.
3. الخادم يقرأ السعر والكود من قاعدة البيانات.
4. الخادم يمنع تغيير السعر أو الكود من payload.
5. الخادم يضع `external_code/provider_num/uniqcode` بنفسه.
6. الخادم يحدد الربطية المناسبة.

هذا يمنع العميل من تغيير سعر الباقة أو إرسال كود مزود غير مصرح به.

## 12. المحاسبة — المصدر الوحيد للرصيد

المصدر الصحيح للرصيد يجب أن يكون:

`accounting.Account -> accounting.Wallet -> JournalEntry/JournalLine`

وليس تعديل رقم `balance` مباشرة.

الرصيد يحسب من القيود المرحّلة.

### حجز خدمة

```text
مدين: محفظة العميل
دائن: تسويات الخدمات المعلقة
```

### نجاح الخدمة

```text
مدين: تسويات الخدمات المعلقة
دائن: إيرادات الخدمات
```

### فشل الخدمة

```text
مدين: تسويات الخدمات المعلقة
دائن: محفظة العميل
```

وهذا يضمن ألا يختفي المبلغ عند Pending أو Failure.

## 13. التحويل بين العملاء

`POST /api/v2/accounting/transfers/`

```json
{
  "recipient": "777888999",
  "amount": "500.00",
  "currency": "YER",
  "note": "تحويل"
}
```

الخادم ينفذ:

```text
مدين: محفظة المرسل
دائن: محفظة المستلم
```

ولا يجب أن يعدل أي API رقم `balance` مباشرة.

## 14. الهدية

`POST /api/v2/accounting/gifts/`

```json
{
  "recipient": "777888999",
  "amount": "500.00",
  "currency": "YER",
  "message": "هدية"
}
```

منطقها المحاسبي نفس التحويل، لكن `source_type=gift`.

## 15. نقطة التوافق القديمة للهدية

العميل الحالي كان يستخدم أيضًا:

`/api/gifts/`

ويجب ألا يحتوي هذا المسار على خصم مباشر من `finance.Wallet.balance`.

الملف الجديد `backend/services/unified_wallet.py` يوفر جسرًا لتزامن محفظة finance القديمة مع المحاسبة، ويجب استخدام هذا النمط عند إبقاء APIs القديمة لأجل التوافق.

## 16. مشكلة المحفظتين التي تم اكتشافها

النسخة الحالية تحتوي على:

`finance.Wallet`

و:

`accounting.Wallet`

الأولى تحتوي `balance` مباشرًا و`WalletTransaction`، والثانية تعتمد على `Account` و`JournalEntry`.

هذا الفصل هو سبب محتمل لظهور حالة يكون فيها التطبيق يرى رصيدًا مختلفًا عن كشف الحساب المحاسبي.

القاعدة النهائية المقترحة:

**Accounting Wallet هو المصدر الحقيقي. Finance Wallet Projection للتوافق فقط.**

## 17. الطلبات Idempotency

كل عملية مالية أو خدمة يجب أن تدعم مفتاحًا فريدًا.

مثال:

`Idempotency-Key: gift:<uuid>`

أو:

`Idempotency-Key: service:<uuid>`

إذا أعاد العميل الطلب بسبب ضعف الإنترنت، يجب ألا ينشئ الخادم خصمًا ثانيًا.

## 18. transid

`transid` الخاص بالمزود يجب أن يكون:

- رقميًا.
- فريدًا.
- لا يعاد استخدامه.
- محفوظًا في `ServiceRequestReference`.

النظام الحالي يولد رقمًا عشوائيًا من 5 إلى 9 أرقام ويخزنه قبل استخدامه.

## 19. التعامل مع Network Failure

إذا لم يصل رد المزود بسبب الشبكة، لا يجوز رد المال مباشرة.

لأن العملية قد تكون وصلت للمزود ونفذت فعلًا.

المنطق الصحيح:

```text
NETWORK
  -> إذا يوجد status route
       -> PENDING_PROVIDER
       -> فحص الحالة دوريًا
  -> إذا لا يوجد status route
       -> MANUAL_REVIEW
```

## 20. Queue / Worker

يجب تشغيل عامل الخدمات باستمرار:

`python manage.py process_service_tasks --loop --limit 1 --sleep 1`

وظيفته تنفيذ `ServiceTask`، وإعادة المحاولة، وفحص العمليات Pending.

لا ينبغي جعل تطبيق الهاتف ينتظر انتهاء العملية الخارجية.

## 21. اختيار المزود والربطية

الخادم يستخدم:

- `ProviderConnection`
- `ProviderLink`
- `ServiceDistribution`

وبالتالي يمكن مستقبلاً وضع أكثر من مزود للخدمة نفسها:

```text
Service
 ├── Provider A priority 10
 ├── Provider B priority 20
 └── Provider C priority 30
```

وعند فشل A يمكن الانتقال إلى B فقط عندما تكون نتيجة A فشلًا مؤكّدًا، وليس عند Network Failure الغامض.

## 22. واجهات الإدارة المالية

`/api/v2/finance/`

الموارد الحالية:

- wallets
- wallet-transactions
- payments
- vendor-finance
- vendor-payouts
- vendor-ledger
- currency-rates
- vendor-city-shipping

## 23. واجهات المحاسبة

`/api/v2/accounting/`

الموارد:

- accounts
- wallets
- journals
- vouchers
- withdrawals
- `/me/report/`
- `/journals/post/`
- `/transfers/`
- `/gifts/`
- `/contract/`

## 24. واجهات التجارة

`/api/v2/orders/`

الطلب التجاري يمر عبر:

```text
Cart
 -> Order
 -> VendorOrder
 -> Payment
 -> Accounting funding
 -> Shipment
 -> Vendor release
 -> Payout
```

ولا ينبغي خلط طلب المنتج التجاري مع خدمة الاتصالات؛ كلاهما يستخدم المحاسبة نفسها.

## 25. الرصيد وشحن الرصيد

شحن رصيد العميل يجب أن ينتج سندًا وقيدًا محاسبيًا.

مثال سند قبض:

```text
مدين: الصندوق/الحساب البنكي
دائن: محفظة العميل
```

أما التعديل الإداري فلا يجب أن يكتب `wallet.balance` فقط؛ بل ينشئ قيدًا له مصدر واضح ومرجع.

## 26. أسعار البيع والعمولات

النظام المرجعي القديم يستخدم `pricestbl` و`percentstblnew` و`provspricetbl` وحقول أسعار داخل جداول الخدمات.

في النظام الجديد يجب فصل:

- سعر المزود.
- سعر العميل.
- عمولة المنصة.
- عمولة الوكيل/التاجر.
- العملة.
- سعر الصرف.

ولا ينبغي تخزين كل ذلك في حقل نصي واحد.

## 27. نموذج التسعير المقترح

```text
Provider Cost
     ↓
Customer Price
     ↓
Platform Commission
     ↓
Vendor/Agent Share
     ↓
Accounting Journal
```

ويجب حفظ Snapshot للسعر وقت العملية حتى لا تتغير فاتورة عملية قديمة بعد تعديل الباقة.

## 28. الباقات الموجودة في العقد

ملف API يحتوي على بيانات يمن موبايل تشمل أكواد الباقات مثل:

- `A68329`
- `A64329`
- `A38394`
- `A44330`
- `A66328`
- `A75328`
- `A76328`
- وأكواد باقات EVDO والدفع المسبق والفوترة المختلفة.

كما يحتوي على جداول سبأفون ويو. يجب إبقاء الكود الخارجي في قاعدة البيانات وعدم الاعتماد على اسم الباقة في التنفيذ.

## 29. الكهرباء والماء

لا يعتمد التطبيق على رقم منطقة ثابت.

التطبيق يرسل:

```json
{
  "customer_id": "123456",
  "placeid": "7"
}
```

والخادم يبني طلب المزود.

الاستعلام مجاني ولا يحجز رصيدًا.

التسديد يحجز الرصيد ويصبح له Transaction وقيد وحالة.

## 30. واجهة العميل المقترحة الموحدة

بدل أن يعرف العميل عشرات endpoints، يمكن للواجهة استخدام:

```text
GET  /api/v2/services/catalog/
GET  /api/v2/services/<id>/
POST /api/v2/services/requests/
GET  /api/v2/services/requests/<uuid>/
```

وهذا ينطبق على:

- يمن موبايل.
- سبأفون.
- يو.
- واي.
- يمن نت.
- يمن فورجي.
- عدن نت.
- الكهرباء.
- الماء.
- الألعاب.
- البطاقات الرقمية.

## 31. لا ترسل هذه الأشياء من العميل

لا يرسل العميل:

- `userid` الخاص بالمزود.
- Username المزود.
- Password المزود.
- Token المزود.
- `backpass`.
- URL المزود.
- سعر مزود يمكن أن يغير السعر الحقيقي.
- ProviderLink ID داخليًا كسلطة تنفيذ.

العميل يرسل فقط:

- service_id أو service code وفق العقد الداخلي.
- item_id عند اختيار باقة/فئة.
- الحقول التي يحتاجها المستخدم.
- Idempotency-Key.

## 32. نموذج عملية لعبة

أولًا:

`GET /api/v2/services/catalog/`

يجد مثلًا خدمة `pubg` وبداخلها GameProduct.

ثم:

```json
{
  "service_id": 501,
  "item_type": "game_products",
  "item_id": 9001,
  "payload": {
    "playerid": "123456789",
    "playername": "Player",
    "zoneid": "1234",
    "mobile": "777777777"
  }
}
```

الخادم يستخرج `uniqcode` من المنتج ويرسل `type=pubg`، ولا يثق بقيمة `type` القادمة من التطبيق.

## 33. نموذج عملية يمن موبايل باقة

```json
{
  "service_id": 10,
  "item_type": "telecom_plans",
  "item_id": 33,
  "payload": {
    "mobile": "777777777",
    "method": "New"
  }
}
```

الخادم يضع `offerid` أو `offerkey` من الكتالوج حسب نوع العملية، ويضع `transid/token/backurl` داخليًا.

## 34. نموذج رصيد مفتوح

```json
{
  "service_id": 20,
  "payload": {
    "mobile": "733333333",
    "amount": "1000",
    "type": "prepaid"
  }
}
```

الخادم يتحقق من حدود العملية، ثم يحجز المبلغ، ثم ينفذ `mtn`.

## 35. حالة الاستعلام

الخدمات من النوع `query` أو `catalog` يجب أن تكون:

`requires_balance=false`

ولا ينتج عنها قيد حجز.

## 36. اختبارات إلزامية قبل الإنتاج

### مالية

- شحن عميل.
- خصم خدمة ناجحة.
- خدمة Pending ثم Success.
- خدمة Pending ثم Ban.
- Network Failure.
- تكرار نفس Idempotency-Key.
- تحويل بين عميلين.
- هدية.
- تحويل لنفس الحساب.
- رصيد غير كافٍ.

### مزود

- Token صحيح.
- transid رقمي فريد.
- GET query.
- POST form للكهرباء والماء.
- `resultCode=0`.
- `resultCode=-2`.
- `10xx`.
- webhook `done`.
- webhook `ban`.
- backpass خاطئ.

### ألعاب

- كل GameProduct له `external_code/uniqcode`.
- playerid.
- zoneid عند الحاجة.
- mobile/email حسب المنتج.
- منع تعديل كود اللعبة من التطبيق.

## 37. الملفات التي تمت إضافتها في هذا الفرع

### `backend/services/unified_wallet.py`

جسر بين محفظة المحاسبة والمحفظة القديمة في Finance. المحاسبة هي المصدر الحقيقي، وFinance Projection للتوافق.

### `backend/services/management/commands/import_legacy_catalog.py`

أداة لاستيراد مجموعات الألعاب ووحداتها والبطاقات من SQL القديم إلى نماذج الخدمات الجديدة.

## 38. ما هو جاهز حاليًا في الفرع

جاهز بدرجة جيدة:

- طبقات Service/Category/ProviderConnection/ProviderLink.
- ServiceDistribution لاختيار الربطية.
- ProviderClient لعقد Sanaacash.
- Token generation.
- transid فريد.
- ServiceTransaction.
- ServiceTask queue.
- Pending/status handling.
- Webhook authentication.
- حجز وتسوية ورد الأموال للخدمات.
- كتالوج يمن موبايل ويو وسبأفون والخدمات الموجودة في عقد PDF.
- API موحد للخدمات.
- APIs للمحاسبة والتحويلات والهدايا.

## 39. ما يجب اعتباره فجوة قبل إعلان Production Ready

1. توحيد كل مسارات المحفظة القديمة والجديدة وعدم السماح لأي endpoint بتعديل `finance.Wallet.balance` مباشرة.
2. ربط كل عملية Gift قديمة بالقيد المحاسبي، بما في ذلك المسار القديم `/api/gifts/`.
3. تشغيل أمر استيراد الكتالوج القديم على نسخة SQL الفعلية، ثم مراجعة 224 مجموعة لعبة و2541 وحدة.
4. استكمال بيانات البطاقات الرقمية وأسعارها إذا كانت غير موجودة في المصدر الخارجي؛ لا يمكن اختراع أسعار غير موجودة في الملف.
5. استكمال/اختبار جميع ServiceDistribution للبيئة الحقيقية.
6. تشغيل Worker باستمرار في الإنتاج.
7. إضافة اختبارات تكامل فعلية مع المزود أو sandbox قبل الإنتاج.
8. التحقق من إعداد `SERVICES_WEBHOOK_BASE_URL` في الخادم.
9. تشغيل `makemigrations/migrate` بعد تثبيت التغييرات على الخادم.
10. اختبار اتساق كشف الحساب مع رصيد التطبيق بعد كل نوع عملية.

## 40. معيار القبول النهائي

لا يعتبر النظام جاهزًا نهائيًا إلا إذا نجح السيناريو التالي كاملًا:

```text
Client
  ↓
Authenticated API
  ↓
Service Catalog
  ↓
Select Item
  ↓
Service Request
  ↓
Validate
  ↓
Accounting Reserve
  ↓
Queue
  ↓
ProviderLink
  ↓
Sanaacash
  ↓
Success / Pending / Failure
  ↓
Webhook أو Status Check
  ↓
Settlement أو Refund
  ↓
Journal
  ↓
Updated Customer Balance
  ↓
Client Transaction History
```

إذا انقطع الإنترنت في أي نقطة، يجب أن يستطيع الخادم معرفة العملية وإكمالها أو تحويلها للمراجعة دون إنشاء خصم مزدوج أو رد خاطئ.

## 41. الخلاصة التنفيذية

التصميم الصحيح ليس نسخ قاعدة النظام القديم كما هي، بل تحويل منطقه إلى طبقات:

```text
Legacy Provider Contract
        ↓
ProviderConnection / ProviderLink
        ↓
Service / ServiceField / ServiceOption
        ↓
ServiceTransaction
        ↓
ServiceTask
        ↓
Accounting Wallet
        ↓
JournalEntry
```

والتطبيق يصبح عميلًا رقيقًا Thin Client: يعرض ما يأتيه من الخادم ويرسل أوامر المستخدم فقط.

بهذا الشكل يمكن تغيير مزود أو إضافة باقة أو لعبة أو ربطية جديدة من الخادم دون إصدار نسخة جديدة من تطبيق العميل.
