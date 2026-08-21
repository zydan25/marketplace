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

تم وضع الرابط في ملف `.env` داخل المشروع الحالي. هذا الرابط للتجربة وليس استضافة إنتاجية ثابتة؛ قد يتوقف عند إيقاف بيئة العمل أو انتهاء الجلسة. عند نشر Django على استضافة دائمة، غيّر `EXPO_PUBLIC_DJANGO_API_URL` إلى الرابط الجديد ثم أعد بناء APK.

## المسار الموصى به للإنتاج

للاستخدام الفعلي، يجب تشغيل Django على استضافة دائمة مع PostgreSQL وHTTPS وتخزين للصور، ثم ضبط `DJANGO_SECRET_KEY` و`DJANGO_ALLOWED_HOSTS` و`CORS_ALLOWED_ORIGINS`. لا ينبغي استخدام SQLite أو الرابط المؤقت في الإنتاج.
