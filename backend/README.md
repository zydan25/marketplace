# خادم منصة السوق متعددة التجار

هذا الجزء يضيف طبقة Django REST Framework مستقلة إلى تطبيق React Native المرفق. يدير الخادم المستخدمين، أدوار العميل والتاجر والمدير، المتاجر، المنتجات، التصميم الديناميكي، الأقسام، الطلبات، العمولات، المحافظ، الإشعارات والمحادثات.

## التشغيل المحلي

من داخل مجلد `backend`:

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver 0.0.0.0:8000
```

تتوفر لوحة المدير على `/admin/`، وتبدأ واجهة REST من `/api/`.

## قاعدة البيانات

يدعم الخادم SQLite للتطوير السريع، ويدعم PostgreSQL كقاعدة تشغيل دائمة. عند ضبط `DATABASE_URL` يستخدم Django PostgreSQL تلقائيًا. كما يبقى الاتصال القديم عبر `DB_ENGINE` و`DB_NAME` و`DB_USER` و`DB_PASSWORD` و`DB_HOST` و`DB_PORT` مدعومًا.

مثال PostgreSQL للبيئة الحالية:

```text
DATABASE_URL=postgresql://marketplace:<PASSWORD>@alattab.site:5432/marketplace
DB_SSLMODE=prefer
DB_CONNECT_TIMEOUT=10
DB_CONN_MAX_AGE=60
```

لا تضع كلمة مرور قاعدة البيانات الفعلية داخل GitHub. اضبطها كمتغير سري في الخادم أو Render.

## ترحيل SQLite إلى PostgreSQL

يوجد سكربت تحقق ونقل لمرة واحدة:

```bash
python scripts/import_sqlite_to_postgres.py
```

قبل تشغيله، يجب أن تكون `DATABASE_URL` تشير إلى قاعدة PostgreSQL الهدف وأن تكون نسخة SQLite موجودة في `backend/db.sqlite3`، أو تحدد مسارها صراحة عبر `SOURCE_SQLITE_DB`.

مثال:

```bash
export DATABASE_URL='postgresql://marketplace:<PASSWORD>@alattab.site:5432/marketplace'
export SOURCE_SQLITE_DB='/path/to/db.sqlite3'
python scripts/import_sqlite_to_postgres.py
```

السكربت:

1. يطبق migrations على PostgreSQL.
2. يرفض خلط البيانات إذا كانت قاعدة الهدف تحتوي أصلًا على بيانات تطبيقية، إلا عند تفعيل `ALLOW_NONEMPTY_TARGET=1` صراحةً.
3. يصدر بيانات Django من SQLite مع الحفاظ على المفاتيح الأساسية والعلاقات اللازمة.
4. يستبعد جداول migrations وcontent types والصلاحيات والجلسات وحسابات سجل الإدارة التي يعاد توليدها أو لا تمثل بيانات التطبيق الأساسية.
5. يعيد ضبط sequences في PostgreSQL.
6. يقارن عدد الصفوف في الجداول المشتركة بعد النقل، ويفشل بدل إعلان النجاح إذا وُجد اختلاف.

بعد نجاح الترحيل، تصبح PostgreSQL هي قاعدة البيانات الوحيدة التي يجب أن يستخدمها الـbackend في بيئة التشغيل.

## المصادقة

يستخدم التطبيق تسجيل الدخول برقم الهاتف وكلمة المرور عبر `POST /api/auth/login/`، ويعيد الخادم توكنًا يُرسل لاحقًا في ترويسة `Authorization: Token <token>`. التسجيل العام عبر `POST /api/auth/register/` ينشئ حساب عميل ومحفظة تلقائيًا. إنشاء حساب تاجر ومراجعته يتمان من لوحة المدير في النسخة الحالية.

## واجهات رئيسية

| المسار | الغرض |
|---|---|
| `/api/products/` | كتالوج المنتجات والبحث والتصفية |
| `/api/vendors/` | المتاجر النشطة وملفات التجار |
| `/api/themes/` | الهوية العامة وسمات متجر التاجر |
| `/api/storefront-sections/` | ترتيب مكونات الواجهة ومحتواها ديناميكيًا |
| `/api/orders/` | إنشاء الطلبات وتتبعها وتحديث حالتها حسب الدور |
| `/api/wallets/` | عرض المحفظة وإنشاء طلبات شحن الرصيد |
| `/api/notifications/` | إشعارات العميل والتاجر |
| `/api/conversations/` | الدعم ومحادثات الطلبات |
| `/api/admin-dashboard/` | مؤشرات الإدارة العليا |

## النشر على Render عند الحاجة فقط

يمكن تشغيل هذا الـbackend على Render، لكن قاعدة SQLite المحلية لا تصلح كمخزن بيانات دائم في بيئة تشغيل تعتمد على نظام ملفات غير دائم. لتجنب فقد البيانات، اجعل `DATABASE_URL` تشير إلى PostgreSQL الدائم بدل SQLite.

إعداد الخدمة:

```text
Repository: zydan25/marketplace
Branch: feat/erp-style-unified-admin-pages-2026-09
Root Directory: backend
Runtime: Python 3
Build Command: pip install -r requirements.txt && python manage.py collectstatic --noinput
Start Command: bash scripts/start_render.sh
```

المتغيرات الأساسية:

```text
DJANGO_DEBUG=0
DJANGO_SECRET_KEY=<ضع مفتاحًا سريًا قويًا>
DJANGO_ALLOWED_HOSTS=<اسم-خدمة-render>.onrender.com
DJANGO_TIME_ZONE=Asia/Aden
DATABASE_URL=postgresql://marketplace:<PASSWORD>@alattab.site:5432/marketplace
DB_SSLMODE=prefer
DB_CONNECT_TIMEOUT=10
DB_CONN_MAX_AGE=60
```

إذا كان PostgreSQL في خادم مستقل، يجب أن يسمح الخادم باتصالات PostgreSQL من Render على المنفذ `5432` مع إعداد جدار ناري ومصادقة مناسبة. لا تفتح PostgreSQL للعالم بلا ضوابط وصول.

### تهيئة حساب المدير تلقائيًا

يستخدم تشغيل Render الملف:

```text
scripts/bootstrap_render_admin.py
```

ويقوم `scripts/start_render.sh` بالترتيب التالي:

```text
1. migrate
2. إنشاء حساب المدير إذا لم يوجد أي مدير
3. تشغيل gunicorn
```

إذا كانت قاعدة PostgreSQL تحتوي أصلًا على مدير، فلن يقوم سكربت التهيئة بتغييره.

## استرجاع النسخة الأصلية عند الانتقال من Render إلى الخادم

بسبب طبيعة التخزين المحلي غير الدائم في بعض بيئات التشغيل، يجب اعتبار **GitHub مصدر الشيفرة** ونسخة `db.sqlite3` الاحتياطية مصدر بيانات SQLite القديمة. بعد نقل البيانات مرة واحدة إلى PostgreSQL، اجعل PostgreSQL المصدر الدائم للـbackend.

### 1. استرجاع الشيفرة على الخادم

```bash
git clone -b feat/erp-style-unified-admin-pages-2026-09 https://github.com/zydan25/marketplace.git
cd marketplace/backend
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
```

### 2. نقل SQLite إلى PostgreSQL

ضع نسخة `db.sqlite3` في مكان معروف على الخادم، ثم:

```bash
export DATABASE_URL='postgresql://marketplace:<PASSWORD>@alattab.site:5432/marketplace'
export SOURCE_SQLITE_DB='/path/to/db.sqlite3'
python scripts/import_sqlite_to_postgres.py
```

### 3. تشغيل التطبيق

```bash
python manage.py collectstatic --noinput
gunicorn --bind 0.0.0.0:8000 config.wsgi:application
```

## ملاحظة إنتاجية

PostgreSQL هو المسار الموصى به للبيانات الدائمة في الإنتاج. تبقى Redis/Valkey اختيارية حسب الحاجة، بينما الصور والملفات الموجودة في `media/` ينبغي تخزينها ونسخها احتياطيًا بشكل مستقل عن قاعدة البيانات.
