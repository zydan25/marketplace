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

تتوفر لوحة المدير على `/admin/`، وتبدأ واجهة REST من `/api/`. يمكن تغيير قاعدة البيانات من خلال `DB_ENGINE` و`DB_NAME` في متغيرات البيئة، مع استخدام SQLite افتراضيًا.

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

يمكن تشغيل هذا الـ backend على **Render Free Web Service** ليعمل عند وصول الطلبات فقط. خدمة Render المجانية تدخل في وضع السكون بعد **15 دقيقة** من دون حركة واردة، ثم تستيقظ تلقائيًا عند وصول طلب HTTP جديد أو اتصال WebSocket جديد، وقد يستغرق الاستيقاظ حوالي دقيقة. لذلك قد يكون أول طلب بعد السكون أبطأ من الطلبات التالية.

> **تنبيه مهم جدًا مع SQLite:** نظام ملفات Render للخدمة المجانية مؤقت (ephemeral). أي تغييرات على `db.sqlite3` أو الملفات المحلية قد تضيع عند إعادة التشغيل أو إعادة النشر أو الدخول في وضع السكون. لذلك لا تعتمد على قاعدة SQLite داخل Render المجاني كمخزن دائم للبيانات.

إعداد الخدمة المقترح:

```text
Repository: zydan25/marketplace
Branch: feat/erp-style-unified-admin-pages-2026-09
Root Directory: backend
Runtime: Python 3
Build Command: pip install -r requirements.txt && python manage.py collectstatic --noinput
Pre-Deploy Command: python manage.py migrate --noinput
Start Command: gunicorn config.wsgi:application
```

المتغيرات الضرورية:

```text
DJANGO_DEBUG=0
DJANGO_SECRET_KEY=<ضع مفتاحًا سريًا قويًا>
DJANGO_ALLOWED_HOSTS=<اسم-خدمة-render>.onrender.com
DJANGO_TIME_ZONE=Asia/Aden
DB_ENGINE=django.db.backends.sqlite3
DB_NAME=db.sqlite3
```

لا يحتاج التشغيل إلى `REDIS_URL`. عند عدم وجوده يستخدم Django ذاكرة محلية للتخزين المؤقت، وإذا أضيف `REDIS_URL` لاحقًا فسيتم استخدام Redis/Valkey تلقائيًا.

## استرجاع النسخة الأصلية عند الانتقال من Render إلى الخادم

بسبب طبيعة التخزين المؤقت في Render Free، يجب اعتبار **GitHub هو مصدر الشيفرة** واعتبار نسخة `db.sqlite3` الاحتياطية هي مصدر بيانات SQLite التي تريد الاحتفاظ بها.

### 1. استرجاع الشيفرة على الخادم

```bash
git clone -b feat/erp-style-unified-admin-pages-2026-09 https://github.com/zydan25/marketplace.git
cd marketplace/backend
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
```

### 2. استرجاع قاعدة SQLite الأصلية

احتفظ بنسخة احتياطية من قاعدة البيانات قبل نقل التطبيق، ثم ضعها في:

```text
backend/db.sqlite3
```

مثال:

```bash
cp /path/to/db.sqlite3 ./db.sqlite3
```

إذا كانت النسخة الاحتياطية مضغوطة:

```bash
cp /path/to/db.sqlite3.backup ./db.sqlite3
```

ثم افحصها:

```bash
python manage.py check
python manage.py migrate --noinput
```

### 3. تشغيل التطبيق على الخادم

```bash
python manage.py collectstatic --noinput
gunicorn config.wsgi:application
```

### 4. للحفاظ على البيانات

لا تعتمد على قاعدة SQLite الموجودة داخل Render Free كنسخة احتياطية دائمة. قبل الانتقال إلى الخادم خذ نسخة من قاعدة البيانات المطلوبة، واحفظها خارج Render، ثم استخدم تلك النسخة لاستعادة `backend/db.sqlite3` على الخادم.

## ملاحظة إنتاجية

هذا الإصدار مصمم حاليًا ليعمل مع SQLite عند الحاجة، مع إمكانية استخدام Redis/Valkey اختياريًا. يجب في بيئة الإنتاج الفعلية الاهتمام بنسخ `db.sqlite3` احتياطيًا وبملفات `media` بشكل منفصل، لأن التخزين المحلي في Render Free غير دائم.

للمزيد من التفاصيل عن سلوك Render Free:
https://render.com/docs/free
