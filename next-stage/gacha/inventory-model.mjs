import {validateWallet} from './wallet.mjs?v=20261108-day13';
import {acquisitions} from './acquisition-history.mjs?v=20261108-day13';
export function inventoryModel(wallet,{rarity='all',sort='id'}={}){
 if(validateWallet(wallet))return {status:'error',cards:[],total:0};
 const entries=acquisitions(wallet),byId=new Map();let total=0;
 for(const receipt of entries)for(const [index,card] of receipt.results.entries()){
  let item=byId.get(card.cardId);if(!item){item={cardId:card.cardId,rarity:card.rarity,count:0,duplicates:0,history:[]};byId.set(card.cardId,item);}
  item.count++;item.duplicates=item.count-1;total++;item.history.push({requestId:receipt.id,index,bannerId:receipt.bannerId,source:receipt.kind});
 }
 const cards=[...byId.values()].filter(c=>rarity==='all'||c.rarity===rarity);
 cards.sort((a,b)=>sort==='count'?b.count-a.count||a.cardId.localeCompare(b.cardId):sort==='rarity'?b.rarity.localeCompare(a.rarity)||a.cardId.localeCompare(b.cardId):a.cardId.localeCompare(b.cardId));
 return {status:total===0?'empty':cards.length===0?'filtered-empty':'ready',total,unique:byId.size,cards};
}
