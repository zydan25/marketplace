# دليل التشغيل والحصول على التطبيقات

## الملفات التي ستستلمها

يحتوي الملف `true-discount-marketplace-v2.zip` على تطبيق React Native وتطبيق التاجر وخادم Django داخل مجلد `backend`. كما أُنشئت حزمة منفصلة باسم `true-discount-django-server.zip` لمن يريد تشغيل خادم Django وحده.

## تشغيل خادم Django محليًا

بعد فك الضغط:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver 0.0.0.0:8000
```

لوحة الإدارة تكون على `http://127.0.0.1:8000/admin/`، وواجهة API الأساسية على `http://127.0.0.1:8000/api/`.

## تغيير رابط الخادم داخل التطبيق

يتم ضبط الرابط في متغير البيئة التالي:

```env
EXPO_PUBLIC_DJANGO_API_URL=https://your-domain.example.com
```

يجب وضع الرابط دون `/` في نهايته. بعد تغييره، تتم إعادة بناء التطبيق؛ لأن الرابط يُضمّن داخل نسخة APK عند البناء. في محاكي Android، إذا كان Django يعمل على جهاز التطوير محليًا، استخدم `http://10.0.2.2:8000`، أما الهاتف الحقيقي فيحتاج عنوان IP للجهاز داخل الشبكة أو نطاقًا عامًا HTTPS.

## بناء نسخة العميل ونسخة التاجر

بعد تثبيت Node.js وpnpm وتسجيل الدخول إلى حساب Expo/EAS:

```bash
pnpm install
pnpm run apk:customer
pnpm run apk:vendor
```

النسخة الأولى تستخدم `APP_VARIANT=customer` وتفتح تطبيق العميل، أما الثانية فتستخدم `APP_VARIANT=vendor` وتفتح بوابة التاجر مباشرة. ملف `eas.json` يحتوي ملفي البناء `customer` و`vendor` ويحدد إخراج Android من نوع APK.

إذا لم يكن EAS متاحًا، يمكن تجهيز مشروع Android محليًا عبر:

```bash
APP_VARIANT=customer npx expo prebuild --platform android
APP_VARIANT=customer npx expo run:android --variant release
```

ثم تكرر الأمر مع `APP_VARIANT=vendor`. إخراج APK المحلي يتطلب Android SDK وJDK مضبوطين على الجهاز.

## الرابط المؤقت الحالي

تم تشغيل Django مؤقتًا على الرابط التالي لاختبار API أثناء مواصلة التطوير:

`https://8000-id0885qolflwfkg80ln4e-d21a2d6a.us5.manus.computer`

تطبيق العميل للتجربة عبر الويب:

`https://8083-id0885qolflwfkg80ln4e-d21a2d6a.us5.manus.computer`

تطبيق التاجر للتجربة عبر الويب:

`https://8082-id0885qolflwfkg80ln4e-d21a2d6a.us5.manus.computer`

لوحة Django Admin:

`https://8000-id0885qolflwfkg80ln4e-d21a2d6a.us5.manus.computer/admin/`

تم وضع رابط Django في ملف `.env` داخل المشروع الحالي. هذه الروابط للتجربة وليست استضافة إنتاجية ثابتة؛ قد تتوقف عند إيقاف بيئة العمل أو انتهاء الجلسة. عند نشر Django على استضافة دائمة، غيّر `EXPO_PUBLIC_DJANGO_API_URL` إلى الرابط الجديد ثم أعد بناء APK.

## آخر تحديث للمشروع والإصلاحات

آخر Commit منشور على GitHub هو `fa078de` على الفرع `main` في مستودع [`zydan25/marketplace`](https://github.com/zydan25/marketplace). يتضمن التحديث محرر الصور الحالية للمنتج مع الحذف والاحتفاظ الانتقائي، الأصناف المتعددة بصيغة `SKU|اللون|المقاس|السعر|المخزون`، تبويب التجار، صفحة المجموعات، الفلاتر الديناميكية، البحث العربي بالهاشتاج، تثبيت زر إتمام الطلب فوق شريط التبويب، مؤشرات التمرير، وإدارة التخفيضات والشحن المجاني من شاشة إدارة الواجهة. كما يتضمن لوحة تاجر مستقلة عن واجهة العميل، وسجل العمليات والمحافظ وسندات القبض ومسار الهدية والتأكد من وجود المحفظة قبل التحويل.

## روابط APK المتاحة وحالتها

النسختان الجاهزتان حاليًا مبنيتان من Commit أقدم `682a214`، لكنهما قابلتان للتثبيت والاختبار:

| النسخة | الحالة | رابط APK |
|---|---|---|
| العميل | جاهز | [تنزيل Customer APK](https://expo.dev/artifacts/eas/gHBYur0Ocb-lbA34TNwAIg7bqvxHEGG7DdICt3sjFew.apk) |
| التاجر | جاهز | [تنزيل Vendor APK](https://expo.dev/artifacts/eas/gZVUojj1pRtLwcvjW2Jhj0cp0yKyIJlrAbt0v6gUhUg.apk) |

توجد بناءات أحدث من Commit `3450797` أُرسلت قبل استنفاد الحصة: بناء العميل `7fdb59a4` كان قيد التنفيذ، وبناء التاجر `d80d9a6c` كان في الطابور عند آخر فحص. لم يمكن إرسال بناء جديد من `fa078de` لأن حساب Expo المجاني استنفد حصة Android الشهرية، وستتجدد بعد 10 أيام وفق رسالة EAS. بعد التجدد، أو من حساب بخطة تسمح ببناء إضافي، شغّل `pnpm run apk:customer` و`pnpm run apk:vendor` من Commit `fa078de`.

## بيانات التجربة الحالية

| الدور | رقم الهاتف | كلمة المرور |
|---|---:|---|
| المدير | `777000001` | `Admin@12345` |
| التاجر | `777000002` | `Vendor@12345` |
| العميل | `777000003` | `Customer@12345` |

## فحوصات آخر تحديث

تم التحقق من نجاح `pnpm check` دون أخطاء TypeScript، و`python3 manage.py check` دون أخطاء Django، واستجابة واجهة العميل والتاجر HTTP 200. كما تم اختبار تعديل المنتج مع الأصناف المتعددة، حذف المنتج HTTP 204، البحث العربي بالهاشتاج، رسالة التحويل عند رقم غير موجود، الروابط المطلقة لصور المنتجات، عرض الأصناف في تفاصيل المنتج، و`/api/home/` مع إعدادات التخفيض والشحن.

## المسار الموصى به للإنتاج

للاستخدام الفعلي، يجب تشغيل Django على استضافة دائمة مع PostgreSQL وHTTPS وتخزين للصور، ثم ضبط `DJANGO_SECRET_KEY` و`DJANGO_ALLOWED_HOSTS` و`CORS_ALLOWED_ORIGINS`. لا ينبغي استخدام SQLite أو الرابط المؤقت في الإنتاج.
