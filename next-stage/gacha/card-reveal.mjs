import {createIntroSequence} from './intro-sequence.mjs?v=20261108-day13';
import {revealTheme,REVEAL_TIMING} from './reveal-theme.mjs?v=20261108-day13';

const freeze=value=>{if(value&&typeof value==='object'){Object.values(value).forEach(freeze);Object.freeze(value);}return value;};
// Sole owner of intro -> card reveal -> final result. No sampling or persistence.
export function createGachaPresentation({onStage=()=>{},onCard=()=>{},onReady=()=>{},onFinish=()=>{},onError=()=>{},timing,revealTiming=REVEAL_TIMING,schedule=setTimeout,unschedule=clearTimeout}={}){
 let run=null,serial=0,disposed=false;
 const report=e=>{try{onError(e);}catch{}};
 function clean(r){if(r.timer!==null){unschedule(r.timer);r.timer=null;}const fn=r.cleanup;r.cleanup=null;try{fn?.();}catch(e){report(e);}}
 function finish(r,reason,present=true){
  if(!r||r.done||run!==r)return;
  r.done=true;clean(r);r.intro?.hide();
  try{onFinish(r.receipt,{reason,present,id:r.id});}catch(e){report(e);}
 }
 function card(r,index){
  if(disposed||r.done||run!==r)return;
  clean(r);r.index=index;r.phase='card';r.ready=false;
  const token=++r.cardToken;
  const current=()=>!disposed&&run===r&&!r.done&&r.cardToken===token;
  const fail=e=>{if(current()){report(e);finish(r,'error');}};
  try{
   const duration=revealTiming.card;
   if(!Number.isFinite(duration)||duration<0)throw Error('Invalid reveal timing');
   const cleanup=onCard(r.receipt.results[index],{index,total:r.receipt.results.length,duration,fail});
   if(!current()){cleanup?.();return;}
   r.cleanup=cleanup;
   r.timer=schedule(()=>{if(!current()||r.ready)return;r.timer=null;clean(r);r.ready=true;try{onReady(index,r.receipt.results.length);}catch(e){fail(e);}},duration);
  }catch(e){fail(e);}
 }
 return {
  get active(){return !!run&&!run.done;},get state(){return !run?'idle':run.done?'finished':run.phase;},
  start(receipt,{changed=true,enabled=true}={}){
   if(disposed)return false;
   finish(run,'replaced',false);
   if(!receipt?.request?.requestId||!Array.isArray(receipt.results))throw TypeError('A committed receipt is required');
   const r=run={id:++serial,receipt:freeze(structuredClone(receipt)),done:false,phase:'intro',index:0,cardToken:0,ready:false,timer:null,cleanup:null,intro:null};
   if(!changed||!enabled){finish(r,!changed?'restored':'reduced-motion');return true;}
   r.intro=createIntroSequence({timing,schedule,unschedule,onError:report,
    onStage:(...args)=>onStage(...args),
    onFinish:(_receipt,{reason,present})=>{
     if(run!==r||r.done||disposed)return;
     if(reason==='complete'&&r.receipt.results.length)card(r,0);else finish(r,reason,present);
    }});
   r.intro.start(r.receipt);return true;
  },
  next(){const r=run;if(!r||r.done||!r.ready||r.phase!=='card')return false;r.ready=false;
   if(r.index+1===r.receipt.results.length)finish(r,'complete');else card(r,r.index+1);return true;},
  skip(){finish(run,'skip');},hide(){finish(run,'hidden',false);},
  syncMotion(enabled){if(!enabled)finish(run,'reduced-motion');},
  destroy(){if(disposed)return;disposed=true;finish(run,'destroyed',false);run?.intro?.destroy();}
 };
}

// One reusable DOM card, one light layer, six particles (at most three mobile).
// No image lookup is required: original geometry is also the missing-art fallback.
export function createCardRevealView(doc,{onNext=()=>{}}={}){
 const element=doc.createElement('section');element.className='gacha-reveal';
 element.innerHTML=`<p class="gacha-reveal-progress" role="status" aria-live="polite" aria-atomic="true"></p>
 <div class="gacha-reveal-stage"><article class="gacha-reveal-card"><div class="gacha-reveal-light" aria-hidden="true"></div><span class="gacha-reveal-symbol" aria-hidden="true">◇</span><strong class="gacha-reveal-rarity"></strong><p class="gacha-reveal-id"></p></article></div>
 <button type="button" class="ui-button ui-button--accent gacha-reveal-next">다음 카드</button>`;
 const q=s=>element.querySelector(s),card=q('.gacha-reveal-card'),light=q('.gacha-reveal-light'),stage=q('.gacha-reveal-stage'),next=q('.gacha-reveal-next');
 const offsets=[[-105,-60],[105,60],[98,-75],[-100,72],[-75,-95],[75,95]];
 const particles=offsets.map(([x,y],i)=>{const p=doc.createElement('span');p.className='gacha-reveal-particle';p.dataset.index=String(i);p.setAttribute('aria-hidden','true');stage.append(p);return p;});
 let disposed=false,cleanup=()=>{};
 const click=()=>onNext();next.addEventListener('click',click);
 function show(result,{index,total,duration,fail}){
  if(disposed)return;
  cleanup();const theme=revealTheme(result?.rarity);
  element.dataset.rarity=theme.key;card.style.setProperty('--reveal-accent',theme.accent);card.style.setProperty('--reveal-light',theme.light);
  const id=typeof result?.cardId==='string'?result.cardId:'카드 ID 확인 불가';
  const rarity=typeof result?.rarity==='string'?result.rarity:'희귀도 확인 불가';
  q('.gacha-reveal-rarity').textContent=rarity;q('.gacha-reveal-id').textContent=id;
  q('.gacha-reveal-progress').textContent=`${index+1} / ${total} · ${rarity} · ${id}`;
  next.textContent=index+1===total?'결과 확인':'다음 카드';next.disabled=true;
  let cancelled=false;const animations=[];
  cleanup=()=>{if(cancelled)return;cancelled=true;for(const a of animations){try{a.cancel();}catch{}}animations.length=0;};
  const animate=(el,frames)=>{const a=el.animate(frames,{duration,easing:'cubic-bezier(.2,.7,.2,1)',fill:'both'});animations.push(a);a.finished.catch(e=>{if(!cancelled&&!disposed)fail(e);});};
  try{
   animate(card,[{opacity:.25,transform:'translateY(8px) scale(.96)'},{opacity:1,transform:'translateY(0) scale(1)'}]);
   if(theme.key==='R3')animate(light,[{opacity:0,transform:'translateX(-120%)'},{opacity:.45,offset:.5},{opacity:0,transform:'translateX(120%)'}]);
   else animate(light,[{opacity:0,transform:'scale(.7)'},{opacity:theme.key==='R4'?.5:.15,offset:.4},{opacity:0,transform:'scale(1.25)'}]);
   const cap=doc.defaultView.matchMedia('(max-width: 480px)').matches?3:6;
   particles.forEach((p,i)=>{p.hidden=i>=Math.min(cap,theme.particles);if(p.hidden)return;const [x,y]=offsets[i];
    animate(p,[{opacity:0,transform:`translate(${x*.75}px,${y*.75}px) rotate(45deg) scale(.5)`},{opacity:.65,offset:.4},{opacity:0,transform:`translate(${x}px,${y}px) rotate(45deg) scale(1)`}]);});
  }catch(e){cleanup();throw e;}
  return cleanup;
 }
 return {element,nextButton:next,show,ready(){if(disposed)return;next.disabled=false;next.focus({preventScroll:true});},
  destroy(){if(disposed)return;disposed=true;cleanup();next.removeEventListener('click',click);}};
}
