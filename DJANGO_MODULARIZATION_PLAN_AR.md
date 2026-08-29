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

### المرحلة 1 — Accounts
النطاق:
- User/Auth
- الأدوار والصلاحيات الأساسية
- UserPreference
- إعدادات المصادقة
- إدارة المستخدمين في Django Admin
- login/register/me
- `/api/preferences/`
- مركز HTML عربي مستقل لإدارة الحسابات

الإنجاز:
- تم إنشاء `backend/accounts` كتطبيق مستقل.
- تم وضع `User` و`UserPreference` كـProxy Models على الجداول الحالية، دون إنشاء جداول جديدة أو تغيير `AUTH_USER_MODEL`.
- تم نقل ملكية واجهات auth وpreferences إلى Accounts مع الحفاظ على نفس عناوين API.
- تم نقل UserAdmin وUserPreferenceAdmin إلى Accounts.
- تم إنشاء Dashboard عربي مستقل للحسابات يشمل الإحصاءات والبحث والتصفية والإضافة والتعديل والتفعيل/الإيقاف وتوثيق الهاتف والصلاحيات الإدارية وتغيير كلمة المرور والتفضيلات وإلغاء جلسات API والإجراءات الجماعية والتصدير CSV.
- تمت إضافة اختبارات للـAPI والـProxy Models والواجهة الإدارية والحالات الجماعية.
- تمت المحافظة على التوافق مع روابط UserAdmin القديمة.

الحد الآمن المقصود:
- نقل **concrete User** في حالة قاعدة البيانات نفسها من app label `marketplace` إلى `accounts` ليس إعادة تسمية ملفات؛ يحتاج migration state/data strategy مستقلة لأن User هو المرجع المركزي لمعظم الدومينات. لا ننفذ هذه العملية ضمن أول فصل مستقر، بل كعملية schema مستقلة بعد ثبات بقية الدومينات.

### المرحلة 2 — Catalog
- Category
- Product
- ProductImage
- ProductVariant
- CatalogOption
- البحث والتصفية والهاشتاج
- Admin وAPI واختبارات الكتالوج
- Dashboard HTML خاص بالكتالوج.

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
- إزالة monkey patch من `apps.py`.
- توحيد permissions.
- توحيد Admin API.
- توحيد Dashboard data source.
- إضافة الصفحات الإدارية الناقصة.
- إضافة E2E للوحة الإدارة والمحرر.
- تحويل `marketplace` إلى compatibility layer مؤقتة ثم تنظيفها أخيرًا.

## تعريف نهاية المشروع

في النهاية تكون كل domain رئيسية مملوكة لتطبيق Django واضح مع API وAdmin وواجهة HTML إدارية واختبارات ومهاجرات، بينما لا يبقى `marketplace` كـgod app. أي نقل للبنية الفيزيائية لجدول المستخدم أو جداول مركزية أخرى يجب أن يكون عملية migration مستقلة ومختبرة، وليس جزءًا من إعادة ترتيب الملفات.
