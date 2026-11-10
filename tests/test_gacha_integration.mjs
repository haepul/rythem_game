import test from 'node:test';
import assert from 'node:assert/strict';
import {createWalletStore} from '../next-stage/gacha/wallet-storage.mjs?v=20261108-day13';
import {createDrawService} from '../next-stage/gacha/draw-service.mjs?v=20261108-day13';
import {createExchangeService} from '../next-stage/gacha/exchange-service.mjs?v=20261108-day13';
import {inventoryModel} from '../next-stage/gacha/inventory-model.mjs?v=20261108-day13';
import {buildResultModel} from '../next-stage/gacha/result-model.mjs?v=20261108-day13';
import {bannerRewards} from '../next-stage/gacha/acquisition-history.mjs?v=20261108-day13';
import {createGachaPresentation} from '../next-stage/gacha/card-reveal.mjs?v=20261108-day13';

function harness(){
 const values=new Map([['wallet',JSON.stringify({schemaVersion:1,balance:6000,claimedGrantIds:['test-crystals-v1']})],['records','untouched-records'],['settings','untouched-settings']]);
 let writes=0,rolls=0,serial=0,tail=Promise.resolve(),readFail=false;
 const storage={getItem:k=>{if(readFail)throw Error('denied');return values.get(k)??null;},setItem:(k,v)=>{values.set(k,v);writes++;}};
 const locks={request:(_key,_options,fn)=>{const p=tail.then(fn);tail=p.catch(()=>{});return p;}};
 const tab=()=>{const store=createWalletStore({key:'wallet',storage,locks});store.refresh();return {store,draw:createDrawService({store,idFactory:()=>`d-${++serial}`,rng:()=>{rolls++;return .99;}}),exchange:createExchangeService({store,idFactory:()=>`e-${++serial}`})};};
 return {tab,values,get writes(){return writes;},get rolls(){return rolls;},set readFail(v){readFail=v;}};
}
test('failed cancellation retains request for retry, while successful cancellation stays read-only',async()=>{
 const h=harness(),t=h.tab();t.draw.prepare('demo-mint',1);const intent=t.draw.snapshot.intent,bytes=h.values.get('wallet');h.readFail=true;
 assert.equal(t.draw.cancel().error,'read-failed');assert.deepEqual(t.draw.snapshot.intent,intent);assert.equal(h.writes,0);assert.equal(h.rolls,0);assert.equal(h.values.get('wallet'),bytes);
 h.readFail=false;assert.ok(t.draw.cancel().cancelled);assert.equal(h.writes,0);assert.equal(h.rolls,0);
});
test('draw and exchange on two tabs share one ledger without losing either operation',async()=>{
 const h=harness(),a=h.tab();a.draw.prepare('demo-mint',10);await a.draw.confirm();const b=h.tab();
 a.draw.prepare('demo-mint',1);b.exchange.prepare('demo-mint','test-card-005');const results=await Promise.all([a.draw.confirm(),b.exchange.confirm()]);assert.ok(results.every(r=>r.ok));
 const wallet=a.store.refresh().wallet;assert.equal(wallet.balance,2700);assert.equal(wallet.receipts.length,2);assert.equal(wallet.exchanges.length,1);assert.equal(wallet.transactions.length,3);assert.equal(inventoryModel(wallet).total,12);assert.equal(bannerRewards(wallet,'demo-mint').balance,3);assert.equal(h.writes,3);assert.equal(h.rolls,22);
});
test('20 restored result/inventory cycles preserve historical NEW, bonus and stored bytes',async()=>{
 const h=harness(),a=h.tab();a.draw.prepare('demo-mint',10);const r=(await a.draw.confirm()).receipt;a.exchange.prepare('demo-mint','test-card-005');await a.exchange.confirm();
 const bytes=h.values.get('wallet'),writes=h.writes,rolls=h.rolls,model=buildResultModel(r,{wallet:a.store.snapshot.wallet});
 for(let i=0;i<20;i++){const t=h.tab();const restored=t.draw.restore().receipt;assert.deepEqual(buildResultModel(restored,{wallet:t.store.snapshot.wallet}),model);assert.equal(inventoryModel(t.store.snapshot.wallet).total,11);assert.equal(bannerRewards(t.store.snapshot.wallet,'demo-mint').balance,2);t.draw.destroy();t.store.destroy();}
 assert.equal(h.values.get('wallet'),bytes);assert.equal(h.writes,writes);assert.equal(h.rolls,rolls);
});
test('explicit corrupt recovery preserves unrelated keys and never silently fixes a future version',async()=>{
 const h=harness(),t=h.tab();for(const raw of ['{',JSON.stringify({schemaVersion:999})]){h.values.set('wallet',raw);t.store.refresh();assert.ok(t.store.snapshot.error);assert.equal(t.draw.prepare('demo-mint',1).ok,false);assert.equal(h.values.get('wallet'),raw);assert.ok((await t.store.recover(raw)).ok);assert.equal(t.store.snapshot.wallet.balance,0);}
 assert.equal(h.values.get('records'),'untouched-records');assert.equal(h.values.get('settings'),'untouched-settings');assert.equal(h.rolls,0);
});
test('20 interrupted presentations clean deadlines and ignore callbacks from earlier runs',()=>{
 let id=0,cleanups=0,finishes=0;const timers=new Map(),late=[];const receipt={request:{requestId:'saved'},results:[{cardId:'test-card-001',rarity:'R2'}]};
 const p=createGachaPresentation({schedule(fn){timers.set(++id,fn);late.push(fn);return id;},unschedule:id=>timers.delete(id),onStage:()=>()=>cleanups++,onFinish:()=>finishes++});
 for(let i=0;i<20;i++){p.start(receipt);p.hide();late.forEach(fn=>fn());assert.equal(timers.size,0);assert.equal(p.active,false);}
 p.destroy();p.destroy();assert.equal(cleanups,20);assert.equal(finishes,20);
});

test('quota failure with 250 receipts preserves every result and retries without pruning',async()=>{
 const h=harness(),source=h.tab();source.draw.prepare('demo-mint',1);const template=(await source.draw.confirm()).receipt;
 const receipts=Array.from({length:250},(_,i)=>({...structuredClone(template),request:{...template.request,requestId:`history-${i}`},balanceBefore:100000-i*300,balanceAfter:100000-(i+1)*300,committedAt:1}));
 const original=JSON.stringify({schemaVersion:2,balance:25000,claimedGrantIds:['test-crystals-v1'],receipts});let raw=original,blocked=true,writes=0;
 const store=createWalletStore({key:'large-fixture',locks:{request:(_k,_o,fn)=>Promise.resolve().then(fn)},storage:{getItem:()=>raw,setItem:(_k,v)=>{if(blocked)throw Object.assign(Error('quota'),{name:'QuotaExceededError'});raw=v;writes++;}}});
 store.refresh();const service=createDrawService({store,idFactory:()=> 'quota-retry',rng:()=>0});service.prepare('demo-mint',10);
 const failed=await service.confirm();assert.equal(failed.error,'quota-exceeded');assert.equal(raw,original);assert.equal(store.snapshot.wallet.receipts.length,250);assert.equal(store.snapshot.wallet.balance,25000);assert.equal(writes,0);
 blocked=false;const saved=await service.confirm();assert.ok(saved.ok);assert.equal(saved.wallet.balance,22000);assert.deepEqual(saved.wallet.receipts.slice(0,250),receipts);assert.equal(saved.wallet.receipts.length,251);assert.equal(inventoryModel(saved.wallet).total,260);assert.equal(writes,1);
 const retry=await service.execute(saved.receipt.request);assert.equal(retry.changed,false);assert.equal(writes,1);assert.deepEqual(retry.receipt,saved.receipt);
});
