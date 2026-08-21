from django.http import HttpResponse


def landing_page(request):
    html = """
    <!doctype html>
    <html lang="ar" dir="rtl">
      <head>
        <meta charset="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <title>شبيك | شبيك لبيك طلبك بين يديك</title>
        <style>
          body { margin:0; font-family:Arial,sans-serif; background:#f6f6f6; color:#161616; }
          .wrap { max-width:900px; margin:0 auto; padding:48px 20px; }
          .hero { background:#111; color:white; border-radius:18px; padding:32px; }
          .brand { color:#ff3352; font-weight:900; letter-spacing:.4px; }
          h1 { font-size:36px; margin:12px 0; }
          p { color:#666; line-height:1.8; }
          .hero p { color:#ddd; }
          .grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(220px,1fr)); gap:14px; margin-top:18px; }
          .card { background:white; border-radius:14px; padding:20px; border:1px solid #e8e8e8; }
          a { color:#e60023; font-weight:800; text-decoration:none; }
          .pill { display:inline-block; background:#eaf8ef; color:#168451; padding:7px 12px; border-radius:100px; font-size:13px; font-weight:800; }
          footer { margin-top:24px; color:#888; font-size:13px; }
        </style>
      </head>
      <body>
        <main class="wrap">
          <section class="hero">
            <div class="brand">شبيك</div>
            <h1>شبيك لبيك، طلبك بين يديك</h1>
            <p>مرحبًا بك في شبيك، منصة السوق متعددة التجار. طلبك بين يديك، والتطبيقات تستخدم واجهات API نفسها بأمان.</p>
            <span class="pill">Django API Online</span>
          </section>
          <section class="grid">
            <div class="card"><h2>لوحة الإدارة</h2><p>إدارة العملاء والتجار والمنتجات والطلبات والأرصدة.</p><a href="/admin/">فتح لوحة Django Admin</a></div>
            <div class="card"><h2>الكتالوج</h2><p>عرض المنتجات المنشورة من واجهة REST.</p><a href="/api/products/">فتح API المنتجات</a></div>
            <div class="card"><h2>الواجهة الديناميكية</h2><p>الأقسام والبنرات التي يتحكم بها المدير والتاجر.</p><a href="/api/home/">فتح API الصفحة الرئيسية</a></div>
            <div class="card"><h2>حالة الخادم</h2><p>المصادقة والسلة والعناوين والمدن والمحافظ متاحة عبر المسار الموحد.</p><a href="/api/cities/">فحص المدن والتسعير</a></div>
          </section>
          <footer>شبيك — شبيك لبيك طلبك بين يديك. هذه الصفحة تعمل من خادمك الدائم.</footer>
        </main>
      </body>
    </html>
    """
    return HttpResponse(html)
