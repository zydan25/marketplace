from . import erp_style_dashboard as legacy


_ORIGINAL_INJECT = legacy._inject_control_script


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

  function internal(url){
    const u=new URL(url,location.origin);
    return u.origin===location.origin && (controlPrefixes.some(p=>u.pathname.startsWith(p)) || !!legacyMap[u.pathname]);
  }

  function normalize(url){
    const u=new URL(url,location.origin);
    if(legacyMap[u.pathname]){
      u.pathname=legacyMap[u.pathname];
    }
    return u.href;
  }

  function fragment(html){
    const doc=new DOMParser().parseFromString(html,'text/html');
    const main=doc.querySelector('main.content');
    if(main)return main.innerHTML;
    return doc.body ? doc.body.innerHTML : html;
  }

  function rewrite(root=document){
    root.querySelectorAll('a[href]').forEach(a=>{
      const u=new URL(a.href,location.origin);
      if(legacyMap[u.pathname]){
        a.href=legacyMap[u.pathname];
        a.dataset.controlNav='1';
      }else if(controlPrefixes.some(p=>u.pathname.startsWith(p))){
        a.dataset.controlNav='1';
      }
    });
  }

  function active(url){
    const path=new URL(url,location.origin).pathname;
    document.querySelectorAll('.nav a').forEach(a=>a.classList.remove('active'));
    document.querySelectorAll('.nav a[href]').forEach(a=>{
      const p=new URL(a.href,location.origin).pathname;
      if(p===path || (p!=='/admin/dashboard/control/' && path.startsWith(p) && p.endsWith('/')))a.classList.add('active');
    });
  }

  function ensureInventoryNav(){
    const nav=document.querySelector('.nav');
    if(!nav || nav.querySelector('[data-inventory-nav]'))return;
    const link=document.createElement('a');
    link.href='/admin/dashboard/control/inventory/';
    link.dataset.inventoryNav='1';
    link.dataset.controlNav='1';
    link.innerHTML='<span class="ico">▤</span>مخزون الفروع';
    const storeLink=[...nav.querySelectorAll('a')].find(a=>a.getAttribute('href')==='/admin/dashboard/vendors/');
    if(storeLink && storeLink.parentNode)storeLink.parentNode.insertBefore(link,storeLink.nextSibling); else nav.prepend(link);
  }

  async function load(url,push){
    const target=normalize(url);
    const r=await fetch(target,{headers:{'X-Requested-With':'XMLHttpRequest','Accept':'text/html'}});
    if(!r.ok)throw new Error('HTTP '+r.status);
    const html=await r.text();
    const box=document.querySelector('main.content');
    if(!box) return;
    box.innerHTML=fragment(html);
    rewrite(box);
    if(push)history.pushState({erpControl:true},'',r.url||target);
    else history.replaceState(history.state,'',r.url||target);
    active(r.url||target);
    ensureInventoryNav();
    window.scrollTo({top:0,behavior:'smooth'});
  }

  window.addEventListener('click',function(e){
    const a=e.target.closest('a[href]');
    if(!a || e.button!==0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey || a.target==='_blank')return;
    const href=a.href;
    if(!internal(href))return;
    e.preventDefault();
    e.stopImmediatePropagation();
    load(href,true).catch(()=>{ location.href=href; });
  },true);

  window.addEventListener('submit',function(e){
    const form=e.target.closest('form');
    if(!form)return;
    const action=form.action||location.href;
    if(!internal(action))return;
    e.preventDefault();
    e.stopImmediatePropagation();
    const method=(form.method||'get').toUpperCase();
    let target=action;
    const opts={method,headers:{'X-Requested-With':'XMLHttpRequest','Accept':'text/html'}};
    if(method==='GET'){
      const qs=new URLSearchParams(new FormData(form));
      target=action+(qs.toString()?'?'+qs.toString():'');
    }else{
      opts.body=new FormData(form);
    }
    fetch(normalize(target),opts).then(async r=>{
      if(!r.ok)throw new Error('HTTP '+r.status);
      const html=await r.text();
      const box=document.querySelector('main.content');
      if(box){box.innerHTML=fragment(html);rewrite(box);}
      history.pushState({erpControl:true},'',r.url||target);
      active(r.url||target);
      ensureInventoryNav();
      window.scrollTo({top:0,behavior:'smooth'});
    }).catch(()=>form.submit());
  },true);

  window.addEventListener('popstate',function(e){
    e.stopImmediatePropagation();
    load(location.href,false).catch(()=>location.reload());
  },true);

  rewrite();
  ensureInventoryNav();
})();
</script>
"""


def _inject_control_script(html):
    return _ORIGINAL_INJECT(html).replace('</body>', BRIDGE_SCRIPT + '</body>')


legacy._inject_control_script = _inject_control_script
erp_style_dashboard = legacy.erp_style_dashboard
