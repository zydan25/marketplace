# خطة تقسيم Django إلى تطبيقات متعددة — شبيك

هذه الخطة مبنية على قاعدة: **تطبيق واحد فقط في كل مرحلة**، مع عدم تغيير عقد الـAPI أو جداول قاعدة البيانات إلا عند وجود migration آمنة ومختبرة.

## قواعد النقل الإلزامية

1. ننشئ branch مستقل لكل مرحلة ولا نعدل `main` مباشرة.
2. ننقل النطاق الوظيفي كاملًا: models + migrations + admin + serializers + API/views + permissions + services + tests.
3. نحافظ على الجداول الحالية باستخدام `db_table` أو `SeparateDatabaseAndState` عند نقل model فعليًا.
4. لا نحذف جدولًا أو نعيد تسميته أثناء refactor إلا عبر migration منفصلة ومقصودة.
5. نحتفظ بطبقات compatibility مؤقتة عندما تكون هناك imports أو API paths قديمة.
6. كل مرحلة يجب أن تنجح في:
   - `python manage.py check`
   - `python manage.py makemigrations --check`
   - `python manage.py migrate --plan`
   - `python manage.py test`
   - اختبار المسارات الرئيسية المرتبطة بالمرحلة.
7. لا تبدأ المرحلة التالية قبل تثبيت نجاح المرحلة الحالية.

## ترتيب المراحل

### المرحلة 1 — Accounts
النطاق:
- User/Auth
- الأدوار والصلاحيات الأساسية
- UserPreference
- إعدادات المصادقة
- إدارة المستخدمين في Django Admin
- واجهات login/register/me

الهدف الخاص: إنشاء حدود تطبيق `accounts` بدون المساس بجدول المستخدم الحالي، ثم تنفيذ نقل concrete User في خطوة schema مستقلة ومختبرة.

### المرحلة 2 — Catalog
- Category
- Product
- ProductImage
- ProductVariant
- CatalogOption
- البحث والتصفية والهاشتاج
- Admin وAPI واختبارات الكتالوج.

### المرحلة 3 — Vendors
- VendorProfile
- VendorApplication
- عمولة التاجر
- vendor permissions
- vendor admin/API.

### المرحلة 4 — Storefront
- DesignTheme
- StorefrontSection
- StorefrontMedia
- visual builder
- ملفات وواجهات محرر المتجر
- admin.

### المرحلة 5 — Orders & Inventory
- Order
- OrderItem
- VendorOrder
- VendorOrderItem
- OrderStatusHistory
- InventoryReservation
- دورة الطلب بالكامل.

### المرحلة 6 — Finance
- Wallet
- WalletTransaction
- Payment
- VendorLedgerEntry
- VendorPayout
- CouponRedemption
- CurrencyRate
- VendorCityShipping
- القيود المالية والعمليات غير القابلة للحذف.

### المرحلة 7 — Communication & Support
- Notification
- Conversation
- Message
- OrderChat
- OrderChatMessage
- Support endpoints/admin.

### المرحلة 8 — Promotions & Customer Utilities
- Coupon
- Referral
- GiftTransfer
- Address
- Loan
- أي ميزات مساعدة مرتبطة بالعميل.

### المرحلة 9 — Admin/Dashboard cleanup
بعد اكتمال نقل الدومينات:
- إزالة الـlegacy views.
- إزالة monkey patch من `apps.py`.
- توحيد permissions.
- توحيد Admin API.
- توحيد Dashboard data source.
- إضافة الصفحات الإدارية الناقصة.
- إضافة E2E للوحة الإدارة والمحرر.

## تعريف نهاية المشروع

في النهاية يكون `marketplace` غير موجود كـ"god app"، ويصبح مجرد مشروع/configuration layer، بينما كل domain مملوك لتطبيق Django واضح مع API وAdmin وtests ومهاجراته.
