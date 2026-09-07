# Runbook تشغيل الإنتاج — Shabik / Marketplace / Services

## 1. مسار الإنتاج المعتمد

المشروع على الخادم:

```bash
/home/root/projects/shabik
```

والـDjango backend:

```bash
/home/root/projects/shabik/backend
```

إعداد PM2 الحالي يشغّل Django باسم `shabik-django` من هذا المسار، عبر `.venv/bin/gunicorn` وعلى `127.0.0.1:5015`.

## 2. قبل أي تحديث

خذ نسخة احتياطية من قاعدة البيانات واحتفظ بها خارج مسار التطبيق. لا تنفذ أي ترحيل مالي على قاعدة الإنتاج دون نسخة قابلة للاسترجاع.

```bash
cd /home/root/projects/shabik/backend
source .venv/bin/activate
python manage.py check
python manage.py makemigrations --check
python manage.py showmigrations
```

## 3. تحديث الكود من الفرع

```bash
cd /home/root/projects/shabik

git status
git fetch origin
git checkout feat/api-legacy-integration-cleanup
git pull --ff-only origin feat/api-legacy-integration-cleanup
```

إذا كان لديك تعديلات محلية، لا تستخدم `git reset --hard` قبل أخذ نسخة منها.

## 4. تحديث بيئة Python والهجرات

```bash
cd /home/root/projects/shabik/backend
source .venv/bin/activate
pip install -r requirements.txt
python manage.py check
python manage.py makemigrations --check
python manage.py migrate --plan
python manage.py migrate --noinput
```

ثم جهّز كتالوج الخدمات:

```bash
python manage.py sync_api_catalog
python manage.py verify_service_catalog --fail
python manage.py audit_service_catalog --fail
```

## 5. فحص التوجيه قبل تشغيل الخدمات

```bash
python manage.py audit_production_routes --strict
```

إذا ظهرت خدمة مدفوعة بدون ProviderConnection/ProviderLink/ServiceDistribution فعال، لا تجعلها متاحة للبيع قبل إكمال الربط.

## 6. استيراد بيانات النسخة القديمة

لا يتم حذف بيانات الكتالوج القديمة تلقائيًا. بعد توفير ملف SQL القديم:

```bash
python manage.py import_legacy_catalog --sql /path/to/legacy.sql
python manage.py normalize_legacy_catalog_hierarchy
python manage.py audit_service_catalog --fail
```

البيانات القديمة الخاصة بالألعاب تحفظ كمرجع، ولا تفعل وحدات شراء غير موثقة في عقد المزود تلقائيًا.

## 7. تشغيل Django

الإعداد المعتمد حاليًا هو PM2:

```bash
cd /home/root/projects/shabik
pm2 status
pm2 reload shabik-django --update-env
pm2 save
pm2 logs shabik-django --lines 100
```

إذا لم يكن التطبيق مسجلًا في PM2:

```bash
cd /home/root/projects/shabik
pm2 start deploy/ecosystem.config.js --only shabik-django
pm2 save
```

## 8. تشغيل Worker الخدمات

بعد تحديث الكود لأول مرة أو بعد تغيير إعدادات الـworker:

```bash
sudo /home/root/projects/shabik/deploy/install_services_worker.sh /home/root/projects/shabik/backend
sudo systemctl enable --now marketplace-services-worker.service
sudo systemctl status marketplace-services-worker.service --no-pager
sudo journalctl -u marketplace-services-worker.service -f
```

السكريبت الآن يستخدم `/home/root/projects/shabik/backend/.venv/bin/python` تلقائيًا، وليس `venv` القديم.

## 9. تحقق سريع من الخدمة

```bash
curl -i https://shopik.alattab.site/api/v2/services/catalog/
```

قد تتطلب نقطة الكتالوج Authentication حسب إعدادات البيئة؛ المهم التأكد من أن Nginx يصل إلى Gunicorn وأن الرد ليس 502/504.

## 10. اختبار السداد والاستعلام

بعد تسجيل الدخول في التطبيق:

1. افتح التسديدات.
2. اختر الشركة.
3. اختر الخدمة.
4. اختر الفئة/الباقة إن كانت الخدمة تعتمد عنصرًا.
5. أدخل رقم المشترك والحقول المطلوبة فقط.
6. نفذ الاستعلام أو السداد.
7. راقب رقم العملية وحالتها والنتيجة القادمة من الخادم.

العميل لا يفترض أن يعرف `uniqcode` أو `num` أو `packageid` الخاصة بالمزود؛ الخادم يستخرجها من العنصر المختار في الكتالوج.

## 11. ملاحظة حول العميل Android

المشروع `flutter-katolin` هو تطبيق Android Jetpack Compose. تم ربط شاشة السداد والكتالوج والألعاب والبطاقات والوايفاي والتحويل المالي بمسارات Django الجديدة، وتمت إضافة CI لبناء APK فعلي واختبارات Unit Tests.

لا تعتبر نسخة APK إنتاجية جاهزة حتى ينجح Workflow `Katolin Android CI` على آخر commit.
