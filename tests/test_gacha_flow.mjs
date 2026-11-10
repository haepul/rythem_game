import test from 'node:test';
import assert from 'node:assert/strict';
import {createWalletStore} from '../next-stage/gacha/wallet-storage.mjs?v=20261108-day13';
import {createDrawService,resolveDrawConfig} from '../next-stage/gacha/draw-service.mjs?v=20261108-day13';
import {initialWallet,parseWallet,validateWallet} from '../next-stage/gacha/wallet.mjs?v=20261108-day13';
import {WALLET_KEY,TEST_GRANT} from '../next-stage/gacha/wallet-config.mjs?v=20261108-day13';

function fixture(balance=3000){
 const data=new Map([[WALLET_KEY,JSON.stringify({...initialWallet(),balance,claimedGrantIds:[TEST_GRANT.id]})]]);
 let tail=Promise.resolve(),writes=0,rolls=0,id=0,readError=false,writeError=null,afterWrite=null;
 const storage={getItem(k){if(readError)throw Error('read');return data.get(k)??null;},setItem(k,v){if(writeError)throw writeError;data.set(k,v);writes++;afterWrite?.();}};
 const locks={request(name,opts,task){assert.equal(name,WALLET_KEY+':transaction');assert.equal(opts.mode,'exclusive');const job=tail.then(task);tail=job.catch(()=>{});return job;}};
 const create=(extra={})=>{const store=createWalletStore({storage,locks});store.refresh();return {store,service:createDrawService({store,rng:()=>{rolls++;return 0;},idFactory:()=>`request-${++id}`,clock:()=>100,...extra})};};
 return {data,storage,locks,create,get writes(){return writes;},get rolls(){return rolls;},set readError(v){readError=v;},set writeError(v){writeError=v;},set afterWrite(v){afterWrite=v;},read:()=>JSON.parse(data.get(WALLET_KEY))};
}
const intent=(s,count=1,id='external')=>({...s.quote('demo-mint',count),requestId:id});

test('v1 migration preserves balance and claimed IDs in the SAME key; no duplicate grant',async()=>{
 const f=fixture();f.data.set(WALLET_KEY,JSON.stringify({schemaVersion:1,balance:2700,claimedGrantIds:[TEST_GRANT.id,'old-grant']}));
 const {store,service}=f.create();assert.equal(store.snapshot.wallet.balance,2700);assert.equal(f.writes,0);
 assert.equal((await store.migrate()).migrated,true);assert.equal(f.read().schemaVersion,3);assert.deepEqual(f.read().claimedGrantIds,[TEST_GRANT.id,'old-grant']);
 assert.equal((await store.claim()).changed,false);assert.equal(f.read().balance,2700);
 await service.execute(intent(service));assert.equal(f.read().balance,2400);assert.equal(f.read().receipts.length,1);assert.equal(f.data.size,1);
});
for(const count of [1,10])test(`${count} draws debit once with exactly ${count} persisted results`,async()=>{
 const f=fixture(),{store,service}=f.create();service.prepare('demo-mint',count);const result=await service.confirm();
 assert.equal(result.ok,true);assert.equal(result.receipt.results.length,count);assert.equal(f.read().balance,3000-(count===1?300:3000));assert.equal(f.writes,1);assert.equal(f.rolls,count*2);
 assert.deepEqual(store.snapshot.wallet,f.read());assert.equal(validateWallet(f.read()),null);
});
test('cancel is RNG-free, write-free, and cannot later confirm',async()=>{
 const f=fixture(),{service}=f.create();service.prepare('demo-mint',10);assert.equal(service.snapshot.status,'confirming');
 assert.equal(service.cancel().cancelled,true);assert.equal((await service.confirm()).ok,false);assert.equal(f.writes,0);assert.equal(f.rolls,0);assert.equal(f.read().balance,3000);
});
test('insufficient balance is rechecked inside lock, not just the confirmation',async()=>{
 const f=fixture(),a=f.create(),b=f.create();a.service.prepare('demo-mint',10);await b.service.execute(intent(b.service));
 assert.equal((await a.service.confirm()).error,'insufficient-balance');assert.equal(f.read().balance,2700);assert.equal(f.writes,1);assert.equal(f.rolls,2);
});
test('20 fast confirmations: only one commit, no duplicate random results',async()=>{
 const f=fixture(),{service}=f.create();service.prepare('demo-mint',1);const results=await Promise.all(Array.from({length:20},()=>service.confirm()));
 assert.equal(results.filter(r=>r.ok).length,1);assert.equal(results.filter(r=>r.error==='busy').length,19);assert.equal(f.writes,1);assert.equal(f.rolls,2);
});
test('two tabs with different requests consume newest balance; no lost update',async()=>{
 const f=fixture(600),a=f.create(),b=f.create();a.service.prepare('demo-mint',1);b.service.prepare('demo-peach',1);
 assert.ok((await Promise.all([a.service.confirm(),b.service.confirm()])).every(r=>r.ok));assert.equal(f.read().balance,0);assert.equal(f.read().receipts.length,2);assert.equal(f.rolls,4);
});
test('two tabs with SAME intent return the exact receipt, no second debit/RNG/write',async()=>{
 const f=fixture(),a=f.create(),b=f.create(),request=intent(a.service);
 const [x,y]=await Promise.all([a.service.execute(request),b.service.execute(request)]);
 assert.deepEqual(x.receipt,y.receipt);assert.equal(f.read().balance,2700);assert.equal(f.writes,1);assert.equal(f.rolls,2);
 assert.deepEqual((await a.service.execute(request)).receipt,x.receipt);assert.equal(f.writes,1);
});
for(const [key,value] of [['bannerId','demo-lilac'],['count',10],['cost',301],['configVersion','changed'],['policyVersion','changed'],['configFingerprint','changed']])test(`same ID conflicting ${key} rejected`,async()=>{
 const f=fixture(),a=f.create(),request=intent(a.service);await a.service.execute(request);
 const b=f.create();assert.equal((await b.service.execute({...request,[key]:value})).error,'request-conflict');assert.equal(f.writes,1);assert.equal(f.rolls,2);
});
for(const name of ['Error','QuotaExceededError'])test(`failed ${name} write has no debit/results; retry same ID`,async()=>{
 const f=fixture(),{store,service}=f.create();service.prepare('demo-mint',1);const id=service.snapshot.intent.requestId;
 f.writeError=Object.assign(Error('failed'),{name});assert.equal((await service.confirm()).ok,false);assert.equal(f.read().balance,3000);assert.equal(f.read().receipts.length,0);assert.equal(store.snapshot.wallet.balance,3000);assert.equal(service.snapshot.intent.requestId,id);
 f.writeError=null;assert.equal((await service.confirm()).ok,true);assert.equal(f.read().balance,2700);assert.equal(f.read().receipts[0].request.requestId,id);
});
test('throw AFTER successful setItem is reconciled by exact readback',async()=>{
 const f=fixture(),{service}=f.create();f.afterWrite=()=>{throw Error('adapter after write');};
 assert.equal((await service.execute(intent(service))).ok,true);assert.equal(f.read().balance,2700);assert.equal(f.writes,1);
});
test('unknown commit + read failure retains intent; retry restores receipt without reroll',async()=>{
 const f=fixture(),{service}=f.create();service.prepare('demo-mint',1);const req=service.snapshot.intent;
 f.afterWrite=()=>{f.readError=true;throw Error('after write');};assert.equal((await service.confirm()).error,'commit-unknown');
 assert.equal(service.cancel().ok,false);assert.deepEqual(service.snapshot.intent,req);
 f.readError=false;f.afterWrite=null;assert.equal((await service.confirm()).ok,true);assert.equal(f.rolls,2);assert.equal(f.writes,1);
});
test('broken UI subscriber cannot change success; reload restores exact last result',async()=>{
 const f=fixture(),{store,service}=f.create();store.subscribe(()=>{throw Error('view failed');});service.subscribe(()=>{throw Error('view failed');});
 const r=await service.execute(intent(service));assert.equal(r.ok,true);
 const reloaded=f.create();assert.deepEqual(reloaded.service.restore().receipt,r.receipt);assert.equal((await reloaded.service.execute(r.receipt.request)).changed,false);assert.equal(f.rolls,2);
 const copy=reloaded.store.snapshot;copy.wallet.receipts[0].results[0].cardId='tampered';assert.notEqual(reloaded.store.snapshot.wallet.receipts[0].results[0].cardId,'tampered');
});
for(const raw of ['{',JSON.stringify({...initialWallet(),schemaVersion:99}),JSON.stringify({...initialWallet(),receipts:[{}]})])test(`corrupt/future snapshot is preserved: ${raw.slice(0,35)}`,async()=>{
 const f=fixture(),{service}=f.create(),r=intent(service);f.data.set(WALLET_KEY,raw);assert.equal((await service.execute(r)).ok,false);assert.equal(f.data.get(WALLET_KEY),raw);assert.equal(f.writes,0);assert.equal(f.rolls,0);
});
test('latest configuration is checked under lock, same-version content edits also rejected',async()=>{
 const f=fixture();let changed=false;const {service}=f.create({resolve:id=>{const d=resolveDrawConfig(id);if(!changed)return d;const config=structuredClone(d.config);config.pools[0].weightBps-=100;config.pools[1].weightBps+=100;return {...d,config};}});
 service.prepare('demo-mint',1);changed=true;assert.equal((await service.confirm()).error,'config-changed');assert.equal(f.rolls,0);assert.equal(f.writes,0);
});
test('old receipts remain replayable when their config is retired; no pruning',async()=>{
 const f=fixture(),a=f.create();const r=await a.service.execute(intent(a.service));
 const b=f.create({resolve:()=>{throw Error('retired');}});assert.deepEqual((await b.service.execute(r.receipt.request)).receipt,r.receipt);assert.equal(f.writes,1);
});
test('RNG failure never writes partial results or debits',async()=>{
 const f=fixture();let i=0;const {service}=f.create({rng:()=>++i===19?NaN:0});assert.equal((await service.execute(intent(service,10))).error,'rng-failed');assert.equal(f.writes,0);assert.equal(f.read().balance,3000);
});
test('grant and draw use one lock; migration races serialize and preserve grants',async()=>{
 const f=fixture();f.data.set(WALLET_KEY,JSON.stringify({schemaVersion:1,balance:300,claimedGrantIds:[]}));
 const a=f.create(),b=f.create();await Promise.all([a.store.claim(),b.service.execute(intent(b.service))]);
 assert.equal(f.read().balance,3000);assert.deepEqual(f.read().claimedGrantIds,[TEST_GRANT.id]);assert.equal(f.read().receipts.length,1);
});
test('no Web Locks is read-only for draw, too',async()=>{
 const f=fixture(),store=createWalletStore({storage:f.storage});store.refresh();const s=createDrawService({store});assert.equal((await s.execute(intent(s))).error,'locking-unavailable');assert.equal(f.writes,0);assert.equal(f.rolls,0);
});
test('wrong receipt shape, arithmetic and duplicate IDs rejected without truncation',async()=>{
 const f=fixture(),{service}=f.create();await service.execute(intent(service));
 for(const mutate of [w=>w.receipts.push(w.receipts[0]),w=>w.receipts[0].balanceAfter++,w=>w.receipts[0].results.pop(),w=>w.receipts[0].results[0].configVersion='bad',w=>w.receipts[0].extra=true]){const w=f.read();mutate(w);assert.equal(parseWallet(JSON.stringify(w)).error,'invalid-data');}
});
test('explicit recovery clears stale service errors, and a recovery/grant keeps other keys',async()=>{
 const f=fixture();f.data.set(WALLET_KEY,'{');f.data.set('rhythm-next-records','keep');const {store,service}=f.create();
 assert.equal(service.restore().error,'invalid-json');await store.recover('{');assert.equal(service.snapshot.error,null);assert.equal(service.snapshot.status,'idle');
 await store.claim();assert.equal(f.data.get('rhythm-next-records'),'keep');assert.equal(f.read().balance,3000);
});
