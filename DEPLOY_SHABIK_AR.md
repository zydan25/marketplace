# تشغيل شبيك تجريبيًا على Web ثم نشره على Contabo

هذا الدليل مخصص للنسخة الحالية على الفرع:

```text
refactor/django-marketplace-foundation
```

لا تدمج الفرع في `main` قبل اكتمال الاختبار التجريبي. في هذه المرحلة، الهدف هو تشغيل Customer Web وVendor Web مع Django ثم اختبار المسارات الأساسية من المتصفح.

## 1. جلب الفرع الصحيح

على جهاز التطوير أو الخادم:

```bash
git clone https://github.com/zydan25/marketplace.git /home/root/projects/shabik
cd /home/root/projects/shabik
git fetch origin
git checkout refactor/django-marketplace-foundation
git pull --ff-only origin refactor/django-marketplace-foundation
```

## 2. تجهيز Django

```bash
cd /home/root/projects/shabik/backend
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
python manage.py check
python manage.py migrate
```

لبيئة تجريبية يمكن تشغيل Django على:

```bash
python manage.py runserver 0.0.0.0:8000
```

## 3. تشغيل Web محليًا مع Django

في طرفية ثانية:

```bash
cd /home/root/projects/shabik
corepack enable
pnpm install --frozen-lockfile
pnpm dev
```

أمر `pnpm dev` يشغل Django وExpo Web معًا. ويستخدم Web التطوير عنوان Django المحلي `http://127.0.0.1:8000`.

## 4. بناء Web تجريبي ثابت

أنشئ متغير البيئة الذي يشير إلى Django التجريبي:

```env
EXPO_PUBLIC_DJANGO_API_URL=https://shopik.alattab.site
```

ثم:

```bash
pnpm install --frozen-lockfile
pnpm check
pnpm build:web:customer
pnpm build:web:vendor
```

النواتج:

```text
dist-web/customer
dist-web/vendor
```

لا تعتمد على القيمة الافتراضية داخل التطبيق في بيئة إنتاج؛ اضبط `EXPO_PUBLIC_DJANGO_API_URL` أثناء البناء دائمًا.

## 5. تحقق Web قبل الرفع

اختبر بالترتيب:

```text
Customer
→ التسجيل
→ الدخول
→ الرئيسية الديناميكية
→ البحث
→ الفئات
→ المنتج
→ Variant
→ السلة
→ العناوين
→ Checkout
→ إنشاء الطلب
→ محادثة كل تاجر داخل الطلب
→ الطلبات
→ الإشعارات
→ الحساب

Vendor
→ الدخول
→ Dashboard
→ المنتجات
→ المخزون
→ الطلبات
→ تفاصيل الطلب
→ الشحن والتتبع
→ محادثة العميل
→ تصميم المتجر
→ المستحقات
→ طلب السحب
```

## 6. نشر Django خلف Nginx/PM2

على Contabo يمكن تشغيل Django/Gunicorn داخليًا على `127.0.0.1:5015` كما هو موضح في ملفات `deploy/`، ثم توجيه `/api/` و`/admin/` إليه عبر Nginx.

ثبت الحزم الأساسية:

```bash
sudo apt update
sudo apt install -y git nginx python3-venv python3-dev build-essential certbot python3-certbot-nginx
```

بعد تجهيز البيئة:

```bash
cd /home/root/projects/shabik/backend
sudo -u www-data .venv/bin/python manage.py migrate
sudo -u www-data .venv/bin/python manage.py collectstatic --noinput
```

ولا تفتح منفذ Django الداخلي للعامة.

## 7. نشر Web

بعد نجاح البناء:

```bash
sudo mkdir -p /home/root/projects/shabik/dist-web
sudo chown -R www-data:www-data /home/root/projects/shabik/dist-web
```

خدم `dist-web/customer` بواسطة Nginx للموقع العام. يمكن وضع `dist-web/vendor` على نطاق/مسار منفصل إذا أردت Web Vendor مستقلًا.

## 8. فحص سريع بعد النشر

```bash
curl -I https://shopik.alattab.site/
curl -I https://shopik.alattab.site/api/home/
curl -I https://shopik.alattab.site/admin/
```

## 9. CI

GitHub Actions في هذا الفرع تتحقق من:

```text
Django check
Migrations
Django tests
TypeScript
Customer Web export
Vendor Web export
```

ويجب أن يظهر Workflow ناجح قبل اعتبار النسخة التجريبية قابلة للرفع النهائي.

## 10. APK لاحقًا

بعد نجاح Web فقط:

```bash
EXPO_PUBLIC_DJANGO_API_URL=https://shopik.alattab.site pnpm apk:customer
EXPO_PUBLIC_DJANGO_API_URL=https://shopik.alattab.site pnpm apk:vendor
```

لا تبن APK من نسخة لم تنجح دورة Web فيها بالكامل.
