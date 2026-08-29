# خطة تقسيم Django إلى تطبيقات متعددة — شبيك

هذه الخطة مبنية على قاعدة: **تطبيق واحد فقط في كل مرحلة**، مع عدم تغيير عقد الـAPI أو جداول قاعدة البيانات إلا عند وجود migration آمنة ومختبرة.

## قواعد النقل الإلزامية

1. ننشئ branch مستقل لكل مرحلة ولا نعدل `main` مباشرة.
2. ننقل النطاق الوظيفي كاملًا: models + migrations + admin + serializers + API/views + permissions + services + tests + واجهات HTML الإدارية الخاصة بالدومين.
3. نحافظ على الجداول الحالية باستخدام `db_table` أو `SeparateDatabaseAndState` عند نقل model فعليًا.
4. لا نحذف جدولًا أو نعيد تسميته أثناء refactor إلا عبر migration منفصلة ومقصودة.
5. نحتفظ بطبقات compatibility مؤقتة عندما تكون هناك imports أو API paths قديمة.
6. كل مرحلة يجب أن تنجح في:
   - `python manage.py check`
   - `python manage.py makemigrations --check`
   - `python manage.py migrate --plan`
   - `python manage.py test marketplace <app>`
   - اختبار المسارات الرئيسية المرتبطة بالمرحلة.
7. لا تبدأ المرحلة التالية قبل تثبيت نجاح المرحلة الحالية.
8. نجاح CI وحده لا يكفي؛ الصفحات الإدارية الخاصة بكل تطبيق يجب أن تكون لها اختبارات HTTP/Template على الأقل، وتضاف اختبارات متصفح عند الحاجة.

## ترتيب المراحل

### المرحلة 1 — Accounts ✅ مكتملة ومندمجة
النطاق:
- User/Auth
- الأدوار والصلاحيات الأساسية
- UserPreference
- إعدادات المصادقة
- إدارة المستخدمين في Django Admin
- login/register/me
- `/api/preferences/`
- مركز HTML عربي مستقل لإدارة الحسابات

تم نقل النطاق تدريجيًا باستخدام Proxy Models وطبقات توافق، مع عدم تغيير `AUTH_USER_MODEL` أو الجدول الفيزيائي للمستخدم.

### المرحلة 2 — Catalog ✅ جاهزة بعد نجاح CI
النطاق:
- Category
- Product
- ProductImage
- ProductVariant
- CatalogOption
- PriceGroup
- البحث والتصفية
- الصور والمعرض والصورة الرئيسية
- إدارة الأصناف والمخزون المحجوز/المتاح
- Admin وAPI واختبارات الكتالوج
- Dashboard HTML عربي مستقل عن Django Admin.

ما تم في المرحلة:
- إنشاء `backend/catalog` كتطبيق Django مستقل.
- إنشاء Proxy Models فوق الجداول الحالية، دون إنشاء جداول بيانات جديدة.
- نقل ملكية API الفعلية للمنتجات والفئات والأصناف والصور والخيارات ومجموعات الأسعار إلى `catalog` مع الحفاظ على المسارات العامة.
- توفير `/api/variants/` و`/api/product-images/` و`/api/price-groups/` كواجهات مستقلة.
- إضافة `catalog/tree` للواجهة الأمامية.
- إنشاء Admin خاص بالكتالوج.
- إنشاء مركز HTML عربي متجاوب يشمل الإحصاءات، المنتجات، الفئات، الخيارات، مجموعات الأسعار، الإضافة، التعديل، الصور، الأصناف، النشر/الإخفاء، الترند، الإجراءات الجماعية والتصدير CSV.
- إضافة طبقات توافق للملفات القديمة بدل حذفها فجأة.
- إزالة monkey patch الخاص بكتالوج المنتجات من `marketplace.apps`.
- ربط الروابط الإدارية القديمة بمركز Catalog الجديد.
- توسيع اختبارات Catalog لتغطي API والصلاحيات وواجهة الإدارة ومسارات الصور والأصناف والإجراءات الجماعية.

الحد الآمن المقصود:
- لا ننقل الجداول الفيزيائية في هذه المرحلة. نقل app label للموديلات الحقيقية سيؤجل إلى عمليات migration مستقلة بعد استقرار جميع الدومينات المرتبطة.

### المرحلة 3 — Vendors
- VendorProfile
- VendorApplication
- عمولة التاجر
- vendor permissions
- vendor admin/API
- Dashboard HTML خاص بالتجار.

### المرحلة 4 — Storefront
- DesignTheme
- StorefrontSection
- StorefrontMedia
- visual builder
- ملفات وواجهات محرر المتجر
- admin
- Dashboard HTML/Builder ownership واضح.

### المرحلة 5 — Orders & Inventory
- Order
- OrderItem
- VendorOrder
- VendorOrderItem
- OrderStatusHistory
- InventoryReservation
- دورة الطلب بالكامل
- Dashboard HTML للطلبات والمخزون.

### المرحلة 6 — Finance
- Wallet
- WalletTransaction
- Payment
- VendorLedgerEntry
- VendorPayout
- CouponRedemption
- CurrencyRate
- VendorCityShipping
- القيود المالية والعمليات غير القابلة للحذف
- Dashboard HTML مالي كامل.

### المرحلة 7 — Communication & Support
- Notification
- Conversation
- Message
- OrderChat
- OrderChatMessage
- Support endpoints/admin
- Dashboard HTML للدعم والتواصل.

### المرحلة 8 — Promotions & Customer Utilities
- Coupon
- Referral
- GiftTransfer
- Address
- Loan
- الميزات المساعدة المرتبطة بالعميل
- Dashboard HTML خاص بها.

### المرحلة 9 — Admin/Dashboard cleanup
بعد اكتمال نقل الدومينات:
- إزالة الـlegacy views.
- إزالة طبقات compatibility التي لم تعد مطلوبة.
- توحيد permissions.
- توحيد Admin API.
- توحيد Dashboard data source.
- إضافة الصفحات الإدارية الناقصة.
- إضافة E2E للوحة الإدارة والمحرر.
- تحويل `marketplace` إلى compatibility layer مؤقتة ثم تنظيفها أخيرًا.

## تعريف نهاية المشروع

في النهاية تكون كل domain رئيسية مملوكة لتطبيق Django واضح مع API وAdmin وواجهة HTML إدارية واختبارات ومهاجرات، بينما لا يبقى `marketplace` كـgod app. أي نقل للبنية الفيزيائية لجدول المستخدم أو جداول مركزية أخرى يجب أن يكون عملية migration مستقلة ومختبرة، وليس جزءًا من إعادة ترتيب الملفات.
