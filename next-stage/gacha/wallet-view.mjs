import {TEST_GRANT,DRAW_COSTS} from './wallet-config.mjs?v=20261108-day13';
import {browserWalletStore,WALLET_ERRORS} from './wallet-storage.mjs?v=20261108-day13';
import {mountGachaDialog} from './details.mjs?v=20261108-day13';

export function mountWalletView(root,{store=browserWalletStore(root.ownerDocument.defaultView),ownsStore=true}={}){
 const doc=root.ownerDocument;let visible=false,disposed=false,lastMessage='',recoveryToken;
 const host=doc.createElement('section');host.className='gacha-wallet';host.setAttribute('aria-label','무료 시뮬레이션 크리스탈');
 host.innerHTML=`<p class="gacha-wallet-label">무료 시뮬레이션 크리스탈</p><strong class="gacha-balance">확인 중</strong>
 <p class="gacha-wallet-policy">프로젝트 임시 테스트 규칙 · 초기 0 · 저장 데이터당 1회 3,000 지급<br>현금 가치 없음 · 1회 ${DRAW_COSTS[1]} / 10회 ${DRAW_COSTS[10]}</p>
 <div class="gacha-wallet-actions"><button type="button" class="ui-button ui-button--accent gacha-claim">테스트 재화 받기</button><button type="button" class="ui-button gacha-retry" hidden>저장소 다시 확인</button><button type="button" class="ui-button gacha-recover" hidden>가챠 데이터만 초기화…</button></div>
 <p class="gacha-wallet-status" role="status" aria-live="polite" aria-atomic="true"></p><p class="gacha-wallet-error" role="alert" aria-atomic="true"></p>`;
 root.querySelector('.gacha-heading').append(host);
 const q=s=>host.querySelector(s),claim=q('.gacha-claim'),retry=q('.gacha-retry'),recover=q('.gacha-recover');
 const modal=mountGachaDialog(root,{titleId:'gacha-recovery-title',onVisible:()=>visible});
 const notice=doc.createElement('p');notice.textContent='가챠의 잔액, 1회 지급 내역, 모든 추첨 결과와 요청 내역을 초기화합니다. 이 저장 객체에 포함된 새 버전의 가챠 정보도 삭제되며 되돌릴 수 없습니다. 새 저장 데이터에서는 테스트 지급을 다시 받을 수 있습니다. 곡 기록·즐겨찾기·설정은 보존됩니다.';
 const confirm=doc.createElement('button');confirm.type='button';confirm.className='ui-button';confirm.textContent='확인: 가챠 데이터만 초기화';modal.content.append(notice,confirm);
 function render(state){if(!visible||disposed)return;
  const {wallet,error,busy,canWrite}=state,claimed=wallet?.claimedGrantIds.includes(TEST_GRANT.id);
  q('.gacha-balance').textContent=wallet?wallet.balance.toLocaleString('ko-KR'):'확인 불가';
  host.setAttribute('aria-busy',String(busy));claim.disabled=busy||!wallet||!!claimed||!canWrite;
  claim.textContent=busy?'저장 처리 중…':claimed?'✓ 테스트 지급 완료':'테스트 재화 받기';
  retry.hidden=!error;retry.disabled=busy;
  recover.hidden=!['invalid-json','invalid-data','unsupported-version'].includes(error);recover.disabled=busy||!canWrite;
  confirm.disabled=busy;confirm.textContent=busy?'저장 처리 중…':'확인: 가챠 데이터만 초기화';
  const message=[error?WALLET_ERRORS[error]??'가챠 저장 상태를 확인해 주세요.':'',!canWrite&&error!=='locking-unavailable'?WALLET_ERRORS['locking-unavailable']:''].filter(Boolean).join(' ');
  q('.gacha-wallet-error').textContent=message;
  if(message&&modal.dialog.open)modal.close();
  q('.gacha-wallet-status').textContent=busy?'저장소를 확인하고 있습니다.':error?'':lastMessage||(claimed?'테스트 재화 지급 완료 · 잔액 '+wallet.balance.toLocaleString('ko-KR'):'');
 }
 const unsubscribe=store.subscribe(state=>{lastMessage='';render(state);});
 const requestGrant=async()=>{lastMessage='';const result=await store.claim();if(disposed)return;
  if(result.ok)lastMessage=result.changed?'테스트 크리스탈 3,000 지급 완료. 이 저장 데이터에서는 다시 지급되지 않습니다.':'이미 지급된 테스트 재화입니다.';render(store.snapshot);
 };
 const reread=()=>{lastMessage='';store.refresh();};
 const showRecovery=()=>{recoveryToken=store.snapshot.rawToken;modal.open('가챠 데이터 초기화',recover);};
 const reset=async()=>{lastMessage='';const result=await store.recover(recoveryToken);if(disposed)return;
  if(result.ok){lastMessage='가챠 데이터만 초기화했습니다. 잔액은 0입니다.';modal.close(false);if(visible)claim.focus();}render(store.snapshot);
 };
 claim.addEventListener('click',requestGrant);retry.addEventListener('click',reread);recover.addEventListener('click',showRecovery);confirm.addEventListener('click',reset);
 return {setVisible(value){visible=value;if(value){lastMessage='';store.refresh();render(store.snapshot);}else modal.close(false);},closeDialogs(){modal.close(false);},
  destroy(){disposed=true;unsubscribe();if(ownsStore)store.destroy();modal.destroy();claim.removeEventListener('click',requestGrant);retry.removeEventListener('click',reread);recover.removeEventListener('click',showRecovery);confirm.removeEventListener('click',reset);host.remove();}
 };
}
