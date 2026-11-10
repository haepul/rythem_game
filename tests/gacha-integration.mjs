// Explicit test-only instrumentation. Never loaded by the game entry point.
const $=id=>document.getElementById(id),key='rhythm-next-day13-fixture';
const native={setTimeout:window.setTimeout.bind(window),clearTimeout:window.clearTimeout.bind(window),add:EventTarget.prototype.addEventListener,remove:EventTarget.prototype.removeEventListener,animate:Element.prototype.animate,matchMedia:window.matchMedia.bind(window)};
const sleep=ms=>new Promise(resolve=>native.setTimeout(resolve,ms));
const timers=new Set(),listeners=new Set();
window.setTimeout=(fn,ms,...args)=>{let id=native.setTimeout(()=>{timers.delete(id);fn(...args);},ms);timers.add(id);return id;};
window.clearTimeout=id=>{timers.delete(id);native.clearTimeout(id);};
EventTarget.prototype.addEventListener=function(type,fn,options){const capture=typeof options==='boolean'?options:!!options?.capture;if(fn&&![...listeners].some(x=>x.target===this&&x.type===type&&x.fn===fn&&x.capture===capture))listeners.add({target:this,type,fn,capture});return native.add.call(this,type,fn,options);};
EventTarget.prototype.removeEventListener=function(type,fn,options){const capture=typeof options==='boolean'?options:!!options?.capture;for(const x of listeners)if(x.target===this&&x.type===type&&x.fn===fn&&x.capture===capture)listeners.delete(x);return native.remove.call(this,type,fn,options);};
const simulatedMotion=new EventTarget();simulatedMotion.matches=false;simulatedMotion.media='(prefers-reduced-motion: reduce)';
window.matchMedia=query=>query===simulatedMotion.media?simulatedMotion:native.matchMedia(query);
let animationFault=false;
Element.prototype.animate=function(...args){if(animationFault)throw Error('DAY13 simulated WAAPI failure');return native.animate.apply(this,args);};
const [{mountGachaView},{createWalletStore},{createDrawService},{inventoryModel},{bannerRewards},{createExchangeService}]=await Promise.all([
 import('../next-stage/gacha/view.mjs?v=20261108-day13'),import('../next-stage/gacha/wallet-storage.mjs?v=20261108-day13'),import('../next-stage/gacha/draw-service.mjs?v=20261108-day13'),import('../next-stage/gacha/inventory-model.mjs?v=20261108-day13'),import('../next-stage/gacha/acquisition-history.mjs?v=20261108-day13'),import('../next-stage/gacha/exchange-service.mjs?v=20261108-day13')]);
let readsFail=false,writesFail=false,afterWrite=false,writes=0,rolls=0,confirms=0,autoNext=false,phaseHook=null,readyHook=null;
const store=createWalletStore({key,locks:navigator.locks,storage:{getItem(k){if(readsFail)throw Error('fixture read');return localStorage.getItem(k);},setItem(k,v){if(writesFail)throw new DOMException('fixture quota','QuotaExceededError');localStorage.setItem(k,v);writes++;if(afterWrite)throw Error('fixture accepted write then throw');}}});
const service=createDrawService({store,rng:()=>{rolls++;return .99;}}),confirm=service.confirm;service.confirm=()=>{confirms++;return confirm();};
const root=$('gacha-screen');let view;
const leave=()=>{view.setVisible(false);root.hidden=true;$('outside').hidden=false;$('outside').querySelector('h2').focus();};
view=mountGachaView(root,leave,{walletStore:store,drawService:service,effects:()=>$('effects').checked&&!simulatedMotion.matches,introOptions:{beforeStage:phase=>phaseHook?.(phase)},revealOptions:{beforeCard:(_card,context)=>readyHook?.(context)}});
const enter=()=>{root.hidden=false;$('outside').hidden=true;view.setVisible(true);};
function setMotion(value){simulatedMotion.matches=value;$('reduce').checked=value;simulatedMotion.dispatchEvent(new Event('change'));}
function publish(data){$('report').textContent=JSON.stringify(data,null,2);}
function snapshot(){const s=store.snapshot;return {writes,rolls,confirms,error:s.error,balance:s.wallet?.balance,receipts:s.wallet?.receipts.length,exchanges:s.wallet?.exchanges.length,cards:s.wallet?inventoryModel(s.wallet).total:null,stickers:s.wallet?bannerRewards(s.wallet,'demo-mint').balance:null,dom:root.querySelectorAll('*').length,animations:document.getAnimations().filter(a=>a.playState==='running'||a.playState==='pending').length,timers:timers.size,listeners:listeners.size};}
async function seed(raw){view.closeDialogs();service.cancel();readsFail=writesFail=afterWrite=animationFault=false;phaseHook=readyHook=null;setMotion(false);$('effects').checked=true;await navigator.locks.request(key+':transaction',()=>localStorage.setItem(key,raw??JSON.stringify({schemaVersion:1,balance:3000,claimedGrantIds:['test-crystals-v1']})));store.refresh();service.cancel();enter();}
const wait=async predicate=>{const end=performance.now()+15000;while(!predicate()){if(performance.now()>end)throw Error('fixture timeout');await sleep(20);}};
const click=s=>{const el=root.querySelector(s);if(!el||el.disabled)throw Error('not actionable '+s);el.click();};
const saved=()=>JSON.stringify(store.snapshot.wallet);
async function draw(count=10){click(`[data-count="${count}"]`);click('[data-confirm]');await wait(()=>!service.snapshot.busy);}
async function result(){await wait(()=>root.querySelector('.gacha-draw-dialog[data-stage=result]')?.open&&!root.querySelector('.gacha-reveal-next'));}
const observer=new MutationObserver(()=>{if(autoNext){const next=root.querySelector('.gacha-reveal-next');if(next&&!next.disabled)native.setTimeout(()=>{if(autoNext&&next.isConnected&&!next.disabled)next.click();},80);}});observer.observe(root,{subtree:true,childList:true,attributes:true,attributeFilter:['disabled']});
async function measure(){
 await seed();autoNext=true;const frames=[],longTasks=[];let running=true,last=null;const sample=t=>{if(!running)return;if(last!==null)frames.push(t-last);last=t;requestAnimationFrame(sample);};
 const po=new PerformanceObserver(list=>longTasks.push(...list.getEntries().map(e=>e.duration)));try{po.observe({type:'longtask'});}catch{}
 await sleep(250);const before=snapshot(),start=performance.now();requestAnimationFrame(sample);await draw();await result();running=false;autoNext=false;po.disconnect();await sleep(250);const elapsed=performance.now()-start,after=snapshot();
 click('.gacha-draw-dialog .gacha-dialog-close');click('.gacha-details');click('dialog[open] .gacha-dialog-close');await sleep(50);const cycleStart=snapshot();for(let i=0;i<20;i++){leave();enter();click('.gacha-details');click('dialog[open] .gacha-dialog-close');await sleep(0);}await sleep(300);const cycleEnd=snapshot();
 const ordered=frames.slice().sort((a,b)=>a-b),percentile=p=>ordered[Math.min(ordered.length-1,Math.floor(ordered.length*p))]??null;
 publish({kind:'performance',userAgent:navigator.userAgent,viewport:[innerWidth,innerHeight],dpr:devicePixelRatio,elapsedMs:elapsed,frames:frames.length,p50Ms:percentile(.5),p95Ms:percentile(.95),maxMs:Math.max(...frames),longTasks,before,after,cycleStart,cycleEnd,note:'One production-duration 10-card presentation; fixture auto Next 80ms. Listener/timer bookkeeping instrumented; no heap/physical-device claim.'});
}
async function regress(){const checks=[];const check=(name,ok,extra={})=>checks.push({name,ok,...extra});
 await seed();click('[data-count="1"]');const bytes=localStorage.getItem(key),before=snapshot();click('dialog[open] .gacha-dialog-close');await sleep(30);check('cancel has no RNG/write/debit',localStorage.getItem(key)===bytes&&rolls===before.rolls&&writes===before.writes);
 click('[data-count="1"]');const button=root.querySelector('[data-confirm]');button.focus();store.refresh();check('confirmation focus survives unchanged refresh',document.activeElement===button);
 localStorage.setItem(key,'{');store.refresh();click('dialog[open] .gacha-dialog-close');await sleep(30);check('corrupt storage does not trap confirmation dialog',!root.querySelector('dialog[open]'));check('corrupt bytes preserved',localStorage.getItem(key)==='{');
 await seed();click('[data-count="10"]');const stale=root.querySelector('[data-confirm]');stale.focus();const other=createWalletStore({key,locks:navigator.locks,storage:localStorage});other.refresh();const otherDraw=createDrawService({store:other,rng:()=>0});otherDraw.prepare('demo-mint',1);await otherDraw.confirm();store.refresh();check('changed balance retains confirmation focus and blocks insufficient draw',document.activeElement===stale&&stale.disabled&&root.querySelector('dialog[open]').textContent.includes('300 크리스탈 부족'));view.closeDialogs();service.cancel();otherDraw.destroy();other.destroy();
 await seed();$('effects').checked=false;await draw();await result();click('.gacha-draw-dialog .gacha-dialog-close');click('.gacha-inventory-open');const disclosure=root.querySelector('dialog[open] summary');disclosure.click();disclosure.focus();store.refresh();check('inventory refresh retains focused expanded history',document.activeElement===disclosure&&disclosure.parentElement.open);
 const exchange=createExchangeService({store});exchange.prepare('demo-mint','test-card-006');await exchange.confirm();check('new exchange updates quantity without collapsing focused history',document.activeElement===disclosure&&disclosure.parentElement.open&&root.querySelector('dialog[open]').textContent.includes('보유 11장'));
 view.closeDialogs();const state=snapshot();for(let i=0;i<5;i++){click('[data-last]');click('.gacha-draw-dialog .gacha-dialog-close');}check('result reopen does not write/sample/debit',snapshot().writes===state.writes&&snapshot().rolls===state.rolls&&snapshot().balance===state.balance);
 await seed();$('effects').checked=false;click('[data-count="1"]');const confirmButton=root.querySelector('[data-confirm]'),old=snapshot();confirmButton.dispatchEvent(new PointerEvent('pointerup',{bubbles:true,pointerType:'touch'}));for(let i=0;i<20;i++)confirmButton.dispatchEvent(new MouseEvent('click',{bubbles:true}));await wait(()=>!service.snapshot.busy);await result();check('synthetic touch plus 20 clicks commit once',snapshot().writes===old.writes+1&&snapshot().rolls===old.rolls+2&&snapshot().balance===2700);view.closeDialogs();publish({kind:'regressions',checks});
}
async function faults(){const checks=[];const record=(name,ok)=>checks.push({name,ok});
 await seed();writesFail=true;await draw(1);record('before-save failure unchanged',store.snapshot.wallet.balance===3000&&store.snapshot.wallet.receipts.length===0);writesFail=false;await service.confirm();view.closeDialogs();service.restore();record('retry commits once',store.snapshot.wallet.balance===2700&&store.snapshot.wallet.receipts.length===1);
 for(const mode of ['accepted-throw','intro-error','reveal-error','reduce-start','reduce-intro','reduce-card','exit-intro','exit-card']){
  await seed();autoNext=true;afterWrite=mode==='accepted-throw';if(mode==='reduce-start')setMotion(true);
  phaseHook=phase=>{if(phase==='gathering'){if(mode==='intro-error')throw Error('fixture intro');if(mode==='reduce-intro')setMotion(true);if(mode==='exit-intro')native.setTimeout(leave,0);}};
  readyHook=()=>{if(mode==='reveal-error')animationFault=true;if(mode==='reduce-card')setMotion(true);if(mode==='exit-card')native.setTimeout(leave,0);};
  await draw(1);await sleep(2200);autoNext=false;animationFault=afterWrite=false;
  const committed=saved(),counts=snapshot();view.closeDialogs();leave();enter();click('[data-last]');await sleep(20);
  record(mode,saved()===committed&&counts.balance===2700&&counts.receipts===1&&snapshot().rolls===counts.rolls&&snapshot().writes===counts.writes&&!!root.querySelector('.gacha-result-card'));view.closeDialogs();
 }
 publish({kind:'faults',checks,snapshot:snapshot()});
}
for(const [id,fn] of [['seed',()=>seed()],['measure',measure],['regress',regress],['faults',faults]])$(id).onclick=async()=>{try{$(id).disabled=true;await fn();}catch(e){publish({error:e.message,snapshot:snapshot()});}finally{$(id).disabled=false;}};
$('enter').onclick=enter;$('reduce').onchange=()=>setMotion($('reduce').checked);$('effects').onchange=()=>{document.body.classList.toggle('reduced',!$('effects').checked);view.syncMotion();};
$('corrupt').onclick=()=>navigator.locks.request(key+':transaction',()=>{localStorage.setItem(key,'{');store.refresh();});
$('spend').onclick=async()=>{service.prepare('demo-mint',1);await service.confirm();publish(snapshot());};
window.addEventListener('storage',e=>{if(e.key===key)store.refresh();});enter();
