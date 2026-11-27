/* Public storefront content bridge. Approved, allow-listed text and design values only.
   No API secrets, code injection, arbitrary CSS, or customer data. */
(()=>{'use strict';
const base=String(window.HP_API_BASE_URL||'').trim().replace(/\/$/,'');
if(!base)return;
const mapping={
 global:{announcement:'.strip',brand_tagline:'.logo small'},
 home:{hero_eyebrow:'#page-home .hero .eyebrow',hero_title:'#page-home .hero h1',
       hero_description:'#page-home .hero .lead',hero_primary_button:'#page-home .hero-actions [data-go="catalog"]',
       hero_secondary_button:'#page-home .hero-actions [data-go="quote"]',
       category_title:'#page-home #categories',category_description:'#page-home #categories',
       featured_title:'#page-home #featured',featured_description:'#page-home #featured'},
 catalog:{title:'#page-catalog .page-title',description:'#page-catalog .page-head p'},
 product:{proof_badge:'#page-product .previewmark',customization_tip:'#page-product #artPreview'},
 quote:{title:'#page-quote .page-title',description:'#page-quote .page-head p'},
 cart:{title:'#page-cart .page-title',description:'#page-cart .page-head p'},
 checkout:{title:'#page-checkout .page-title',description:'#page-checkout .page-head p'}
};
const fieldMappings={
 'home.category_title':()=>document.querySelector('#categories')?.closest('.section')?.querySelector('.sectionhead h2'),
 'home.category_description':()=>document.querySelector('#categories')?.closest('.section')?.querySelector('.sectionhead p'),
 'home.featured_title':()=>document.querySelector('#featured')?.closest('.section')?.querySelector('.sectionhead h2'),
 'home.featured_description':()=>document.querySelector('#featured')?.closest('.section')?.querySelector('.sectionhead p'),
 'product.customization_tip':()=>document.querySelector('#page-product .detail-info .note'),
 'global.announcement':()=>document.querySelector('.strip')
};
let saved=null;
function apply(){
 if(!saved)return;
 const pages=saved.pages||{};
 for(const [page,fields] of Object.entries(mapping)){
   const values=pages[page]?.config||{};
   for(const [key,selector] of Object.entries(fields)){
     const val=values[key];if(typeof val!=='string')continue;
     const node=(fieldMappings[page+'.'+key]||(()=>document.querySelector(selector)))();
     if(node)node.textContent=val;
   }
 }
 const glob=pages.global?.config||{},home=pages.home?.config||{},catalog=pages.catalog?.config||{};
 const root=document.documentElement;
 if(/^#[0-9a-f]{6}$/i.test(glob.primary_color||''))root.style.setProperty('--aqua',glob.primary_color);
 if(/^#[0-9a-f]{6}$/i.test(glob.accent_color||''))root.style.setProperty('--orange',glob.accent_color);
 const button=glob.button_style||'rounded';
 root.style.setProperty('--ai-button-radius',button==='pill'?'999px':button==='square'?'3px':'11px');
 root.dataset.heroLayout=['split','centered','editorial'].includes(home.hero_layout)?home.hero_layout:'split';
 root.dataset.catalogColumns=['2','3','4'].includes(catalog.columns)?catalog.columns:'3';
}
async function load(){
 try{
  const ctrl=new AbortController();
  const abort=setTimeout(()=>ctrl.abort(),12000);
  let response=await fetch(base+'/api/v1/site-content',{cache:'no-store',signal:ctrl.signal});
  clearTimeout(abort);
  if(!response.ok)return;
  saved=await response.json();
  apply();
 }catch(err){/* Keep last available page design; never block cart/order. */}
}
window.addEventListener('hashchange',()=>setTimeout(apply,0));
const observer=new MutationObserver(()=>{if(saved){clearTimeout(window.__hpCmsRefresh);window.__hpCmsRefresh=setTimeout(apply,50)}});
observer.observe(document.getElementById('page-home')||document.body,{subtree:true,childList:true});
observer.observe(document.getElementById('page-product')||document.body,{subtree:true,childList:true});
load();
})();