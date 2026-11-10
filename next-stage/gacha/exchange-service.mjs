import {REWARD_VERSION,rewardRule} from './reward-config.mjs?v=20261108-day13';
import {bannerRewards} from './acquisition-history.mjs?v=20261108-day13';
import {validExchangeRequest,sameExchangeRequest} from './wallet.mjs?v=20261108-day13';
export const EXCHANGE_ERRORS=Object.freeze({'insufficient-stickers':'스티커가 부족합니다. 최신 잔량을 확인하세요.','request-conflict':'같은 거래 ID의 내용이 다릅니다. 비용을 차감하지 않았습니다.','invalid-exchange':'교환 설정을 확인할 수 없습니다.','pending-request':'현재 교환을 먼저 확인하거나 취소하세요.','busy':'저장 처리 중입니다.','request-id-unavailable':'안전한 거래 ID를 생성할 수 없습니다.'});
export function createExchangeService({store,idFactory=()=>globalThis.crypto.randomUUID(),clock=()=>Date.now()}={}){
 let intent=null,busy=false;
 const quote=(bannerId,cardId)=>{const rule=rewardRule(),card=rule.cards.find(c=>c.id===cardId);if(!rule.banners.includes(bannerId)||!card)throw Error('invalid-exchange');return {bannerId,cardId,rarity:card.rarity,ruleVersion:REWARD_VERSION,cost:rule.exchangeCost};};
 function prepare(bannerId,cardId){if(busy||store.snapshot.busy)return {ok:false,error:'busy'};if(intent)return {ok:false,error:'pending-request'};const saved=store.refresh();if(saved.error)return {ok:false,error:saved.error};if(!saved.canWrite)return {ok:false,error:'locking-unavailable'};
  let request;try{request={...quote(bannerId,cardId),requestId:idFactory()};if(!validExchangeRequest(request))throw Error();}catch{return {ok:false,error:'invalid-exchange'};}
  intent=Object.freeze(request);return {ok:true,intent:{...intent}};
 }
 async function execute(request){
  if(busy)return {ok:false,error:'busy'};if(!validExchangeRequest(request))return {ok:false,error:'invalid-exchange'};
  if(intent&&!sameExchangeRequest(intent,request))return {ok:false,error:'pending-request'};
  request=Object.freeze({...request});intent=request;busy=true;
  try{const result=await store.update(wallet=>{
   if(wallet.receipts.some(r=>r.request.requestId===request.requestId))return {ok:false,error:'request-conflict'};
   const old=wallet.exchanges.find(r=>r.request.requestId===request.requestId);
   if(old)return sameExchangeRequest(old.request,request)?{ok:true,changed:false,wallet,exchange:old}:{ok:false,error:'request-conflict'};
   if(request.ruleVersion!==REWARD_VERSION)return {ok:false,error:'invalid-exchange'};
   const before=bannerRewards(wallet,request.bannerId,request.ruleVersion).balance;
   if(before<request.cost)return {ok:false,error:'insufficient-stickers'};
   const exchange={request:{...request},stickersBefore:before,stickersAfter:before-request.cost,committedAt:clock()};
   return {ok:true,changed:true,exchange,wallet:{...wallet,exchanges:[...wallet.exchanges,exchange],transactions:[...wallet.transactions,{kind:'exchange',id:request.requestId}]}};
  });if(result.ok)intent=null;return result;}catch{return {ok:false,error:'commit-unknown'};}finally{busy=false;}
 }
 function cancel(){if(busy)return {ok:false,error:'busy'};
  if(intent){const saved=store.refresh();if(saved.error)return {ok:false,error:saved.error};const old=saved.wallet.exchanges.find(e=>e.request.requestId===intent.requestId);if(old){if(!sameExchangeRequest(old.request,intent))return {ok:false,error:'request-conflict'};intent=null;return {ok:true,committed:true,exchange:old};}}
  intent=null;return {ok:true,cancelled:true};
 }
 return {quote,prepare,execute,cancel,confirm:()=>intent?execute(intent):Promise.resolve({ok:false,error:'invalid-exchange'}),get snapshot(){return {busy,intent:intent?{...intent}:null};}};
}
