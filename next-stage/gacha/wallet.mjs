import {SCHEMA_VERSION,INITIAL_BALANCE} from './wallet-config.mjs?v=20261101-day7';

export const safeAmount=value=>Number.isSafeInteger(value)&&value>=0;
export const initialWallet=()=>({schemaVersion:SCHEMA_VERSION,balance:INITIAL_BALANCE,claimedGrantIds:[],receipts:[]});
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
export function validateWallet(value){
 if(!value||typeof value!=='object'||Array.isArray(value))return 'invalid-data';
 if(!Number.isInteger(value.schemaVersion))return 'invalid-data';
 if(value.schemaVersion!==1&&value.schemaVersion!==SCHEMA_VERSION)return 'unsupported-version';
 const keys=value.schemaVersion===1?'balance,claimedGrantIds,schemaVersion':'balance,claimedGrantIds,receipts,schemaVersion';
 if(!shape(value,keys)||!safeAmount(value.balance)||!Array.isArray(value.claimedGrantIds))return 'invalid-data';
 if(value.claimedGrantIds.some(id=>typeof id!=='string'||!id.trim())||new Set(value.claimedGrantIds).size!==value.claimedGrantIds.length)return 'invalid-data';
 if(value.schemaVersion===2&&(!Array.isArray(value.receipts)||!value.receipts.every(validReceipt)||new Set(value.receipts.map(r=>r.request.requestId)).size!==value.receipts.length))return 'invalid-data';
 return null;
}
export function migrateWallet(wallet){return wallet.schemaVersion===1?{...wallet,schemaVersion:SCHEMA_VERSION,claimedGrantIds:[...wallet.claimedGrantIds],receipts:[]}:structuredClone(wallet);}
export function parseWallet(raw){
 if(raw===null)return {ok:true,wallet:initialWallet()};
 try{const wallet=JSON.parse(raw),error=validateWallet(wallet);return error?{ok:false,error}:{ok:true,wallet:migrateWallet(wallet),migrated:wallet.schemaVersion===1};}
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
