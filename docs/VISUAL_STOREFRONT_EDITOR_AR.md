# محرر واجهة المتجر البصري

## ما أصبح متاحًا
المحرر طبقة إدارة مرئية فوق `StorefrontSection` لتغيير الصفحة الرئيسية أو متجر التاجر بدون إصدار APK جديد.

### المدير
- يرى الأقسام العامة وأقسام جميع المتاجر.
- ينشئ قسمًا جديدًا ويحدد نوعه.
- يعدّل العنوان، الصورة، النص الفرعي، الزر، الرابط، الظهور والترتيب.
- يضيف بطاقات داخل القسم عبر قائمة بطاقات منظمة.
- يسحب الأقسام لإعادة ترتيبها.
- يستخدم معاينة هاتف داخل لوحة Django.

### التاجر
- يدخل إلى نفس المحرر بحسابه.
- يرى أقسام متجره فقط.
- ينشئ ويعدل ويرتب أقسام متجره.
- لا يستطيع رؤية أو تعديل أقسام متجر آخر أو أقسام المنصة العامة.

## الوصول
من Django Admin: Storefront Sections → «فتح المحرر».

المسار المباشر للمدير/التاجر:
`/admin/marketplace/storefront-editor/`

## أنواع الأقسام المسموحة
`hero`, `banner`, `category`, `product_grid`, `trend`, `tab`.

## عقد المحتوى
المفاتيح المرئية الأساسية:
- `image_url`
- `subtitle`
- `button_label`
- `target_url`
- `cards`

مثال:
```json
{
  "image_url": "/media/storefront/hero.webp",
  "subtitle": "تشكيلة الموسم",
  "button_label": "تسوق الآن",
  "target_url": "/collection?category=new",
  "cards": [
    {
      "title": "فساتين",
      "image_url": "/media/storefront/dresses.webp",
      "target_url": "/collection?category=dresses"
    }
  ]
}
```

## الواجهة العميلة
العميل يقرأ `/api/home/` ويعرض الأقسام الظاهرة بالترتيب. لذلك تغيير الصورة أو النص أو الزر أو الرابط أو إخفاء القسم من Django لا يحتاج إصدار APK جديد.

## قواعد responsive
- Scroll عمودي رئيسي واحد في الصفحة.
- القوائم الأفقية تستخدم فقط للـtabs والدوائر والعناصر التي تحتاج تمريرًا أفقيًا.
- لا توجد fixed widths للبطاقات.
- المعاينة تستخدم عرض هاتف لتقليل أخطاء التصميم قبل Web/APK.

## الأمن
- كل تعديل يمر عبر ownership check.
- التاجر محدود بمتجره.
- إعدادات القسم يجب أن تكون JSON object.
- أنواع الأقسام محصورة في allowlist.
- الروابط الداخلية أو الخارجية يجب أن تمر بمراجعة قواعد الرابط قبل التوسع النهائي لمنع بروتوكولات غير آمنة.

## الاختبارات
`backend/marketplace/tests/test_storefront_editor.py` يغطي:
- إنشاء قسم عام بواسطة الإدارة.
- إنشاء قسم خاص بالتاجر.
- تعديل القسم العام بواسطة الإدارة.
- تعديل التاجر لقسمه فقط.
- منع تعديل متجر آخر.
- منع العميل من الوصول للمحرر.
- منع section types غير معروفة.
- رفض config غير الصالح.

## قبل الإنتاج
```bash
cd backend
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py migrate
python manage.py test marketplace
cd ..
pnpm check
```

ثم اختبر Web customer وWeb vendor، وبعدها Android customer وAndroid vendor، خصوصًا Hero وCards والصور والروابط والترتيب والإخفاء والتمرير على عرض هاتف ضيق.