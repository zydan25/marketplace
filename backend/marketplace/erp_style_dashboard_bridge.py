from . import erp_style_dashboard as legacy


_ORIGINAL_INJECT = legacy._inject_control_script
RESPONSIVE_CSS = "/static/marketplace/erp-control-responsive.css?v=20260917-4"


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
  function keepResponsiveStylesLast(){const link=ensureResponsiveStyles();if(link&&link.parentNode===document.head)document.head.appendChild(link);}
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
