// Original SVG/CSS geometry; six reusable particles, four on narrow screens.
// Deliberately independent of rarity, sampling, wallet, and audio.
export function createIntroView(doc){
 const element=doc.createElement('section');element.className='gacha-intro';
 element.innerHTML=`<p class="gacha-intro-announcement" role="status">결과 저장 완료 · 새로운 무대를 여는 중입니다.</p>
 <div class="gacha-intro-art" aria-hidden="true"><div class="gacha-intro-orbit"></div><div class="gacha-intro-symbol"><svg viewBox="0 0 160 160" focusable="false"><path d="M80 12 148 80 80 148 12 80Z" fill="#e2fbf6" stroke="#19cbbb" stroke-width="2"/><path d="m80 32 48 48-48 48-48-48Z" fill="#fff" stroke="#b8a6e9" stroke-width="1.5"/><circle cx="80" cy="80" r="14" fill="#66e9d2"/><path d="M80 60v40M60 80h40" stroke="#fff" stroke-width="2"/></svg></div></div>
 <p class="gacha-intro-phase" aria-hidden="true"></p><p class="gacha-intro-hint">결과는 이미 안전하게 저장되어 있습니다.</p>`;
 const art=element.querySelector('.gacha-intro-art'),symbol=element.querySelector('.gacha-intro-symbol'),orbit=element.querySelector('.gacha-intro-orbit');
 const offsets=[[-94,-22],[90,14],[-50,76],[54,-74],[-80,-66],[80,68]];
 const particles=offsets.map(([x,y],i)=>{const p=doc.createElement('span');p.className='gacha-intro-particle';p.style.setProperty('--px',x+'px');p.style.setProperty('--py',y+'px');p.dataset.index=String(i);art.append(p);return p;});
 let disposed=false,currentCleanup=()=>{};
 function stage(phase,_receipt,{duration,fail}){
  if(disposed)return;
  currentCleanup();
  element.dataset.phase=phase;element.querySelector('.gacha-intro-phase').textContent={entering:'무대가 열립니다',gathering:'빛이 모입니다',revealing:'결과를 확인해 보세요'}[phase];
  let cancelled=false;const animations=[];
  const cleanup=()=>{cancelled=true;for(const a of animations){try{a.cancel();}catch(e){console.error('[gacha intro] animation cleanup',e);}}animations.length=0;};
  currentCleanup=cleanup;
  const animate=(el,frames)=>{const a=el.animate(frames,{duration,easing:'cubic-bezier(.2,.7,.2,1)',fill:'both'});animations.push(a);a.finished.catch(e=>{if(!cancelled&&!disposed)fail(e);});};
  try{
   animate(symbol,phase==='entering'?[{opacity:0,transform:'translateY(12px) scale(.86)'},{opacity:1,transform:'translateY(0) scale(1)'}]:phase==='gathering'?[{opacity:1,transform:'scale(1)'},{opacity:1,transform:'scale(1.08)'}]:[{opacity:1,transform:'scale(1.08)'},{opacity:0,transform:'scale(1.2)'}]);
   animate(orbit,phase==='revealing'?[{opacity:.5,transform:'scale(1)'},{opacity:0,transform:'scale(1.22)'}]:[{opacity:.15,transform:'rotate(-12deg) scale(.9)'},{opacity:.55,transform:'rotate(0) scale(1)'}]);
   for(const [i,p] of particles.entries()){
    if(doc.defaultView.matchMedia('(max-width: 480px)').matches&&i>=4)continue;
    const [x,y]=offsets[i],to=phase==='gathering'?.62:phase==='revealing'?1.15:1;
    animate(p,[{opacity:phase==='entering'?0:.5,transform:`translate(${x}px,${y}px) rotate(45deg) scale(.65)`},{opacity:phase==='revealing'?0:.6,transform:`translate(${x*to}px,${y*to}px) rotate(45deg) scale(1)`}]);
   }
  }catch(e){cleanup();throw e;}
  return cleanup;
 }
 return {element,stage,destroy(){if(disposed)return;currentCleanup();disposed=true;}};
}
