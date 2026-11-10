import {DRAW_COSTS} from './wallet-config.mjs?v=20261108-day13';
import {WALLET_ERRORS} from './wallet-storage.mjs?v=20261108-day13';
import {createDrawService,DRAW_ERRORS} from './draw-service.mjs?v=20261108-day13';
import {mountGachaDialog} from './details.mjs?v=20261108-day13';
import {buildResultModel} from './result-model.mjs?v=20261108-day13';
import {createResultView} from './result-view.mjs?v=20261108-day13';
import {createGachaPresentation,createCardRevealView} from './card-reveal.mjs?v=20261108-day13';
import {createIntroView} from './intro-view.mjs?v=20261108-day13';

export function mountDrawView(root,{store,getBanner,banners,onReturn=()=>{},service=createDrawService({store}),effects=()=>!root.ownerDocument.body.classList.contains('reduced'),introOptions={},revealOptions={}}){
 const doc=root.ownerDocument,host=doc.createElement('section');host.className='gacha-draw';host.setAttribute('aria-label','무료 시뮬레이션 추첨');
 host.innerHTML=`<p class="gacha-draw-policy">프로젝트 테스트 규칙 · 10회 보장 없음 · 현금 가치 없음</p><div class="gacha-draw-actions">${[1,10].map(n=>`<div><button type="button" class="ui-button ui-button--accent" data-count="${n}">${n}회 추첨 · ${DRAW_COSTS[n].toLocaleString('ko-KR')}</button><p data-reason="${n}"></p></div>`).join('')}</div><div class="gacha-draw-history"><button type="button" class="ui-button" data-last>마지막 결과 다시 보기</button><button type="button" class="ui-button" data-pending hidden>진행 중인 요청 확인</button></div><p class="gacha-draw-status" role="status" aria-live="polite"></p><p class="gacha-draw-error" role="alert"></p>`;
 root.querySelector('.gacha-bottom').before(host);
 let visible=false,disposed=false,awaiting=false,epoch=0,shownReceipt=null,resultModel=null,intro=null,listening=false,confirmation=null;
 const pinResult=receipt=>{shownReceipt=structuredClone(receipt);const saved=store.snapshot;
  resultModel=buildResultModel(shownReceipt,saved.error?{}:{wallet:saved.wallet});
 };
 const motion=doc.defaultView.matchMedia('(prefers-reduced-motion: reduce)');
 const enabled=()=>effects()&&!motion.matches;
 const logIntroError=e=>console.error('[gacha intro] 결과 저장은 유지됩니다.',e);
 const message=code=>DRAW_ERRORS[code]??WALLET_ERRORS[code]??'요청을 확인할 수 없습니다. 저장소를 다시 확인해 주세요.';
 const modal=mountGachaDialog(root,{titleId:'gacha-draw-title',onVisible:()=>visible,onRequestClose(){
  if(intro?.active){intro.skip();return false;}
  if(service.snapshot.busy||awaiting)return false;
  // Failed reads retain the pending request, but must not hide recovery controls
  // behind a modal that the user cannot dismiss.
  if(service.snapshot.intent){const r=service.cancel();if(r.committed)return false;}else service.acknowledge();return true;
 }});
 modal.dialog.classList.add('gacha-draw-dialog');
 const close=modal.dialog.querySelector('.gacha-dialog-close');
 const returnButton=doc.createElement('button');returnButton.type='button';returnButton.className='ui-button gacha-result-return';returnButton.textContent='곡 선택으로 돌아가기';returnButton.hidden=true;modal.dialog.append(returnButton);
 const resultView=createResultView(doc);
 const returnToLibrary=()=>{if(!visible||disposed||intro.active||awaiting||!resultModel)return;epoch++;intro.hide();modal.close(false);service.acknowledge();onReturn();};
 returnButton.addEventListener('click',returnToLibrary);
 const paragraph=text=>{const p=doc.createElement('p');p.textContent=text;return p;};
 const art=createIntroView(doc);
 const cards=createCardRevealView(doc,{onNext:()=>intro.next()});
 intro=createGachaPresentation({timing:introOptions.timing,revealTiming:revealOptions.timing,onError:logIntroError,
  onStage(phase,receipt,context){
   if(!visible||disposed||doc.hidden)return;
   if(phase==='entering'){
    modal.content.replaceChildren(art.element);modal.content.setAttribute('aria-label','저장된 결과 진입 연출');
    modal.dialog.querySelector('h2').textContent='새로운 무대';modal.dialog.setAttribute('aria-busy','false');
    close.disabled=false;close.textContent='건너뛰기';close.focus({preventScroll:true});
   }
   host.dataset.state='intro-'+phase;
   introOptions.beforeStage?.(phase); // Injectable presentation fault fixture only.
   return art.stage(phase,receipt,context);
  },
  onCard(card,context){
   if(!visible||disposed||doc.hidden)return;
   modal.content.replaceChildren(cards.element);modal.content.setAttribute('aria-label','저장된 카드 공개');
   modal.dialog.insertBefore(cards.nextButton,close);
   modal.dialog.querySelector('h2').textContent='카드 공개';close.textContent='모두 건너뛰기';
   host.dataset.state='card-reveal';close.focus({preventScroll:true});
   revealOptions.beforeCard?.(card,context);
   return cards.show(card,context);
  },
  onReady(){if(visible&&!disposed&&!doc.hidden&&modal.dialog.open)cards.ready();},
  onFinish(receipt,{present}){
   if(!resultModel||resultModel.requestId!==receipt.request.requestId)pinResult(receipt);
   if(present&&visible&&!disposed&&!doc.hidden&&modal.dialog.open){renderDialog();close.focus({preventScroll:true});}
  }
 });
 function renderDialog(){
  if(!visible||disposed||doc.hidden)return;
  cards.nextButton.remove();
  const state=service.snapshot,wallet=store.snapshot.wallet;const {intent}=state,receipt=shownReceipt??state.receipt,isResult=!!shownReceipt||state.status==='result';
  host.dataset.state=isResult?'result':state.status;
  if(isResult&&receipt){
   confirmation=null;
   if(!resultModel)pinResult(receipt);
   const entering=modal.content.firstElementChild!==resultView.element;
   modal.dialog.classList.add('gacha-result-mode');returnButton.hidden=false;
   close.disabled=false;close.textContent='확인하여 가챠로 돌아가기';modal.dialog.setAttribute('aria-busy','false');
   modal.dialog.querySelector('h2').textContent='추첨 결과';modal.content.setAttribute('role','region');modal.content.setAttribute('aria-label','저장된 추첨 결과');modal.content.tabIndex=0;
   resultView.render(resultModel,{bannerName:banners.find(b=>b.id===resultModel.bannerId)?.title,balance:wallet?.balance});
   if(entering){modal.content.replaceChildren(resultView.element);modal.content.scrollTop=0;if(modal.dialog.open)close.focus({preventScroll:true});}
   modal.dialog.dataset.stage='result';return;
  }
  modal.dialog.classList.remove('gacha-result-mode');returnButton.hidden=true;
  const wasInside=modal.dialog.contains(doc.activeElement),previous=modal.dialog.dataset.stage;
  close.disabled=state.busy;close.textContent=state.busy?'저장 처리 중…':intent?'취소':'확인';
  modal.dialog.setAttribute('aria-busy',String(state.busy));modal.content.tabIndex=0;
  modal.content.setAttribute('role','region');modal.content.setAttribute('aria-label','추첨 확인 및 결과');
  modal.dialog.querySelector('h2').textContent=isResult?'저장된 추첨 결과':'무료 시뮬레이션 추첨 확인';
  if(intent){
   const balance=wallet?.balance;
   const key=JSON.stringify(intent);
   if(confirmation?.key!==key||!modal.content.contains(confirmation.button)){
    modal.content.replaceChildren();
    const balanceText=paragraph(''),missing=paragraph(''),processing=paragraph('확정 중에는 닫기와 Escape가 잠깁니다. 화면을 떠나도 저장은 계속되며, 돌아오면 결과를 확인할 수 있습니다.'),errorText=paragraph('');errorText.setAttribute('role','alert');
    const button=doc.createElement('button');button.type='button';button.className='ui-button ui-button--accent';button.dataset.confirm='';
    modal.content.append(paragraph(banners.find(b=>b.id===intent.bannerId)?.title??intent.bannerId),paragraph(`배너 ID: ${intent.bannerId}`),paragraph(`설정: ${intent.configVersion} / ${intent.policyVersion}`),paragraph(`${intent.count}회 · 비용 ${intent.cost.toLocaleString('ko-KR')} 크리스탈`),balanceText,paragraph('프로젝트 테스트 규칙입니다. 10회는 독립 추첨이며 보장은 없습니다. 확인 직전 최신 잔액과 설정을 다시 검증합니다.'),missing,button,processing,errorText);
    confirmation={key,balanceText,missing,button,processing,errorText};
   }
   const c=confirmation;
   c.balanceText.textContent=`현재 잔액 ${balance?.toLocaleString('ko-KR')??'확인 불가'} · 예상 잔액 ${balance===undefined?'확인 불가':Math.max(0,balance-intent.cost).toLocaleString('ko-KR')}`;
   c.missing.hidden=balance===undefined||balance>=intent.cost;c.missing.textContent=c.missing.hidden?'':`${(intent.cost-balance).toLocaleString('ko-KR')} 크리스탈 부족`;
   c.button.disabled=state.busy||(balance!==undefined&&balance<intent.cost);
   c.button.textContent=state.busy?'차감·결과 저장 중…':state.status==='error'?'같은 요청으로 재시도':'확인하고 추첨';
   c.processing.hidden=!state.busy;c.errorText.textContent=state.error?message(state.error):'';
  }else{
   confirmation=null;modal.content.replaceChildren();
   if(state.error){const p=paragraph(message(state.error));p.setAttribute('role','alert');modal.content.append(p);}
  }
  modal.dialog.dataset.stage=state.status;
  if(modal.dialog.open&&((wasInside&&!modal.dialog.contains(doc.activeElement))||(state.status==='result'&&previous!=='result')))(close.disabled?modal.content:close).focus({preventScroll:true});
 }
 function render(){
  if(!visible||disposed||doc.hidden)return;
  const state=service.snapshot,saved=store.snapshot;
  if(!intro.active)host.dataset.state=state.status;
  for(const n of [1,10]){
   let configOK=true;try{service.quote(getBanner(),n);}catch{configOK=false;}
   const missing=saved.wallet?Math.max(0,DRAW_COSTS[n]-saved.wallet.balance):null;
   host.querySelector(`[data-count="${n}"]`).disabled=awaiting||intro.active||state.busy||saved.busy||!!state.intent||!saved.wallet||!saved.canWrite||!!saved.error||!!missing||!configOK;
   host.querySelector(`[data-reason="${n}"]`).textContent=!configOK?'추첨 설정을 확인할 수 없습니다.':missing?`${missing.toLocaleString('ko-KR')} 크리스탈 부족`:!saved.canWrite?'안전한 저장을 지원하는 브라우저가 필요합니다.':saved.error?'저장 상태 확인이 필요합니다.':`${n}회 · ${DRAW_COSTS[n].toLocaleString('ko-KR')} 무료 시뮬레이션 크리스탈`;
  }
  host.querySelector('[data-last]').disabled=state.busy||saved.busy||!!state.intent||!saved.wallet?.receipts.length;
  host.querySelector('[data-pending]').hidden=!state.intent;host.querySelector('[data-pending]').disabled=state.busy;
  host.querySelector('.gacha-draw-status').textContent=state.busy?'차감과 결과를 함께 저장하고 있습니다.':saved.wallet?.receipts.length?`저장된 추첨 ${saved.wallet.receipts.length}건 · 마지막 결과를 다시 볼 수 있습니다.`:'';
  host.querySelector('.gacha-draw-error').textContent=state.error?message(state.error):'';
  if(modal.dialog.open&&!awaiting&&!intro.active)renderDialog();
 }
 const show=opener=>{renderDialog();modal.open(resultModel?'추첨 결과':'무료 시뮬레이션 추첨 확인',opener);};
 const click=e=>{const target=e.target.closest('button');if(!target)return;
  if(awaiting||intro.active)return;
  if(target.dataset.count){shownReceipt=null;resultModel=null;const r=service.prepare(getBanner(),Number(target.dataset.count));if(r.ok)show(target);}
  else if(target.hasAttribute('data-last')){shownReceipt=null;resultModel=null;service.restore();if(service.snapshot.receipt){pinResult(service.snapshot.receipt);show(target);}}
  else if(target.hasAttribute('data-pending'))show(target);
 };
 const confirm=async e=>{
  if(!e.target.closest('[data-confirm]')||awaiting||intro.active)return;
  awaiting=true;const token=epoch;
  const pending=service.confirm();renderDialog();
  const result=await pending;awaiting=false;if(disposed)return;
  if(result.ok)pinResult(result.receipt);
  if(!visible||doc.hidden||!modal.dialog.open)return;
  if(!result.ok||token!==epoch){renderDialog();return;}
  try{intro.start(result.receipt,{changed:result.changed,enabled:enabled()});}
  catch(error){logIntroError(error);renderDialog();close.focus({preventScroll:true});}
 };
 const syncMotion=()=>{if(!disposed&&intro.active){try{intro.syncMotion(enabled());}catch(e){logIntroError(e);intro.skip();}}};
 const visibility=()=>{if(doc.hidden){epoch++;intro.hide();}else if(visible&&!disposed){render();}};
 const pagehide=()=>{epoch++;intro.hide();};
 function listen(on){if(on===listening)return;listening=on;
  const method=on?'addEventListener':'removeEventListener';doc[method]('visibilitychange',visibility);motion[method]('change',syncMotion);
  doc.defaultView[method]('pagehide',pagehide);
 }
 host.addEventListener('click',click);modal.content.addEventListener('click',confirm);
 const offStore=store.subscribe(render),offService=service.subscribe(render);
 return {service,refresh:render,syncMotion,closeDialogs(){epoch++;intro.hide();modal.close(false);},setVisible(value){visible=value;listen(value);if(value){shownReceipt=null;resultModel=null;service.restore();render();}else{epoch++;intro.hide();modal.close(false);}},
  destroy(){if(disposed)return;disposed=true;visible=false;epoch++;listen(false);intro.destroy();art.destroy();cards.destroy();offStore();offService();service.destroy();returnButton.removeEventListener('click',returnToLibrary);modal.destroy();host.removeEventListener('click',click);modal.content.removeEventListener('click',confirm);host.remove();}
 };
}
