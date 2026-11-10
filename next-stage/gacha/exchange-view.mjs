import {rewardRule} from './reward-config.mjs?v=20261108-day13';
import {bannerRewards} from './acquisition-history.mjs?v=20261108-day13';
import {createExchangeService,EXCHANGE_ERRORS} from './exchange-service.mjs?v=20261108-day13';
import {WALLET_ERRORS} from './wallet-storage.mjs?v=20261108-day13';
import {mountGachaDialog} from './details.mjs?v=20261108-day13';
export function mountExchange(root,{store,getBanner,inventory,banners}){
 const doc=root.ownerDocument,rule=rewardRule(),service=createExchangeService({store});let visible=false,disposed=false,banner=null,stage='list',saved=null,error=null;
 const panel=doc.createElement('section');panel.className='gacha-rewards';panel.innerHTML='<h3>무료 스티커 보너스</h3><p class="gacha-reward-rule"></p><p class="gacha-reward-balance" role="status" aria-live="polite"></p><progress aria-label="추첨 보너스 진행도"></progress><p class="gacha-reward-last"></p><button class="ui-button ui-button--accent" type="button">교환소</button>';
 root.querySelector('.gacha-bottom').before(panel);const openButton=panel.querySelector('button'),summary=panel.querySelector('.gacha-reward-balance'),bar=panel.querySelector('progress');
 panel.querySelector('.gacha-reward-rule').textContent=`프로젝트 무료 테스트 규칙 · 대상 배너 카드 1장당 스티커 ${rule.stickersPerCard}장과 진행도 ${rule.progressPerCard}점. ${rule.threshold}점마다 같은 배너 스티커 ${rule.bonusStickers}장 추가. 기존 유효한 추첨에도 최초 규칙을 소급 적용합니다. 같은 배너 스티커 ${rule.exchangeCost}장으로 임시 카드 1장 교환 · 교환 보너스 없음 · 만료/현금 가치 없음.`;
 const message=code=>EXCHANGE_ERRORS[code]??WALLET_ERRORS[code]??'교환을 처리하지 못했습니다. 저장 상태를 확인하세요.';
 const closeRequest=()=>{if(service.snapshot.busy)return false;const r=service.cancel();if(!r.ok){error=r.error;update();return true;}if(r.committed){saved=r.exchange;stage='result';build();return false;}return true;};
 const modal=mountGachaDialog(root,{titleId:'gacha-exchange-title',onVisible:()=>visible,onRequestClose:closeRequest});modal.dialog.classList.add('gacha-collection-dialog');
 function update(){if(!visible||disposed)return;const s=store.snapshot;let current=null;try{if(s.wallet&&!s.error)current=bannerRewards(s.wallet,getBanner());}catch{}
  summary.textContent=current?`스티커 ${current.balance}장 · 보너스 ${current.progress}/${current.threshold} · 다음 보상 스티커 ${current.bonus}장`:'저장 상태를 확인할 수 없습니다. 가챠 저장 복구 안내를 확인하세요.';
  bar.max=rule.threshold;bar.value=current?.progress??0;bar.setAttribute('aria-valuetext',summary.textContent);openButton.disabled=!current||!s.canWrite||s.busy||!rule.banners.includes(getBanner());
  const last=s.wallet?.exchanges?.filter(e=>e.request.bannerId===getBanner()).at(-1);panel.querySelector('.gacha-reward-last').textContent=last?`마지막 확정 교환: ${last.request.cardId} (${last.request.rarity}) · 스티커 ${last.request.cost}장 사용`:'';
  if(!modal.dialog.open)return;
  const close=modal.dialog.querySelector('.gacha-dialog-close');close.disabled=service.snapshot.busy;close.textContent=service.snapshot.busy?'저장 처리 중…':stage==='confirming'?'취소':'원래 배너로 돌아가기';
  const note=modal.content.querySelector('[data-balance]');let state=null;try{if(s.wallet&&!s.error)state=bannerRewards(s.wallet,banner);}catch{}
  if(note)note.textContent=state?`현재 ${state.balance}장 · 비용 ${rule.exchangeCost}장 · ${state.balance<rule.exchangeCost?`${rule.exchangeCost-state.balance}장 더 필요`:`교환 후 ${state.balance-rule.exchangeCost}장`}`:'저장 상태 확인 불가';
  for(const b of modal.content.querySelectorAll('[data-card],[data-confirm-exchange]'))b.disabled=service.snapshot.busy||s.busy||!s.canWrite||!state||state.balance<rule.exchangeCost;
  const alert=modal.content.querySelector('[role=alert]');if(alert)alert.textContent=error?message(error):'';
 }
 function build(){if(!visible||disposed)return;modal.content.replaceChildren();const el=(tag,text)=>{const e=doc.createElement(tag);e.textContent=text;modal.content.append(e);return e;};
  el('p',banners.find(b=>b.id===banner)?.title??banner);
  if(stage==='result'){
   el('p',`교환 저장 완료 · ${saved.request.cardId} · ${saved.request.rarity} · 1장 획득`).setAttribute('role','status');el('p',`사용 스티커 ${saved.request.cost}장 · 확정 직후 ${saved.stickersAfter}장`);
   const b=el('button','보관함에서 확인');b.type='button';b.className='ui-button ui-button--accent';b.dataset.inventory='';
  }else{
   const balance=el('p','');balance.dataset.balance='';balance.setAttribute('role','status');
   if(stage==='confirming'){const r=service.snapshot.intent;el('p',`${r.cardId} · ${r.rarity} 카드 1장으로 교환합니다. 교환에는 진행도와 보너스가 붙지 않습니다.`);const b=el('button','확인하고 교환');b.type='button';b.className='ui-button ui-button--accent';b.dataset.confirmExchange='';}
   else{el('p','교환할 임시 카드를 선택하세요.');const list=el('div','');list.className='gacha-exchange-options';for(const card of rule.cards){const b=doc.createElement('button');b.type='button';b.className='ui-button';b.dataset.card=card.id;b.textContent=`${card.rarity} · ${card.id} · 스티커 ${rule.exchangeCost}장`;list.append(b);}}
  }
  el('p','').setAttribute('role','alert');
  if(stage==='confirming'&&error){const retry=el('button','저장 상태 다시 확인');retry.type='button';retry.className='ui-button';retry.dataset.refreshExchange='';}
  update();modal.dialog.querySelector('.gacha-dialog-close').focus({preventScroll:true});
 }
 const open=()=>{banner=service.snapshot.intent?.bannerId??getBanner();stage=service.snapshot.intent?'confirming':'list';saved=null;error=null;store.refresh();if(modal.open('무료 스티커 교환소',openButton))build();};
 const click=async e=>{const b=e.target.closest('button');if(!b||service.snapshot.busy)return;
  if(b.dataset.card){const r=service.prepare(banner,b.dataset.card);error=r.ok?null:r.error;if(r.ok)stage='confirming';build();}
  else if(b.hasAttribute('data-confirm-exchange')){error=null;const promise=service.confirm();update();const r=await promise;if(disposed)return;if(r.ok){saved=r.exchange;stage='result';}else error=r.error;if(visible&&modal.dialog.open)build();}
  else if(b.hasAttribute('data-refresh-exchange')){const s=store.refresh();error=s.error??null;build();}
  else if(b.hasAttribute('data-inventory')){modal.close(false);inventory.open(openButton);}
 };
 openButton.addEventListener('click',open);modal.content.addEventListener('click',click);const off=store.subscribe(update);
 return {refresh:update,close(){modal.close(false);if(!service.snapshot.busy)service.cancel();},setVisible(v){visible=v;if(!v)modal.close(false);else update();},destroy(){disposed=true;visible=false;off();openButton.removeEventListener('click',open);modal.content.removeEventListener('click',click);modal.destroy();panel.remove();}};
}
