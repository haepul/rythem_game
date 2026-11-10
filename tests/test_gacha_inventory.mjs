import test from 'node:test';import assert from 'node:assert/strict';
import {inventoryModel} from '../next-stage/gacha/inventory-model.mjs';
import {createWalletStore} from '../next-stage/gacha/wallet-storage.mjs?v=20261108-day13';
import {createDrawService} from '../next-stage/gacha/draw-service.mjs?v=20261108-day13';
test('DAY11 committed counts, duplicates, filters, sorting and pure repeated reads',async()=>{
 let raw=null,writes=0;const store=createWalletStore({storage:{getItem:()=>raw,setItem:(_k,v)=>{raw=v;writes++;}},locks:{request:(_n,_o,fn)=>fn()}});store.refresh();assert.equal(inventoryModel(store.snapshot.wallet).status,'empty');await store.claim();
 const draw=createDrawService({store,rng:()=>0,idFactory:()=> 'inventory-ten'});draw.prepare('demo-mint',10);const result=await draw.confirm();assert.ok(result.ok);const bytes=raw,w=writes;
 for(let i=0;i<3;i++){draw.restore();const m=inventoryModel(store.snapshot.wallet);assert.equal(m.total,10);assert.equal(m.cards[0].count,10);assert.equal(m.cards[0].duplicates,9);assert.equal(m.cards[0].history.length,10);assert.equal(inventoryModel(store.snapshot.wallet,{rarity:'R4'}).status,'filtered-empty');}
 assert.equal((await draw.execute(result.receipt.request)).changed,false);store.refresh();assert.equal(raw,bytes);assert.equal(writes,w);assert.equal(store.snapshot.wallet.balance,0);
});
test('DAY11 storage error is distinct from empty inventory',()=>{assert.equal(inventoryModel(null).status,'error');assert.equal(inventoryModel({schemaVersion:99}).status,'error');});
