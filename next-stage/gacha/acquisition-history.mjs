import {REWARD_VERSION,LEGACY_REWARD_VERSION,rewardRule} from './reward-config.mjs?v=20261108-day13';
export const drawTransaction=receipt=>({kind:'draw',id:receipt.request.requestId,rewardVersion:REWARD_VERSION});
export const legacyDrawTransaction=receipt=>({kind:'draw',id:receipt.request.requestId,rewardVersion:LEGACY_REWARD_VERSION});
export function acquisitions(wallet){
 const draws=new Map((wallet.receipts??[]).map(r=>[r.request.requestId,r])),exchanges=new Map((wallet.exchanges??[]).map(r=>[r.request.requestId,r]));
 return (wallet.transactions??(wallet.receipts??[]).map(legacyDrawTransaction)).map(t=>{
  const r=(t.kind==='draw'?draws:exchanges).get(t.id);if(!r)throw Error('incomplete-history');
  return {kind:t.kind,id:t.id,bannerId:r.request.bannerId,results:t.kind==='draw'?r.results:[{cardId:r.request.cardId,rarity:r.request.rarity}]};
 });
}
export function rewardBalances(wallet){
 const result=new Map(),progress=new Map(),draws=new Map((wallet.receipts??[]).map(r=>[r.request.requestId,r])),exchanges=new Map((wallet.exchanges??[]).map(r=>[r.request.requestId,r]));
 for(const t of wallet.transactions??(wallet.receipts??[]).map(legacyDrawTransaction)){
  const r=(t.kind==='draw'?draws:exchanges).get(t.id);if(!r)throw Error('incomplete-history');
  const rule=rewardRule(t.kind==='draw'?t.rewardVersion:r.request.ruleVersion),banner=r.request.bannerId;
  if(!rule.banners.includes(banner)){if(t.kind==='exchange')throw Error('invalid-exchange');continue;}
  let balance=result.get(banner)??0;
  if(t.kind==='draw'){
   const key=JSON.stringify([banner,rule.version]),points=(progress.get(key)??0)+r.results.length*rule.progressPerCard;
   balance+=r.results.length*rule.stickersPerCard+Math.floor(points/rule.threshold)*rule.bonusStickers;progress.set(key,points%rule.threshold);
  }else{
   if(r.stickersBefore!==balance||r.stickersAfter!==balance-r.request.cost||r.stickersAfter<0)throw Error('invalid-exchange-balance');
   balance-=r.request.cost;
  }
  if(!Number.isSafeInteger(balance)||balance<0)throw Error('reward-overflow');result.set(banner,balance);
 }
 return {balances:result,progress};
}
export function bannerRewards(wallet,bannerId,version=REWARD_VERSION){const state=rewardBalances(wallet),rule=rewardRule(version);return {balance:state.balances.get(bannerId)??0,progress:state.progress.get(JSON.stringify([bannerId,version]))??0,threshold:rule.threshold,bonus:rule.bonusStickers};}
