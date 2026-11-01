import {DRAW_COSTS} from './wallet-config.mjs?v=20261101-day7';
import {WALLET_ERRORS} from './wallet-storage.mjs?v=20261101-day7';
import {createDrawService,DRAW_ERRORS} from './draw-service.mjs?v=20261101-day7';
import {mountGachaDialog,rarityLabel} from './details.mjs?v=20261101-day7';

export function mountDrawView(root,{store,getBanner,banners,service=createDrawService({store})}){
 const doc=root.ownerDocument,host=doc.createElement('section');host.className='gacha-draw';host.setAttribute('aria-label','무료 시뮬레이션 추첨');
 host.innerHTML=`<p class="gacha-draw-policy">프로젝트 테스트 규칙 · 10회 보장 없음 · 현금 가치 없음</p><div class="gacha-draw-actions">${[1,10].map(n=>`<div><button type="button" class="ui-button ui-button--accent" data-count="${n}">${n}회 추첨 · ${DRAW_COSTS[n].toLocaleString('ko-KR')}</button><p data-reason="${n}"></p></div>`).join('')}</div><div class="gacha-draw-history"><button type="button" class="ui-button" data-last>마지막 결과 다시 보기</button><button type="button" class="ui-button" data-pending hidden>진행 중인 요청 확인</button></div><p class="gacha-draw-status" role="status" aria-live="polite"></p><p class="gacha-draw-error" role="alert"></p>`;
 root.querySelector('.gacha-bottom').before(host);
 let visible=false,disposed=false;
 const message=code=>DRAW_ERRORS[code]??WALLET_ERRORS[code]??'요청을 확인할 수 없습니다. 저장소를 다시 확인해 주세요.';
 const modal=mountGachaDialog(root,{titleId:'gacha-draw-title',onVisible:()=>visible,onRequestClose(){
  if(service.snapshot.busy)return false;
  if(service.snapshot.intent){const r=service.cancel();if(!r.ok||r.committed)return false;}else service.acknowledge();return true;
 }});
 modal.dialog.classList.add('gacha-draw-dialog');
 const close=modal.dialog.querySelector('.gacha-dialog-close');
 const paragraph=text=>{const p=doc.createElement('p');p.textContent=text;return p;};
 function renderDialog(){
  const state=service.snapshot,wallet=store.snapshot.wallet;const {intent,receipt}=state;
  const wasInside=modal.dialog.contains(doc.activeElement),previous=modal.dialog.dataset.stage;
  close.disabled=state.busy;close.textContent=state.busy?'저장 처리 중…':intent?'취소':'확인';
  modal.dialog.setAttribute('aria-busy',String(state.busy));modal.content.replaceChildren();modal.content.tabIndex=0;
  modal.content.setAttribute('role','region');modal.content.setAttribute('aria-label','추첨 확인 및 결과');
  modal.dialog.querySelector('h2').textContent=state.status==='result'?'저장된 추첨 결과':'무료 시뮬레이션 추첨 확인';
  if(state.status==='result'&&receipt){
   const r=receipt.request;
   modal.content.append(paragraph(`${banners.find(b=>b.id===r.bannerId)?.title??r.bannerId} · ${r.count}회 · ${r.cost.toLocaleString('ko-KR')} 사용`),paragraph(`확정 당시 잔액 ${receipt.balanceBefore.toLocaleString('ko-KR')} → ${receipt.balanceAfter.toLocaleString('ko-KR')} · 현재 ${wallet?.balance.toLocaleString('ko-KR')??'확인 불가'}`));
   const list=doc.createElement('ol');list.className='gacha-result-list';
   for(const card of receipt.results){const li=doc.createElement('li');li.append(paragraph(card.cardId),paragraph(rarityLabel(card.rarity)));list.append(li);}modal.content.append(list,paragraph(`배너 ${r.bannerId} · 설정 ${r.configVersion} · 요청 ${r.requestId}`));
  }else if(intent){
   const balance=wallet?.balance;
   modal.content.append(paragraph(banners.find(b=>b.id===intent.bannerId)?.title??intent.bannerId),paragraph(`배너 ID: ${intent.bannerId}`),paragraph(`설정: ${intent.configVersion} / ${intent.policyVersion}`),paragraph(`${intent.count}회 · 비용 ${intent.cost.toLocaleString('ko-KR')} 크리스탈`),paragraph(`현재 잔액 ${balance?.toLocaleString('ko-KR')??'확인 불가'} · 예상 잔액 ${balance===undefined?'확인 불가':Math.max(0,balance-intent.cost).toLocaleString('ko-KR')}`),paragraph('프로젝트 테스트 규칙입니다. 10회는 독립 추첨이며 보장은 없습니다. 확인 직전 최신 잔액과 설정을 다시 검증합니다.'));
   if(balance!==undefined&&balance<intent.cost)modal.content.append(paragraph(`${(intent.cost-balance).toLocaleString('ko-KR')} 크리스탈 부족`));
   const button=doc.createElement('button');button.type='button';button.className='ui-button ui-button--accent';button.dataset.confirm='';button.disabled=state.busy;
   button.textContent=state.busy?'차감·결과 저장 중…':state.status==='error'?'같은 요청으로 재시도':'확인하고 추첨';modal.content.append(button);
  }
  if(state.busy)modal.content.append(paragraph('확정 중에는 닫기와 Escape가 잠깁니다. 화면을 떠나도 저장은 계속되며, 돌아오면 결과를 확인할 수 있습니다.'));
  if(state.error){const p=paragraph(message(state.error));p.setAttribute('role','alert');modal.content.append(p);}
  modal.dialog.dataset.stage=state.status;
  if(modal.dialog.open&&((wasInside&&!modal.dialog.contains(doc.activeElement))||(state.status==='result'&&previous!=='result')))(close.disabled?modal.content:close).focus({preventScroll:true});
 }
 function render(){
  if(!visible||disposed)return;
  const state=service.snapshot,saved=store.snapshot;
  host.dataset.state=state.status;
  for(const n of [1,10]){
   let configOK=true;try{service.quote(getBanner(),n);}catch{configOK=false;}
   const missing=saved.wallet?Math.max(0,DRAW_COSTS[n]-saved.wallet.balance):null;
   host.querySelector(`[data-count="${n}"]`).disabled=state.busy||saved.busy||!!state.intent||!saved.wallet||!saved.canWrite||!!saved.error||!!missing||!configOK;
   host.querySelector(`[data-reason="${n}"]`).textContent=!configOK?'추첨 설정을 확인할 수 없습니다.':missing?`${missing.toLocaleString('ko-KR')} 크리스탈 부족`:!saved.canWrite?'안전한 저장을 지원하는 브라우저가 필요합니다.':saved.error?'저장 상태 확인이 필요합니다.':`${n}회 · ${DRAW_COSTS[n].toLocaleString('ko-KR')} 무료 시뮬레이션 크리스탈`;
  }
  host.querySelector('[data-last]').disabled=state.busy||saved.busy||!!state.intent||!saved.wallet?.receipts.length;
  host.querySelector('[data-pending]').hidden=!state.intent;host.querySelector('[data-pending]').disabled=state.busy;
  host.querySelector('.gacha-draw-status').textContent=state.busy?'차감과 결과를 함께 저장하고 있습니다.':saved.wallet?.receipts.length?`저장된 추첨 ${saved.wallet.receipts.length}건 · 마지막 결과를 다시 볼 수 있습니다.`:'';
  host.querySelector('.gacha-draw-error').textContent=state.error?message(state.error):'';
  if(modal.dialog.open)renderDialog();
 }
 const show=opener=>{renderDialog();modal.open(service.snapshot.status==='result'?'저장된 추첨 결과':'무료 시뮬레이션 추첨 확인',opener);};
 const click=e=>{const target=e.target.closest('button');if(!target)return;
  if(target.dataset.count){const r=service.prepare(getBanner(),Number(target.dataset.count));if(r.ok)show(target);}
  else if(target.hasAttribute('data-last')){service.restore();if(service.snapshot.receipt)show(target);}
  else if(target.hasAttribute('data-pending'))show(target);
 };
 const confirm=e=>{if(e.target.closest('[data-confirm]'))void service.confirm();};
 host.addEventListener('click',click);modal.content.addEventListener('click',confirm);
 const offStore=store.subscribe(render),offService=service.subscribe(render);
 return {service,refresh:render,closeDialogs(){modal.close(false);},setVisible(value){visible=value;if(value){service.restore();render();}else modal.close(false);},
  destroy(){disposed=true;offStore();offService();service.destroy();modal.destroy();host.removeEventListener('click',click);modal.content.removeEventListener('click',confirm);host.remove();}
 };
}
