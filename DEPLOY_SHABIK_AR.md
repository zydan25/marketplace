# نشر شبيك على Contabo Ubuntu

هذا الدليل ينقل المشروع من روابط التجربة المؤقتة إلى خادم دائم على النطاق `shopik.alattab.site`. سيعمل Django/Gunicorn محليًا على `127.0.0.1:5015`، بينما يستقبل Nginx طلبات HTTPS على المنفذ 443 ويوجه طلبات `/api/` و`/admin/` إلى Django، ويخدم واجهة العميل المصدرة من Expo Web.

> لا يمكن تنفيذ أوامر الخادم على Contabo من داخل هذه الجلسة لأن بيانات SSH لم تُقدم. الملفات الجاهزة موجودة في مجلد `deploy/` ويمكن نسخها مباشرة إلى الخادم.

## 1. تجهيز DNS

في لوحة DNS الخاصة بالنطاق، أنشئ سجلًا من نوع `A` للاسم `shopik.alattab.site` يشير إلى عنوان IPv4 لخادم Contabo. أضف `www` كسجل `CNAME` إلى `shopik.alattab.site` أو كسجل `A` إلى العنوان نفسه. انتظر حتى ينتشر DNS، ثم تحقق من الخادم:

```bash
dig +short shopik.alattab.site
```

يجب أن يعيد عنوان خادم Contabo.

## 2. تثبيت الحزم الأساسية

نفذ على Contabo:

```bash
sudo apt update
sudo apt install -y git nginx python3-venv python3-dev build-essential certbot python3-certbot-nginx
```

## 3. تنزيل المشروع وتجهيز Django

استخدم مسارًا قياسيًا يسهل على `www-data` الوصول إليه:

```bash
sudo mkdir -p /var/www
sudo git clone https://github.com/zydan25/marketplace.git /var/www/shabik
sudo chown -R www-data:www-data /var/www/shabik
cd /var/www/shabik/backend
sudo -u www-data python3 -m venv .venv
sudo -u www-data .venv/bin/pip install --upgrade pip
sudo -u www-data .venv/bin/pip install -r requirements.txt
```

أنشئ ملف البيئة:

```bash
sudo cp /var/www/shabik/deploy/backend.env.production.example /var/www/shabik/backend/.env.production
sudo nano /var/www/shabik/backend/.env.production
```

غيّر `DJANGO_SECRET_KEY` إلى قيمة عشوائية طويلة وفريدة. لا تضع المفتاح في GitHub ولا ترسله في محادثة عامة.

أنشئ قاعدة البيانات والملفات الثابتة:

```bash
cd /var/www/shabik/backend
sudo -u www-data bash -lc 'set -a; source .env.production; set +a; .venv/bin/python manage.py migrate'
sudo -u www-data bash -lc 'set -a; source .env.production; set +a; .venv/bin/python manage.py collectstatic --noinput'
sudo chown -R www-data:www-data /var/www/shabik/backend
```

إذا كانت قاعدة البيانات الحالية موجودة على الخادم القديم، انسخ ملف `db.sqlite3` إلى `/var/www/shabik/backend/db.sqlite3` قبل تشغيل `migrate`، ثم اضبط الملكية إلى `www-data`.

## 4. تشغيل Django على المنفذ 5015 باستخدام PM2

ثبت PM2 عالمياً (إذا لم يكن مثبتاً):

```bash
sudo npm install -g pm2
```

شغل الخادم باستخدام ملف الإعدادات المجهز:

```bash
cd /var/www/shabik/deploy
pm2 start ecosystem.config.js
pm2 save
pm2 startup
```

اختبر Django محليًا على الخادم:

```bash
curl -I http://127.0.0.1:5015/
pm2 logs shabik-django --lines 50
```

## 5. بناء واجهة الويب

ثبت Node.js وpnpm إن لم يكونا مثبتين، ثم ابنِ نسخة العميل من داخل مجلد المشروع. ملف `.env` في آخر Commit مضبوط على `https://shopik.alattab.site`، وهو الرابط الذي سيُضمّن داخل JavaScript عند البناء:

```bash
cd /var/www/shabik
corepack enable
pnpm install --frozen-lockfile
pnpm check
pnpm build:web:customer
```

سيتم إنشاء `dist-web/customer`. انسخها إلى مسار خدمة الويب:

```bash
sudo mkdir -p /var/www/shabik/dist-web/customer
sudo chown -R www-data:www-data /var/www/shabik/dist-web
```

إذا كان البناء على الخادم نفسه، لا حاجة لنسخ إضافي. وبالنسبة إلى نسخة التاجر المنفصلة للويب، يمكن تنفيذ:

```bash
pnpm build:web:vendor
```

لكن التطبيق الموحد لواجهة الموقع يستطيع توجيه التاجر إلى `/vendor` بعد تسجيل الدخول، لذلك تكفي نسخة العميل للموقع العام، بينما تبقى نسخة التاجر المنفصلة مخصصة لـ APK.

## 6. إعداد Nginx

انسخ الإعداد الجاهز:

```bash
sudo cp /var/www/shabik/deploy/shopik.alattab.site.nginx /etc/nginx/sites-available/shopik.alattab.site
sudo ln -sfn /etc/nginx/sites-available/shopik.alattab.site /etc/nginx/sites-enabled/shopik.alattab.site
sudo nginx -t
```

في حال وجود إعداد قديم للنطاق نفسه، أوقف الرابط الرمزي القديم أو استبدله قبل إعادة التحميل. لا تشغل إعدادين لنفس `server_name`.

## 7. إصدار أو تجديد شهادة HTTPS

إذا كانت الشهادة الحالية صالحة للمجال، احتفظ بمساراتها الموجودة في الملف. وإلا نفذ بعد التأكد من DNS وفتح المنفذين 80 و443:

```bash
sudo certbot --nginx -d shopik.alattab.site -d www.shopik.alattab.site
sudo nginx -t
sudo systemctl reload nginx
```

ثم اختبر:

```bash
curl -I https://shopik.alattab.site/
curl -I https://shopik.alattab.site/api/home/
curl -I https://shopik.alattab.site/admin/
```

## 8. الجدار الناري

إذا كان UFW مفعّلًا:

```bash
sudo ufw allow OpenSSH
sudo ufw allow 'Nginx Full'
sudo ufw enable
sudo ufw status
```

لا تفتح المنفذ 5015 للعامة؛ يجب أن يبقى Django مستمعًا على `127.0.0.1:5015` وتصل إليه Nginx داخليًا فقط.

## 9. تحديث APK لاحقًا

بعد نجاح الموقع الدائم، رابط API داخل APK الجديد يجب أن يكون:

```env
EXPO_PUBLIC_DJANGO_API_URL=https://shopik.alattab.site
```

بناء نسخة العميل والتاجر من حساب Expo:

```bash
cd /var/www/shabik
pnpm run apk:customer
pnpm run apk:vendor
```

بناء APK يتطلب حصة EAS متاحة. النسخ القديمة ستظل تشير إلى رابط التجربة السابق حتى يتم إعادة بنائها؛ لا يمكن تغيير رابط API داخل APK موجود بعد تنزيله.

## 10. التشغيل والصيانة

للتحديثات اللاحقة:

```bash
cd /var/www/shabik
sudo -u www-data git pull origin main
cd backend
sudo -u www-data bash -lc 'set -a; source .env.production; set +a; .venv/bin/pip install -r requirements.txt; .venv/bin/python manage.py migrate; .venv/bin/python manage.py collectstatic --noinput'
pm2 restart shabik-django
cd ..
pnpm install --frozen-lockfile
pnpm build:web:customer
sudo nginx -t && sudo systemctl reload nginx
```

خذ نسخًا احتياطية منتظمة من `backend/db.sqlite3` ومجلد `backend/media/` قبل أي تحديث. للاستخدام التجاري الكبير، انقل قاعدة البيانات إلى PostgreSQL والتخزين إلى مساحة ملفات مستقلة بدل SQLite المحلي.
