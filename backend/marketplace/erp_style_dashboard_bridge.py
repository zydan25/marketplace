from . import erp_style_dashboard as legacy


_ORIGINAL_INJECT = legacy._inject_control_script
RESPONSIVE_CSS = "/static/marketplace/erp-control-responsive.css?v=20260917-5"


FORCE_MOBILE_CSS = r"""
<style data-erp-force-mobile>
@media (max-width:900px){
  html,body{width:100%;max-width:100%;overflow-x:hidden!important}
  .main,.content{width:100%!important;max-width:100%!important;min-width:0!important}
  .content{padding:14px 10px!important}
  .content > *{max-width:100%!important;min-width:0!important}
  .content .v4-head,.content .ov-head,.content .st6-head,.content .sv-hero,.content .sd6-hero{width:100%!important;min-width:0!important}
  .content .v4-grid,.content .ov-stats,.content .st6-kpis,.content .sv-kpis,.content .sd6-kpis,.content .cg-stats{grid-template-columns:1fr 1fr!important;min-width:0!important}
  .content .v4-filter,.content .ov-filter,.content .st6-filter,.content .cg-tools{grid-template-columns:1fr!important;min-width:0!important}
  .content .v4-grid{grid-template-columns:1fr!important}
  .content .v4-product,.content .v4-card,.content .ov-card,.content .st6-card,.content .sv-card,.content .sd6-card,.content .cg-card,.content .vr-card,.content .iv-card,.content .ap-card,.content .pm-card{width:100%!important;min-width:0!important;max-width:100%!important}
  .content .v4-menu,.content .ov-actions,.content .st6-actions,.content .sv-actions,.content .sd6-actions{width:100%!important;min-width:0!important;flex-wrap:wrap!important}
  .content .v4-menu a,.content .st6-btn,.content .sv-btn,.content .sd6-btn,.content .ov-link{min-width:0!important;max-width:100%!important}
  .content .v4-media{height:170px!important}
  .content .v4-body{padding:10px!important}
  .content .v4-title{font-size:14px!important;line-height:1.45!important;overflow-wrap:anywhere}
  .content .v4-meta{font-size:9px!important;line-height:1.45!important;overflow-wrap:anywhere}
  .content .v4-row{align-items:flex-start!important;flex-direction:column!important}
  .content .v4-price{font-size:15px!important}
  .content table{width:100%!important;max-width:100%!important}
  .content .table-wrap,.content .sv-scroll,.content .sd6-scroll,.content .st6-table-wrap,.content .cg-scroll,.content .ov-scroll,.content .ap-scroll,.content .vr-scroll,.content .iv-scroll,.content .pm-scroll{width:100%!important;max-width:100%!important;min-width:0!important}
  .content .st6-table,.content .sv-table,.content .sd6-table,.content .cg-table,.content .ov-table,.content .ap-table,.content .vr-table,.content .iv-table,.content .pm-table{width:100%!important;min-width:0!important}
  .content .st6-table thead,.content .sv-table thead,.content .sd6-table thead,.content .cg-table thead,.content .ov-table thead,.content .ap-table thead,.content .vr-table thead,.content .iv-table thead,.content .pm-table thead{display:none!important}
  .content .st6-table tbody,.content .sv-table tbody,.content .sd6-table tbody,.content .cg-table tbody,.content .ov-table tbody,.content .ap-table tbody,.content .vr-table tbody,.content .iv-table tbody,.content .pm-table tbody{display:grid!important;gap:8px!important}
  .content .st6-table tr,.content .sv-table tr,.content .sd6-table tr,.content .cg-table tr,.content .ov-table tr,.content .ap-table tr,.content .vr-table tr,.content .iv-table tr,.content .pm-table tr{display:grid!important;grid-template-columns:1fr 1fr!important;gap:6px 10px!important;margin:0!important;padding:10px!important;border:1px solid #e2e8f0!important;border-radius:12px!important;background:#fff!important;box-shadow:0 5px 14px rgba(15,23,42,.04)!important}
  .content .st6-table td,.content .sv-table td,.content .sd6-table td,.content .cg-table td,.content .ov-table td,.content .ap-table td,.content .vr-table td,.content .iv-table td,.content .pm-table td{display:flex!important;flex-direction:column!important;min-width:0!important;white-space:normal!important;border:0!important;padding:2px 0!important;text-align:right!important;font-size:11px!important;line-height:1.4!important;overflow-wrap:anywhere}
  .content .st6-table td::before,.content .sv-table td::before,.content .sd6-table td::before,.content .cg-table td::before,.content .ov-table td::before,.content .ap-table td::before,.content .vr-table td::before,.content .iv-table td::before,.content .pm-table td::before{font-size:8px!important;font-weight:800!important;color:#94a3b8!important;margin-bottom:2px!important}
  .content form{max-width:100%!important;min-width:0!important}
  .content input,.content select,.content textarea{max-width:100%!important;min-width:0!important;box-sizing:border-box!important}
  .content .sv-grid,.content .sd6-grid,.content .cg-grid{grid-template-columns:1fr!important;min-width:0!important}
  .content [style*="grid-template-columns"]{min-width:0!important}
}
@media (max-width:500px){
  .content{padding:12px 8px!important}
  .content .v4-stats,.content .ov-stats,.content .st6-kpis,.content .sv-kpis,.content .sd6-kpis,.content .cg-stats{grid-template-columns:1fr 1fr!important;gap:5px!important}
  .content .st6-table tr,.content .sv-table tr,.content .sd6-table tr,.content .cg-table tr,.content .ov-table tr,.content .ap-table tr,.content .vr-table tr,.content .iv-table tr,.content .pm-table tr{grid-template-columns:1fr!important;padding:8px!important}
  .content .v4-media{height:150px!important}
}
</style>
"""

BRIDGE_SCRIPT = r"""
<script>
(function(){
  const controlPrefixes=['/admin/dashboard/control/'];
  const legacyMap={
    '/admin/dashboard/catalog/':'/admin/dashboard/control/products/',
    '/admin/dashboard/resource/categories/':'/admin/dashboard/control/categories/',
    '/admin/dashboard/resource/variants/':'/admin/dashboard/control/variants/',
    '/admin/dashboard/vendors/':'/admin/dashboard/control/stores/',
    '/admin/dashboard/vendors/applications/':'/admin/dashboard/control/applications/',
    '/admin/dashboard/orders/':'/admin/dashboard/control/orders/',
    '/admin/dashboard/resource/payments/':'/admin/dashboard/control/payments/',
    '/admin/dashboard/finance/':'/admin/dashboard/control/finance/'
  };
  const workspaceNav=[
    ['/admin/dashboard/control/categories/','▦','التصنيفات العامة'],
    ['/admin/dashboard/control/stores/','▣','المتاجر'],
    ['/admin/dashboard/control/products/','◆','المنتجات'],
    ['/admin/dashboard/control/variants/','◇','المتغيرات'],
    ['/admin/dashboard/control/inventory/','▤','مخزون الفروع'],
    ['/admin/dashboard/control/orders/','⌑','الطلبات'],
    ['/admin/dashboard/control/applications/','◌','طلبات المتاجر'],
    ['/admin/dashboard/control/payments/','▤','المدفوعات'],
    ['/admin/dashboard/control/finance/','◈','مالية التجار']
  ];
  function internal(url){const u=new URL(url,location.origin);return u.origin===location.origin&&(controlPrefixes.some(p=>u.pathname.startsWith(p))||!!legacyMap[u.pathname]);}
  function normalize(url){const u=new URL(url,location.origin);if(legacyMap[u.pathname])u.pathname=legacyMap[u.pathname];return u.href;}
  function ensureViewport(){let meta=document.querySelector('meta[name="viewport"]');if(!meta){meta=document.createElement('meta');meta.name='viewport';document.head.appendChild(meta);}meta.content='width=device-width,initial-scale=1,viewport-fit=cover';}
  function ensureResponsiveStyles(){let link=document.querySelector('link[data-erp-control-style]');if(!link){link=document.createElement('link');link.rel='stylesheet';link.href=RESPONSIVE_CSS;link.dataset.erpControlStyle='1';document.head.appendChild(link);}else{link.href=RESPONSIVE_CSS;}return link;}
  function keepResponsiveStylesLast(){const link=ensureResponsiveStyles();if(link&&link.parentNode===document.head)document.head.appendChild(link);let force=document.querySelector('style[data-erp-force-mobile]');if(!force){const holder=document.createElement('div');holder.innerHTML=FORCE_MOBILE_CSS;force=holder.firstElementChild;document.head.appendChild(force);}else if(force.parentNode===document.head){document.head.appendChild(force);}}
  function styleKey(css){let h=5381;for(let i=0;i<css.length;i++)h=((h<<5)-h)+css.charCodeAt(i)|0;return'erp-control-'+(h>>>0).toString(36);}
  function adoptStyles(doc){doc.querySelectorAll('style').forEach(style=>{const css=style.textContent||'';if(!css.trim()){style.remove();return;}const key=styleKey(css);if(!document.head.querySelector('style[data-control-style="'+key+'"]')){const adopted=document.createElement('style');adopted.setAttribute('data-control-style',key);adopted.textContent=css;document.head.appendChild(adopted);}style.remove();});keepResponsiveStylesLast();}
  function fragment(html){const doc=new DOMParser().parseFromString(html,'text/html');adoptStyles(doc);const main=doc.querySelector('main.content');return main?main.innerHTML:(doc.body?doc.body.innerHTML:html);}
  function rewrite(root=document){root.querySelectorAll('a[href]').forEach(a=>{const u=new URL(a.href,location.origin);if(legacyMap[u.pathname]){a.href=legacyMap[u.pathname];a.dataset.controlNav='1';}else if(controlPrefixes.some(p=>u.pathname.startsWith(p)))a.dataset.controlNav='1';});}
  function active(url){const path=new URL(url,location.origin).pathname;document.querySelectorAll('.nav a').forEach(a=>a.classList.remove('active'));document.querySelectorAll('.nav a[href]').forEach(a=>{const p=new URL(a.href,location.origin).pathname;if(p===path||(p!=='/admin/dashboard/control/'&&path.startsWith(p)&&p.endsWith('/')))a.classList.add('active');});}
  function closeMobileMenu(){if(window.innerWidth<=900&&typeof window.toggleMenu==='function')window.toggleMenu(false);}
  function ensureWorkspaceNav(){const nav=document.querySelector('.nav');if(!nav)return;workspaceNav.forEach(([href,icon,label])=>{const exists=[...nav.querySelectorAll('a[href]')].some(a=>{try{return new URL(a.href,location.origin).pathname===href;}catch(e){return false;}});if(exists)return;const link=document.createElement('a');link.href=href;link.dataset.workspaceHref=href;link.dataset.controlNav='1';link.innerHTML='<span class="ico">'+icon+'</span>'+label;nav.appendChild(link);});}
  async function load(url,push){closeMobileMenu();const target=normalize(url);const r=await fetch(target,{headers:{'X-Requested-With':'XMLHttpRequest','Accept':'text/html'}});if(!r.ok)throw new Error('HTTP '+r.status);const html=await r.text();const box=document.querySelector('main.content');if(!box)throw new Error('main.content missing');box.innerHTML=fragment(html);rewrite(box);keepResponsiveStylesLast();if(push)history.pushState({erpControl:true},'',r.url||target);else history.replaceState(history.state,'',r.url||target);active(r.url||target);ensureWorkspaceNav();closeMobileMenu();window.scrollTo({top:0,behavior:'smooth'});}
  window.addEventListener('click',function(e){const a=e.target.closest('a[href]');if(!a||e.button!==0||e.metaKey||e.ctrlKey||e.shiftKey||e.altKey||a.target==='_blank')return;if(!internal(a.href))return;e.preventDefault();e.stopImmediatePropagation();load(a.href,true).catch(()=>{location.href=a.href;});},true);
  window.addEventListener('submit',function(e){const form=e.target.closest('form');if(!form)return;const action=form.action||location.href;if(!internal(action))return;e.preventDefault();e.stopImmediatePropagation();closeMobileMenu();const method=(form.method||'get').toUpperCase();let target=action;const opts={method,headers:{'X-Requested-With':'XMLHttpRequest','Accept':'text/html'}};if(method==='GET'){const qs=new URLSearchParams(new FormData(form));target=action+(qs.toString()?'?'+qs.toString():'');}else opts.body=new FormData(form);fetch(normalize(target),opts).then(async r=>{if(!r.ok)throw new Error('HTTP '+r.status);const html=await r.text(),box=document.querySelector('main.content');if(box){box.innerHTML=fragment(html);rewrite(box);keepResponsiveStylesLast();}history.pushState({erpControl:true},'',r.url||target);active(r.url||target);ensureWorkspaceNav();closeMobileMenu();window.scrollTo({top:0,behavior:'smooth'});}).catch(()=>form.submit());},true);
  window.addEventListener('popstate',function(){load(location.href,false).catch(()=>location.reload());},true);
  ensureViewport();ensureResponsiveStyles();rewrite();ensureWorkspaceNav();active(location.href);keepResponsiveStylesLast();
})();
</script>
"""


def _inject_control_script(html):
    html = _ORIGINAL_INJECT(html)
    if '</head>' in html:
        html = html.replace('</head>', '<link rel="stylesheet" data-erp-control-style href="' + RESPONSIVE_CSS + '"></head>', 1)
    return html.replace('</body>', BRIDGE_SCRIPT + '</body>')


legacy._inject_control_script = _inject_control_script
erp_style_dashboard = legacy.erp_style_dashboard
