import {WALLET_KEY,TEST_GRANT} from './wallet-config.mjs?v=20261101-day7';
import {parseWallet,initialWallet,grantWallet,validateWallet} from './wallet.mjs?v=20261101-day7';

export const WALLET_ERRORS=Object.freeze({
 'invalid-json':'저장된 가챠 데이터를 읽을 수 없습니다. 자동으로 덮어쓰지 않았습니다.',
 'invalid-data':'가챠 저장 데이터의 형식 또는 잔액이 올바르지 않습니다. 원본을 보존했습니다.',
 'unsupported-version':'이 버전에서 읽을 수 없는 가챠 저장 형식입니다. 최신 버전을 확인하거나 명시적으로 초기화해 주세요.',
 'read-failed':'가챠 저장소를 읽지 못했습니다. 브라우저 저장 권한을 확인한 뒤 다시 시도해 주세요.',
 'write-failed':'저장에 실패했습니다. 잔액·결과를 확정하지 않았습니다. 저장 권한을 확인하고 같은 요청으로 다시 시도해 주세요.',
 'quota-exceeded':'저장 공간이 부족합니다. 기록을 삭제하거나 잔액을 차감하지 않았습니다. 공간 확보 후 같은 요청으로 재시도해 주세요.',
 'commit-unknown':'저장 확정 여부를 확인하지 못했습니다. 새 추첨 대신 같은 요청으로 저장소를 다시 확인해 주세요.',
 'locking-unavailable':'이 환경은 안전한 탭 간 잠금을 지원하지 않아 잔액 조회만 가능합니다. HTTPS와 Web Locks 지원 브라우저를 사용해 주세요.',
 'lock-failed':'탭 간 잠금을 얻지 못했습니다. 지급하지 않았으니 다시 시도해 주세요.',
 'recovery-conflict':'확인 중 다른 탭에서 데이터가 변경되었습니다. 최신 상태를 확인하고 다시 진행해 주세요.',
 'overflow':'잔액이 안전한 정수 범위를 넘어 지급할 수 없습니다.',
 'busy':'저장 처리 중입니다.', 'invalid-grant':'지급 설정을 확인할 수 없습니다.'
});

// Only this key is ever written. Each writer must use the same same-origin lock.
// The adapter may throw (including access to window.localStorage itself).
export function createWalletStore({storage,locks,key=WALLET_KEY,grant=TEST_GRANT}={}){
 let wallet=null,error=null,busy=false,destroyed=false,rawToken,refreshPending=false;
 const listeners=new Set(),canWrite=typeof locks?.request==='function';
 const snapshot=()=>({wallet:wallet?structuredClone(wallet):null,error,busy,canWrite,rawToken});
 // A broken view must never turn an accepted write into a failed transaction.
 const notify=listener=>{try{listener(snapshot());}catch{/* Re-entry/reload reads the committed snapshot. */}};
 const publish=()=>{if(!destroyed)for(const listener of listeners)notify(listener);};
 const read=()=>{try{const raw=storage.getItem(key);return {...parseWallet(raw),raw};}catch{return {ok:false,error:'read-failed'};}};
 const accept=result=>{rawToken=result.raw;if(result.ok){wallet=result.wallet;error=null;}else{wallet=null;error=result.error;}};
 function refresh(){if(destroyed)return snapshot();if(busy){refreshPending=true;return snapshot();}accept(read());publish();return snapshot();}
 async function transact(operation){
  if(destroyed)return {ok:false,error:'closed'};
  if(busy)return {ok:false,error:'busy'};
  if(!canWrite){error='locking-unavailable';publish();return {ok:false,error};}
  busy=true;error=null;publish();let entered=false;
  try{return await locks.request(key+':transaction',{mode:'exclusive'},()=>{
   entered=true;if(destroyed)return {ok:false,error:'closed'};
   const fresh=read();
   const next=operation(fresh);
   if(!next.ok){accept(fresh);error=next.error;return next;}
   if(validateWallet(next.wallet)||next.wallet.schemaVersion!==2){accept(fresh);error='invalid-data';return {ok:false,error};}
   const writes=next.changed||fresh.migrated,encoded=JSON.stringify(next.wallet);
   if(writes){
    try{storage.setItem(key,encoded);}
    catch(e){
     const confirmed=read();
     if(!confirmed.ok&&confirmed.error==='read-failed'){wallet=null;error='commit-unknown';return {ok:false,error};}
     if(!confirmed.ok||confirmed.raw!==encoded){accept(confirmed);error=e?.name==='QuotaExceededError'?'quota-exceeded':'write-failed';return {ok:false,error};}
     // An adapter may throw after accepting a write. Exact readback resolves it.
    }
   }
   // Commit UI/memory only after the single saved object has been accepted.
   wallet=structuredClone(next.wallet);rawToken=writes?encoded:fresh.raw;error=null;return structuredClone({...next,migrated:!!fresh.migrated});
  });}catch{error=entered?'write-failed':'lock-failed';return {ok:false,error};}
  finally{
   busy=false;
   if(refreshPending&&!destroyed){
    refreshPending=false;const operationError=error;accept(read());
    // A focus/storage refresh during a failed write must not erase its error.
    if(!error&&operationError)error=operationError;
   }
   publish();
  }
 }
 return {key,get snapshot(){return snapshot();},
  subscribe(listener){listeners.add(listener);notify(listener);return ()=>listeners.delete(listener);},refresh,
  // Synchronous pure update inside the same lock used for grants and recovery.
  update(operation){return transact(fresh=>fresh.ok?operation(fresh.wallet):fresh);},
  migrate(){return transact(fresh=>fresh.ok?{ok:true,changed:false,wallet:fresh.wallet}:fresh);},
  claim(){return transact(fresh=>fresh.ok?grantWallet(fresh.wallet,grant):fresh);},
  // Explicit, confirmed recovery only. Compare with the exact bytes the user saw
  // before the confirmation; never erase a newer write from another tab.
  recover(expectedRaw){return transact(fresh=>{
   if(fresh.error==='read-failed')return fresh;
   if(typeof expectedRaw!=='string'||fresh.raw!==expectedRaw)return {ok:false,error:'recovery-conflict'};
   return {ok:true,changed:true,wallet:initialWallet()};
  });},
  destroy(){destroyed=true;listeners.clear();}
 };
}
export function browserWalletStore(win=window){
 const store=createWalletStore({storage:{getItem:key=>win.localStorage.getItem(key),setItem:(key,value)=>win.localStorage.setItem(key,value)},locks:win.navigator.locks});
 const changed=e=>{if(e.key===null||e.key===store.key)store.refresh();};
 const focus=()=>store.refresh();win.addEventListener('storage',changed);win.addEventListener('focus',focus);
 const destroy=store.destroy;store.destroy=()=>{win.removeEventListener('storage',changed);win.removeEventListener('focus',focus);destroy();};
 return store;
}
