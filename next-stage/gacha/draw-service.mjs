import {DRAW_COSTS,COST_POLICY_VERSION} from './wallet-config.mjs?v=20261101-day7';
import {validDrawRequest,sameDrawRequest} from './wallet.mjs?v=20261101-day7';
import {CARDS} from './cards.mjs?v=20261101-day7';
import {DRAW_CONFIGS,BANNER_DRAW_CONFIG_IDS,validateDrawConfig} from './draw-config.mjs?v=20261101-day7';
import {drawCards} from './draw-engine.mjs?v=20261101-day7';

export const DRAW_ERRORS=Object.freeze({
 'invalid-request':'추첨 요청 형식이 잘못되었습니다.',
 'invalid-config':'선택 배너의 추첨 설정을 확인할 수 없습니다.',
 'config-changed':'확인한 설정 또는 비용이 변경되었습니다. 취소 후 새 안내를 확인해 주세요.',
 'request-conflict':'같은 요청 ID에 다른 내용이 있습니다. 차감하지 않았습니다.',
 'insufficient-balance':'무료 시뮬레이션 크리스탈이 부족합니다.',
 'rng-failed':'추첨 결과를 생성하지 못했습니다. 차감하지 않았습니다.',
 'request-id-unavailable':'안전한 요청 ID를 만들 수 없는 환경입니다.',
 'pending-request':'먼저 진행 중인 요청을 확인하거나 취소해 주세요.',
 'cancelled':'추첨을 취소했습니다.', 'busy':'저장 처리 중입니다.'
});
export function resolveDrawConfig(bannerId){
 const version=Object.hasOwn(BANNER_DRAW_CONFIG_IDS,bannerId)?BANNER_DRAW_CONFIG_IDS[bannerId]:null;
 const config=version&&Object.hasOwn(DRAW_CONFIGS,version)?DRAW_CONFIGS[version]:null;
 if(!config||config.version!==version)throw new Error('invalid-config');
 return {config,cards:CARDS};
}
const fingerprint=({config,cards})=>JSON.stringify({config,cards:cards.map(c=>({id:c.id,rarity:c.rarity}))});
export function createDrawService({store,resolve=resolveDrawConfig,rng=Math.random,idFactory=()=>globalThis.crypto.randomUUID(),clock=()=>Date.now()}={}){
 let status='idle',intent=null,receipt=null,error=null,busy=false;
 const listeners=new Set();
 const snapshot=()=>structuredClone({status,intent,receipt,error,busy});
 const publish=()=>{for(const fn of listeners){try{fn(snapshot());}catch{/* UI failure cannot change persistence. */}}};
 const fail=code=>{status='error';error=code;publish();return {ok:false,error:code};};
 function quote(bannerId,count){
  if(count!==1&&count!==10)throw new Error('invalid-request');
  const definition=resolve(bannerId);validateDrawConfig(definition.config,definition.cards);
  return {bannerId,count,cost:DRAW_COSTS[count],policyVersion:COST_POLICY_VERSION,configVersion:definition.config.version,configFingerprint:fingerprint(definition)};
 }
 function prepare(bannerId,count){
  if(busy||store.snapshot.busy)return {ok:false,error:'busy'};
  if(intent)return {ok:false,error:'pending-request'};
  const state=store.refresh();
  if(state.error||!state.wallet)return fail(state.error??'read-failed');
  if(!state.canWrite)return fail('locking-unavailable');
  let request;try{request=quote(bannerId,count);}catch{return fail('invalid-config');}
  if(state.wallet.balance<request.cost)return fail('insufficient-balance');
  try{request.requestId=idFactory();if(!validDrawRequest(request))throw new Error();}catch{return fail('request-id-unavailable');}
  intent=Object.freeze(request);receipt=null;status='confirming';error=null;publish();return {ok:true,intent:{...intent}};
 }
 async function execute(request){
  if(busy)return {ok:false,error:'busy'};
  if(!validDrawRequest(request))return {ok:false,error:'invalid-request'};
  if(intent&&!sameDrawRequest(intent,request))return {ok:false,error:'pending-request'};
  intent=Object.freeze({...request});busy=true;status='committing';error=null;publish();
  let result;
  try{result=await store.update(wallet=>{
   const existing=wallet.receipts.find(r=>r.request.requestId===intent.requestId);
   if(existing)return sameDrawRequest(existing.request,intent)?{ok:true,changed:false,wallet,receipt:existing}:{ok:false,error:'request-conflict'};
   let current;try{current=quote(intent.bannerId,intent.count);}catch{return {ok:false,error:'invalid-config'};}
   if(!sameDrawRequest({...current,requestId:intent.requestId},intent))return {ok:false,error:'config-changed'};
   if(wallet.balance<intent.cost)return {ok:false,error:'insufficient-balance'};
   let results;try{const def=resolve(intent.bannerId);results=drawCards(def.config,intent.count,{cards:def.cards,rng});}catch{return {ok:false,error:'rng-failed'};}
   const next={request:{...intent},results,balanceBefore:wallet.balance,balanceAfter:wallet.balance-intent.cost,committedAt:clock()};
   return {ok:true,changed:true,receipt:next,wallet:{...wallet,balance:next.balanceAfter,receipts:[...wallet.receipts,next]}};
  });}catch{result={ok:false,error:'commit-unknown'};}
  busy=false;
  if(!result.ok)return fail(result.error);
  receipt=result.receipt;intent=null;status='result';error=null;publish();return result;
 }
 function cancel(){
  if(busy)return {ok:false,error:'busy'};
  // Read before dismissing an uncertain request. Never hide a committed result.
  if(intent){const state=store.refresh();if(state.error)return fail(state.error);
   const saved=state.wallet?.receipts.find(r=>r.request.requestId===intent.requestId);
   if(saved){if(!sameDrawRequest(saved.request,intent))return fail('request-conflict');receipt=saved;intent=null;status='result';error=null;publish();return {ok:true,committed:true};}
  }
  intent=null;receipt=null;status='idle';error=null;publish();return {ok:true,cancelled:true};
 }
 function restore(){
  if(busy)return snapshot();
  const state=store.refresh();if(state.error){fail(state.error);return snapshot();}
  if(intent){const saved=state.wallet?.receipts.find(r=>sameDrawRequest(r.request,intent));if(saved){receipt=saved;intent=null;status='result';error=null;}}
  else{receipt=state.wallet?.receipts.at(-1)??null;status=receipt?'result':'idle';error=null;}
  publish();return snapshot();
 }
 // Storage recovery/another tab also clears stale idle error messages. Do not
 // replace a pinned intent or an in-flight result with a background refresh.
 const offStore=store.subscribe(state=>{if(busy||intent)return;receipt=state.wallet?.receipts.at(-1)??null;error=state.error;status=error?'error':receipt?'result':'idle';publish();});
 return {quote,prepare,execute,cancel,restore,get snapshot(){return snapshot();},
  destroy(){offStore();listeners.clear();},
  confirm(){return intent?execute(intent):Promise.resolve({ok:false,error:'invalid-request'});},
  acknowledge(){if(!busy&&!intent){status='idle';error=null;publish();}},
  subscribe(fn){listeners.add(fn);try{fn(snapshot());}catch{}return ()=>listeners.delete(fn);}
 };
}
