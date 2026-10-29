import {BANNERS,BANNER_ART,BANNER_THEMES,validateBanners} from './banners.mjs';
import {BannerSelection,loadBannerArt} from './banner-selection.mjs';

// Mount once; selection updates never replace the return button or focused option.
export function mountGachaView(root,onReturn,{banners=BANNERS,assets=BANNER_ART,effects=()=>!document.body.classList.contains('reduced')&&!matchMedia('(prefers-reduced-motion: reduce)').matches}={}){
 const validated=validateBanners(banners,assets),doc=root.ownerDocument;
 root.innerHTML=`<header class="gacha-heading"><p class="eyebrow">RHYTHM STAGE / COLLECTION</p>
 <h1 id="gacha-title" tabindex="-1">GACHA<span aria-hidden="true">.</span></h1>
 <p>세 가지 색으로 만나는 무대 · 무료 시뮬레이션 디자인 미리보기</p></header>
 <div class="gacha-panel ui-panel" id="gacha-content">
 <div class="gacha-banner-layout"><section class="gacha-picker" aria-label="배너 선택"><p class="gacha-list-label">STAGE SELECT <span></span></p><div class="gacha-banner-list" role="group" aria-label="디자인 배너"></div></section>
 <section class="gacha-feature" aria-labelledby="gacha-banner-title"><div class="gacha-feature-copy"><p class="gacha-badge"></p><h2 id="gacha-banner-title"></h2><p class="gacha-subtitle"></p></div>
 <div class="gacha-visual"><span class="gacha-fallback" aria-hidden="true">◇</span><div class="gacha-image" aria-hidden="true"></div></div></section></div>
 <p class="gacha-config-note" hidden>일부 미리보기를 표시할 수 없어 기본 도형으로 안내합니다.</p>
 <div class="gacha-bottom"><p>독창적인 도형으로 만든 임시 배너입니다.<br>현재는 디자인 선택만 제공됩니다.</p><button type="button" class="gacha-return ui-button ui-button--accent">곡 선택으로 돌아가기 <span aria-hidden="true">↗</span></button></div>
 <p class="gacha-live" aria-live="polite" aria-atomic="true"></p></div>`;
 const q=s=>root.querySelector(s),list=q('.gacha-banner-list'),feature=q('.gacha-feature'),imageHost=q('.gacha-image'),fallback=q('.gacha-fallback'),returnButton=q('.gacha-return');
 const buttons=new Map(),failedThumbnails=new Set();let animation=null,visible=false;
 q('.gacha-list-label span').textContent=String(validated.banners.length).padStart(2,'0')+' / PREVIEW';
 q('.gacha-config-note').hidden=!validated.errors.length;
 for(const banner of validated.banners){
  const button=doc.createElement('button');button.type='button';button.className='gacha-banner-button';button.dataset.bannerId=banner.id;button.setAttribute('aria-pressed','false');
  const thumb=doc.createElement('span');thumb.className='gacha-thumbnail';thumb.dataset.theme=BANNER_THEMES[banner.themeKey];thumb.setAttribute('aria-hidden','true');thumb.textContent='◇';
  const src=assets[banner.artKey]?.thumbnailSrc;
  if(src){const img=doc.createElement('img');img.alt='';img.onerror=()=>{failedThumbnails.add(img);if(visible)img.remove();};img.src=src;thumb.append(img);}
  const copy=doc.createElement('span');copy.className='gacha-option-copy';
  const title=doc.createElement('strong');title.textContent=banner.title;
  const label=doc.createElement('small');label.textContent=banner.previewLabel;
  const selected=doc.createElement('span');selected.className='gacha-selected';selected.textContent='✓ 선택됨';selected.hidden=true;
  copy.append(title,label,selected);button.append(thumb,copy);list.append(button);buttons.set(banner.id,{button,selected});
 }
 const cancelMotion=()=>{animation?.cancel();animation=null;};
 const keepInList=button=>{ // Never scroll the entire document when selecting a banner.
  const a=list.getBoundingClientRect(),b=button.getBoundingClientRect();
  if(list.scrollWidth>list.clientWidth)list.scrollLeft+=b.left<a.left?b.left-a.left:b.right>a.right?b.right-a.right:0;
 };
 const selection=new BannerSelection({banners:validated.banners,assets,loadArt:loadBannerArt,onSelect(banner,changed){
  cancelMotion();imageHost.replaceChildren();fallback.hidden=false;
  for(const [id,{button,selected}] of buttons){const active=id===banner?.id;button.setAttribute('aria-pressed',String(active));selected.hidden=!active;}
  feature.dataset.bannerId=banner?.id??'';feature.dataset.theme=banner?BANNER_THEMES[banner.themeKey]:'mint';
  q('.gacha-badge').textContent=banner?.previewLabel??'디자인 미리보기';
  q('#gacha-banner-title').textContent=banner?.title??'준비된 배너가 없습니다';
  q('.gacha-subtitle').textContent=banner?.subtitle??'곡 선택으로 돌아가 리듬게임을 계속할 수 있어요.';
  if(banner)keepInList(buttons.get(banner.id).button);
  if(changed){q('.gacha-live').textContent=banner.title+' 선택됨';
   const value=getComputedStyle(feature).getPropertyValue('--ui-normal').trim();
   const duration=parseFloat(value)*(value.endsWith('ms')?1:1000)||0;
   if(effects()&&duration)animation=feature.animate([{opacity:.5,transform:'translateY(4px)'},{opacity:1,transform:'translateY(0)'}],{duration,easing:'cubic-bezier(.2,.8,.2,1)'});
  }
 },onArt(image){if(image){image.alt='';imageHost.replaceChildren(image);fallback.hidden=true;}}});
 const choose=e=>{const button=e.target.closest('[data-banner-id]');if(button&&list.contains(button))selection.select(button.dataset.bannerId);};
 list.addEventListener('click',choose);returnButton.addEventListener('click',onReturn);
 return {errors:validated.errors,get selectedBannerId(){return selection.selectedBannerId;},
  setVisible(value){visible=value;if(!visible)cancelMotion();else{for(const img of failedThumbnails)img.remove();failedThumbnails.clear();}selection.setVisible(visible);},
  syncMotion(){if(!effects())cancelMotion();},
  destroy(){visible=false;cancelMotion();selection.destroy();list.removeEventListener('click',choose);returnButton.removeEventListener('click',onReturn);for(const img of list.querySelectorAll('img'))img.onerror=null;failedThumbnails.clear();root.replaceChildren();}
 };
}
