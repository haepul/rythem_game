import {SCHEMA_VERSION,INITIAL_BALANCE} from './wallet-config.mjs?v=20261108-day13';
import {legacyDrawTransaction,rewardBalances} from './acquisition-history.mjs?v=20261108-day13';
import {rewardRule} from './reward-config.mjs?v=20261108-day13';

export const safeAmount=value=>Number.isSafeInteger(value)&&value>=0;
export const initialWallet=()=>({schemaVersion:SCHEMA_VERSION,balance:INITIAL_BALANCE,claimedGrantIds:[],receipts:[],exchanges:[],transactions:[]});
const text=v=>typeof v==='string'&&v.trim().length>0;
const shape=(v,keys)=>v&&typeof v==='object'&&!Array.isArray(v)&&Object.keys(v).sort().join(',')===keys.split(',').sort().join(',');
export function validDrawRequest(r){
 return shape(r,'requestId,bannerId,count,cost,configVersion,configFingerprint,policyVersion')&&
 ['requestId','bannerId','configVersion','configFingerprint','policyVersion'].every(k=>text(r[k]))&&
 (r.count===1||r.count===10)&&safeAmount(r.cost)&&r.cost>0;
}
export const sameDrawRequest=(a,b)=>validDrawRequest(a)&&validDrawRequest(b)&&Object.keys(a).every(k=>a[k]===b[k]);
export function validReceipt(r){
 return shape(r,'request,results,balanceBefore,balanceAfter,committedAt')&&validDrawRequest(r.request)&&
 safeAmount(r.balanceBefore)&&safeAmount(r.balanceAfter)&&r.balanceBefore-r.request.cost===r.balanceAfter&&safeAmount(r.committedAt)&&
 Array.isArray(r.results)&&r.results.length===r.request.count&&r.results.every(c=>
 shape(c,'cardId,rarity,configVersion,schemaVersion')&&text(c.cardId)&&['R2','R3','R4'].includes(c.rarity)&&c.configVersion===r.request.configVersion&&c.schemaVersion===1);
}
export function validExchangeRequest(r){
 if(!shape(r,'requestId,bannerId,ruleVersion,cardId,rarity,cost')||!text(r.requestId))return false;
 try{const rule=rewardRule(r.ruleVersion);return rule.banners.includes(r.bannerId)&&r.cost===rule.exchangeCost&&rule.cards.some(c=>c.id===r.cardId&&c.rarity===r.rarity);}catch{return false;}
}
export const sameExchangeRequest=(a,b)=>validExchangeRequest(a)&&validExchangeRequest(b)&&Object.keys(a).every(k=>a[k]===b[k]);
export const validExchange=r=>shape(r,'request,stickersBefore,stickersAfter,committedAt')&&validExchangeRequest(r.request)&&safeAmount(r.stickersBefore)&&safeAmount(r.stickersAfter)&&safeAmount(r.committedAt)&&r.stickersBefore-r.request.cost===r.stickersAfter;
export function validateWallet(value){
 if(!value||typeof value!=='object'||Array.isArray(value))return 'invalid-data';
 if(!Number.isInteger(value.schemaVersion))return 'invalid-data';
 if(![1,2,SCHEMA_VERSION].includes(value.schemaVersion))return 'unsupported-version';
 const keys=value.schemaVersion===1?'balance,claimedGrantIds,schemaVersion':value.schemaVersion===2?'balance,claimedGrantIds,receipts,schemaVersion':'balance,claimedGrantIds,receipts,exchanges,transactions,schemaVersion';
 if(!shape(value,keys)||!safeAmount(value.balance)||!Array.isArray(value.claimedGrantIds))return 'invalid-data';
 if(value.claimedGrantIds.some(id=>typeof id!=='string'||!id.trim())||new Set(value.claimedGrantIds).size!==value.claimedGrantIds.length)return 'invalid-data';
 if(value.schemaVersion>=2&&(!Array.isArray(value.receipts)||!value.receipts.every(validReceipt)||new Set(value.receipts.map(r=>r.request.requestId)).size!==value.receipts.length))return 'invalid-data';
 if(value.schemaVersion===3){
  if(!Array.isArray(value.exchanges)||!value.exchanges.every(validExchange)||!Array.isArray(value.transactions))return 'invalid-data';
  const ids=[...value.receipts,...value.exchanges].map(r=>r.request.requestId);
  if(new Set(ids).size!==ids.length||value.transactions.length!==ids.length)return 'invalid-data';
  const seen=new Set(),drawIds=[],exchangeIds=[];
  for(const t of value.transactions){
   if(!t||seen.has(t.id)||!ids.includes(t.id))return 'invalid-data';seen.add(t.id);
   if(t.kind==='draw'){if(!shape(t,'kind,id,rewardVersion'))return 'invalid-data';try{rewardRule(t.rewardVersion);}catch{return 'unsupported-version';}drawIds.push(t.id);}
   else if(t.kind==='exchange'&&shape(t,'kind,id'))exchangeIds.push(t.id);else return 'invalid-data';
  }
  if(JSON.stringify(drawIds)!==JSON.stringify(value.receipts.map(r=>r.request.requestId))||JSON.stringify(exchangeIds)!==JSON.stringify(value.exchanges.map(r=>r.request.requestId)))return 'invalid-data';
  try{rewardBalances(value);}catch{return 'invalid-data';}
 }
 return null;
}
export function migrateWallet(wallet){const current=structuredClone(wallet);if(current.schemaVersion===3)return current;return {...current,schemaVersion:SCHEMA_VERSION,receipts:current.receipts??[],exchanges:[],transactions:(current.receipts??[]).map(legacyDrawTransaction)};}
export function parseWallet(raw){
 if(raw===null)return {ok:true,wallet:initialWallet()};
 try{const wallet=JSON.parse(raw),error=validateWallet(wallet);if(error)return {ok:false,error};const migrated=migrateWallet(wallet),migrationError=validateWallet(migrated);return migrationError?{ok:false,error:migrationError}:{ok:true,wallet:migrated,migrated:wallet.schemaVersion!==SCHEMA_VERSION};}
 catch{return {ok:false,error:'invalid-json'};}
}
export function grantWallet(wallet,{id,amount}){
 const error=validateWallet(wallet);if(error)return {ok:false,error};
 if(typeof id!=='string'||!id.trim()||!safeAmount(amount)||amount===0)return {ok:false,error:'invalid-grant'};
 const current=migrateWallet(wallet);
 if(wallet.claimedGrantIds.includes(id))return {ok:true,changed:false,wallet:current};
 if(!safeAmount(wallet.balance+amount))return {ok:false,error:'overflow'};
 return {ok:true,changed:true,wallet:{...current,balance:wallet.balance+amount,claimedGrantIds:[...wallet.claimedGrantIds,id]}};
}
// Eligibility only: no debit, random draw or result is created by this function.
export function drawEligibility({cost,balance,busy=false,storageAvailable=true}){
 if(busy)return 'busy';
 if(!storageAvailable)return 'storage-unavailable';
 if(cost===null||cost===undefined)return 'cost-unset';
 if(!safeAmount(cost)||cost===0)return 'invalid-cost';
 if(!safeAmount(balance))return 'storage-unavailable';
 return balance<cost?'insufficient-balance':'ready';
}
