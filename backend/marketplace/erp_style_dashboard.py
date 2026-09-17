from collections import OrderedDict
from decimal import Decimal
import re

from django.contrib.auth import get_user_model
from django.db.models import Sum
from django.http import HttpResponse
from django.shortcuts import render
from django.utils import timezone

from .control_pages import render_control_partial
from .dashboard import dashboard_access_required
from .marketplace_models import Payment, VendorApplication, VendorOrder
from .models import Category, Notification, Order, Product, StorefrontSection, VendorPayout, VendorProfile, Wallet
from services.models import (
    DigitalProduct,
    GameProduct,
    Service,
    ServiceDistribution,
    ServiceOption,
    ServiceTask,
    ServiceTransaction,
    TelecomDenomination,
    TelecomPlan,
)
from services.service_platform_v2 import PACKAGE_SERVICES
from services.settings_models import ServiceSetting


User = get_user_model()

CONTROL_SECTION_MAP = {
    "stores": "/admin/dashboard/control/stores/",
    "products": "/admin/dashboard/control/products/",
}


def _replace_inner_content(html, fragment):
    pattern = re.compile(r'(<main class="content">).*?(</main>)', re.S)
    return pattern.sub(lambda m: f"{m.group(1)}{fragment}{m.group(2)}", html, count=1)


def _inject_control_script(html):
    script = r"""
<script>
(function(){
  const map={
    '/admin/dashboard/catalog/':'/admin/dashboard/control/products/',
    '/admin/dashboard/resource/categories/':'/admin/dashboard/control/categories/',
    '/admin/dashboard/resource/variants/':'/admin/dashboard/control/variants/',
    '/admin/dashboard/vendors/':'/admin/dashboard/control/stores/',
    '/admin/dashboard/vendors/applications/':'/admin/dashboard/control/applications/',
    '/admin/dashboard/orders/':'/admin/dashboard/control/orders/',
    '/admin/dashboard/resource/payments/':'/admin/dashboard/control/payments/',
    '/admin/dashboard/finance/':'/admin/dashboard/control/finance/'
  };
  function rewriteLinks(root=document){
    root.querySelectorAll('a[href]').forEach(a=>{
      const u=new URL(a.href,location.origin), target=map[u.pathname];
      if(target){a.href=target;a.dataset.controlNav='1';}
    });
  }
  function activeNav(url){
    const path=new URL(url,location.origin).pathname;
    document.querySelectorAll('.nav a').forEach(a=>a.classList.remove('active'));
    document.querySelectorAll('.nav a[href]').forEach(a=>{
      const p=new URL(a.href,location.origin).pathname;
      if(p===path)a.classList.add('active');
    });
  }
  async function replaceContent(url,push=true){
    const r=await fetch(url,{headers:{'X-Requested-With':'XMLHttpRequest','Accept':'text/html'}});
    if(!r.ok)throw new Error('HTTP '+r.status);
    const html=await r.text(), box=document.querySelector('main.content');
    if(!box)return;
    box.innerHTML=html;
    rewriteLinks(box);
    bindInner(box);
    activeNav(url);
    if(push)history.pushState({erpControl:true},'',url);
    window.scrollTo({top:0,behavior:'smooth'});
  }
  function bindInner(root){
    root.querySelectorAll('[data-inner-modal-open]').forEach(b=>b.onclick=()=>{
      const m=document.getElementById(b.dataset.innerModalOpen);if(m)m.classList.add('open');
    });
    root.querySelectorAll('[data-inner-modal-close]').forEach(b=>b.onclick=()=>b.closest('.inner-modal,.product-modal')?.classList.remove('open'));
    root.querySelectorAll('.inner-modal,.product-modal').forEach(m=>m.onclick=e=>{if(e.target===m)m.classList.remove('open')});
  }
  rewriteLinks();
  bindInner(document);
  document.addEventListener('click',function(e){
    const a=e.target.closest('a[data-control-nav]');
    if(a && e.button===0 && !e.metaKey && !e.ctrlKey && !e.shiftKey && !e.altKey){
      e.preventDefault();replaceContent(a.href).catch(()=>location.href=a.href);return;
    }
    const close=e.target.closest('[data-inner-modal-close]');
    if(close)close.closest('.inner-modal,.product-modal')?.classList.remove('open');
  });
  document.addEventListener('submit',async function(e){
    const form=e.target.closest('[data-inner-form],[data-control-filter]');
    if(!form)return;
    e.preventDefault();
    const method=(form.method||'get').toUpperCase(), url=form.action || location.href;
    let target=url;
    if(method==='GET'){
      const qs=new URLSearchParams(new FormData(form));
      target=url+(qs.toString()?'?'+qs.toString():'');
    }
    try{
      const opts={method,headers:{'X-Requested-With':'XMLHttpRequest','Accept':'text/html'}};
      if(method!=='GET')opts.body=new FormData(form);
      const r=await fetch(target,opts);if(!r.ok)throw new Error('HTTP '+r.status);
      const html=await r.text();const box=document.querySelector('main.content');
      if(box){box.innerHTML=html;rewriteLinks(box);bindInner(box);}
      activeNav(target);history.pushState({erpControl:true},'',target);window.scrollTo({top:0,behavior:'smooth'});
    }catch(err){form.submit();}
  });
  window.addEventListener('popstate',()=>replaceContent(location.href,false).catch(()=>location.reload()));
})();
</script>"""
    return html.replace('</body>', script + '</body>')


@dashboard_access_required
def erp_style_dashboard(request):
    """Keep the existing ERP shell; only the inner workspace changes per control section."""
    now = timezone.now()
    day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    stats = {
        "products": Product.objects.count(),
        "customers": User.objects.filter(role="customer").count(),
        "stores": VendorProfile.objects.filter(status="active").count(),
        "categories": Category.objects.filter(is_active=True).count(),
        "orders": Order.objects.count(),
        "today_orders": Order.objects.filter(created_at__gte=day_start).count(),
        "today_paid": Order.objects.filter(created_at__gte=day_start, payment_status="paid").aggregate(v=Sum("total"))["v"] or Decimal("0"),
        "wallet_balance": Wallet.objects.aggregate(v=Sum("balance"))["v"] or Decimal("0"),
        "pending_applications": VendorApplication.objects.filter(status="pending").count(),
        "pending_payouts": VendorPayout.objects.filter(status__in=["pending", "approved"]).count(),
        "notifications": Notification.objects.filter(is_read=False).count(),
    }

    service_rows = Service.objects.filter(is_active=True).select_related("category__main_category").order_by(
        "category__main_category__sort_order", "category__sort_order", "sort_order", "id"
    )
    service_tree = OrderedDict()
    for service in service_rows:
        main_name = getattr(getattr(service.category, "main_category", None), "name", "الخدمات")
        cat_name = getattr(service.category, "name", "عام")
        service_tree.setdefault(main_name, OrderedDict()).setdefault(cat_name, []).append(service)

    service_counts = {
        "services": service_rows.count(),
        "settings": ServiceSetting.objects.filter(is_active=True).count(),
        "providers": ServiceTransaction.objects.values("provider_link").distinct().count(),
        "distributions": ServiceDistribution.objects.filter(is_active=True).count(),
        "plans": TelecomPlan.objects.filter(is_active=True).count(),
        "denominations": TelecomDenomination.objects.filter(is_active=True).count(),
        "games": GameProduct.objects.filter(is_active=True).count(),
        "digital": DigitalProduct.objects.filter(is_active=True).count(),
        "options": ServiceOption.objects.filter(is_active=True).count(),
    }

    package_nav = []
    for key, (provider_name, service_code, title) in PACKAGE_SERVICES.items():
        service = service_rows.filter(code=service_code).first()
        if service:
            package_nav.append({"key": key, "name": provider_name, "title": title, "service": service})

    transaction_status = OrderedDict()
    for row in ServiceTransaction.objects.values("status").annotate(total=Sum("customer_amount")).order_by("status"):
        transaction_status[row["status"] or "غير محدد"] = row["total"] or Decimal("0")

    context = {
        "now": now,
        "stats": stats,
        "service_tree": service_tree,
        "package_nav": package_nav,
        "service_counts": service_counts,
        "transaction_status": transaction_status,
        "latest_transactions": ServiceTransaction.objects.select_related("service", "customer").order_by("-created_at")[:10],
        "latest_orders": Order.objects.select_related("customer").order_by("-created_at")[:8],
        "latest_stores": VendorProfile.objects.select_related("owner").order_by("-created_at")[:8],
        "low_stock": Product.objects.filter(is_published=True, stock__lte=5).order_by("stock", "name")[:8],
        "pending_applications": VendorApplication.objects.select_related("applicant").filter(status="pending").order_by("-created_at")[:6],
        "recent_settings": ServiceSetting.objects.select_related("service").filter(is_active=True).order_by("group", "sort_order", "id")[:8],
        "recent_tasks": ServiceTask.objects.order_by("-created_at")[:8],
        "payment_summary": {
            "paid": Payment.objects.filter(status="paid").count(),
            "pending": Payment.objects.filter(status="pending").count(),
            "failed": Payment.objects.filter(status="failed").count(),
        },
        "vendor_orders": {
            "pending": VendorOrder.objects.filter(status="pending").count(),
            "processing": VendorOrder.objects.filter(status="processing").count(),
            "shipped": VendorOrder.objects.filter(status="shipped").count(),
            "delivered": VendorOrder.objects.filter(status="delivered").count(),
        },
    }

    response = render(request, "admin/erp_style_dashboard.html", context)
    html = response.content.decode("utf-8")
    screen = request.GET.get("screen", "dashboard")
    if screen in CONTROL_SECTION_MAP:
        html = _replace_inner_content(html, render_control_partial(request, screen).content.decode("utf-8"))
    response = HttpResponse(_inject_control_script(html), content_type="text/html; charset=utf-8")
    return response
