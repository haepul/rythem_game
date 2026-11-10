import {validReceipt,sameDrawRequest,validateWallet} from './wallet.mjs?v=20261108-day13';
import {acquisitions} from './acquisition-history.mjs?v=20261108-day13';

const frozen=value=>{if(value&&typeof value==='object'){Object.values(value).forEach(frozen);Object.freeze(value);}return value;};
const sameReceipt=(a,b)=>validReceipt(a)&&validReceipt(b)&&sameDrawRequest(a.request,b.request)&&
 ['balanceBefore','balanceAfter','committedAt'].every(k=>a[k]===b[k])&&a.results.every((c,i)=>
 ['cardId','rarity','configVersion','schemaVersion'].every(k=>c[k]===b.results[i][k]));

// Read-only projection. historyComplete is a caller guarantee about provenance,
// not something timestamps or a current inventory can establish.
export function buildResultModel(receipt,{history,historyComplete=false,wallet}={}){
 if(!receipt?.request?.requestId||!Array.isArray(receipt.results))throw TypeError('A committed receipt is required');
 let newStatus='unknown',seen=new Set();
 if(wallet){history=wallet.receipts;historyComplete=!validateWallet(wallet);}
 if(historyComplete&&Array.isArray(history)&&history.every(validReceipt)&&
  new Set(history.map(r=>r.request.requestId)).size===history.length){
  const index=history.findIndex(r=>r.request.requestId===receipt.request.requestId);
  if(index>=0&&sameReceipt(history[index],receipt)){
   newStatus='known';
   const entries=wallet?acquisitions(wallet):history.map(r=>({kind:'draw',id:r.request.requestId,results:r.results}));
   for(const entry of entries){if(entry.kind==='draw'&&entry.id===receipt.request.requestId)break;for(const card of entry.results)seen.add(card.cardId);}
  }
 }
 const cards=receipt.results.map((card,index)=>{
  const isNew=newStatus==='known'?!seen.has(card.cardId):null;
  seen.add(card.cardId);
  return {key:JSON.stringify([receipt.request.requestId,index]),index,cardId:card.cardId,rarity:card.rarity,isNew};
 });
 return frozen({requestId:receipt.request.requestId,bannerId:receipt.request.bannerId,count:cards.length,
  cost:receipt.request.cost,balanceBefore:receipt.balanceBefore,balanceAfter:receipt.balanceAfter,newStatus,cards});
}
