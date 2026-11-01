import test from 'node:test';
import assert from 'node:assert/strict';
import {initialWallet,validateWallet,parseWallet,grantWallet,drawEligibility} from '../next-stage/gacha/wallet.mjs?v=20261101-day7';
import {createWalletStore,browserWalletStore} from '../next-stage/gacha/wallet-storage.mjs?v=20261101-day7';
import {WALLET_KEY,TEST_GRANT,DRAW_COST} from '../next-stage/gacha/wallet-config.mjs?v=20261101-day7';
import {bannerDetails} from '../next-stage/gacha/details.mjs?v=20261101-day7';
import {BANNERS} from '../next-stage/gacha/banners.mjs?v=20261101-day7';

function fixture(){
 const data=new Map();let tail=Promise.resolve(),writes=0,readError=null,writeError=null;
 const storage={getItem(key){if(readError)throw readError;return data.get(key)??null;},setItem(key,value){if(writeError)throw writeError;writes++;data.set(key,value);}};
 const locks={request(name,options,task){assert.equal(name,WALLET_KEY+':transaction');assert.equal(options.mode,'exclusive');const job=tail.then(task);tail=job.catch(()=>{});return job;}};
 return {data,storage,locks,get writes(){return writes;},set readError(e){readError=e;},set writeError(e){writeError=e;},create:()=>createWalletStore({storage,locks})};
}
test('DAY4 details are selected by ID; no fabricated rates or draw rules',()=>{
 for(const b of BANNERS){const d=bannerDetails(b.id,BANNERS,{bindings:{}});assert.equal(d.title,b.title);assert.equal(d.description,b.subtitle);assert.match(d.probability,/미설정/);assert.doesNotMatch(JSON.stringify(d),/\d+%/);assert.match(d.rarity,/준비 중/);}
 assert.equal(bannerDetails('missing',BANNERS),null);
});
test('initial zero, pure grant, duplicate idempotency and immutable input',()=>{
 const state=initialWallet(),result=grantWallet(state,TEST_GRANT);
 assert.equal(state.balance,0);assert.deepEqual(state.claimedGrantIds,[]);
 assert.equal(result.wallet.balance,3000);assert.equal(grantWallet(result.wallet,TEST_GRANT).changed,false);assert.equal(DRAW_COST,300);
});
test('persisted single object commits before notifying; fresh store restores',async()=>{
 const f=fixture(),s=f.create();s.refresh();assert.equal(f.writes,0);
 s.subscribe(({wallet})=>{if(wallet?.balance===3000)assert.deepEqual(JSON.parse(f.data.get(WALLET_KEY)),wallet);});
 assert.equal((await s.claim()).ok,true);assert.equal(f.writes,1);assert.equal(f.data.size,1);
 const next=f.create();next.refresh();assert.equal(next.snapshot.wallet.balance,3000);assert.equal((await next.claim()).changed,false);assert.equal(f.writes,1);
});
test('rapid repeated claims are busy or duplicate and never double pay',async()=>{
 const f=fixture(),s=f.create();s.refresh();const results=await Promise.all(Array.from({length:20},()=>s.claim()));
 assert.equal(results.filter(r=>r.changed).length,1);assert.equal(results.filter(r=>r.error==='busy').length,19);assert.equal(s.snapshot.wallet.balance,3000);assert.equal(f.writes,1);
});
test('two tabs re-read inside shared lock; both converge to same 3000',async()=>{
 const f=fixture(),a=f.create(),b=f.create();a.refresh();b.refresh();
 const results=await Promise.all([a.claim(),b.claim()]);assert.equal(results.filter(r=>r.changed).length,1);assert.equal(f.writes,1);assert.deepEqual(a.snapshot.wallet,b.snapshot.wallet);
});
for(const name of ['SecurityError','QuotaExceededError','Error'])test(`write ${name}: no balance or claim commit; retry pays once`,async()=>{
 const f=fixture(),s=f.create();s.refresh();f.writeError=Object.assign(new Error(),{name});
 const result=await s.claim();assert.equal(result.ok,false);assert.equal(s.snapshot.wallet.balance,0);assert.deepEqual(s.snapshot.wallet.claimedGrantIds,[]);assert.equal(f.data.size,0);assert.equal(s.snapshot.busy,false);
 f.writeError=null;assert.equal((await s.claim()).ok,true);assert.equal(s.snapshot.wallet.balance,3000);assert.equal(f.writes,1);
});
test('getItem failure blocks grant and recovery without overwriting anything',async()=>{
 const f=fixture(),s=f.create();f.readError=new Error();assert.equal(s.refresh().error,'read-failed');assert.equal((await s.claim()).error,'read-failed');assert.equal((await s.recover('bad')).error,'read-failed');assert.equal(f.writes,0);
 f.readError=null;assert.equal(s.refresh().wallet.balance,0);
});
const invalid=[['json','{','invalid-json'],['null','null'],['array','[]'],['string','"value"'],['missing','{}'],['version type','{"schemaVersion":"1"}'],['future',JSON.stringify({...initialWallet(),schemaVersion:99}),'unsupported-version'],['past',JSON.stringify({...initialWallet(),schemaVersion:0}),'unsupported-version'],
 ...[-1,.5,Number.MAX_SAFE_INTEGER+1,'3000',null].map((balance,i)=>['balance'+i,JSON.stringify({...initialWallet(),balance})]),
 ...[null,'id',[1],[''],['x','x']].map((claimedGrantIds,i)=>['ids'+i,JSON.stringify({...initialWallet(),claimedGrantIds})]),['extra field',JSON.stringify({...initialWallet(),unknown:1})]];
for(const [label,raw,code='invalid-data'] of invalid)test(`reject ${label}; preserve bytes; require explicit recovery`,async()=>{
 const f=fixture();f.data.set(WALLET_KEY,raw);const s=f.create();assert.equal(s.refresh().error,code);assert.equal(s.snapshot.wallet,null);
 assert.equal((await s.claim()).error,code);assert.equal(f.data.get(WALLET_KEY),raw);assert.equal(f.writes,0);
 assert.equal((await s.recover(raw)).ok,true);assert.deepEqual(s.snapshot.wallet,initialWallet());assert.equal((await s.claim()).wallet.balance,3000);
});
test('recovery preserves records, favorites, settings and rejects stale confirmation',async()=>{
 const f=fixture();for(const key of ['rhythm-next-settings','rhythm-next-records','rhythm-next-favorites'])f.data.set(key,'keep');
 f.data.set(WALLET_KEY,'bad');const a=f.create(),b=f.create();a.refresh();b.refresh();
 await b.recover('bad');await b.claim();assert.equal((await a.recover('bad')).error,'recovery-conflict');assert.equal(a.snapshot.wallet.balance,3000);
 for(const key of ['rhythm-next-settings','rhythm-next-records','rhythm-next-favorites'])assert.equal(f.data.get(key),'keep');
});
test('failed recovery preserves corrupt bytes and remains recoverable',async()=>{
 const f=fixture();f.data.set(WALLET_KEY,'bad');const s=f.create();s.refresh();f.writeError=new Error();assert.equal((await s.recover('bad')).ok,false);assert.equal(f.data.get(WALLET_KEY),'bad');
 f.writeError=null;s.refresh();assert.equal((await s.recover('bad')).ok,true);
});
test('no Web Locks is read-only, including explicit reset; lock denial is retriable',async()=>{
 const f=fixture(),s=createWalletStore({storage:f.storage});s.refresh();assert.equal((await s.claim()).error,'locking-unavailable');assert.equal((await s.recover('bad')).error,'locking-unavailable');assert.equal(f.writes,0);
 const denied=createWalletStore({storage:f.storage,locks:{request:()=>Promise.reject(new Error())}});assert.equal((await denied.claim()).error,'lock-failed');assert.equal(denied.snapshot.busy,false);
});
test('overflow, nonfinite amounts and bad grants are rejected without mutation',()=>{
 const wallet={...initialWallet(),balance:Number.MAX_SAFE_INTEGER};assert.equal(grantWallet(wallet,TEST_GRANT).error,'overflow');
 for(const amount of [NaN,Infinity,-Infinity,-1,0,.1,Number.MAX_SAFE_INTEGER+1,'3'])assert.equal(grantWallet(initialWallet(),{id:'test',amount}).error,'invalid-grant');
 for(const balance of [NaN,Infinity,-Infinity])assert.equal(validateWallet({...initialWallet(),balance}),'invalid-data');
 assert.equal(grantWallet(initialWallet(),{id:'',amount:1}).error,'invalid-grant');
});
test('cost fixtures distinguish every gate; boundary equal succeeds; no debit',()=>{
 const check=(cost,balance=3000,extra={})=>drawEligibility({cost,balance,...extra});
 assert.equal(check(null),'cost-unset');assert.equal(check(undefined),'cost-unset');
 for(const cost of [0,-1,.5,'3000',NaN,Infinity,Number.MAX_SAFE_INTEGER+1])assert.equal(check(cost),'invalid-cost');
 assert.equal(check(3000,2999),'insufficient-balance');assert.equal(check(3000,3000),'ready');assert.equal(check(3000,3001),'ready');assert.equal(check(Number.MAX_SAFE_INTEGER,Number.MAX_SAFE_INTEGER),'ready');
 assert.equal(check(3000,-1),'storage-unavailable');assert.equal(check(null,0,{busy:true}),'busy');assert.equal(check(null,0,{storageAvailable:false}),'storage-unavailable');
});
test('snapshot cannot mutate internal state; destroy cancels queued claim',async()=>{
 const f=fixture(),s=f.create();s.refresh();const copy=s.snapshot;copy.wallet.balance=42;copy.wallet.claimedGrantIds.push('bad');assert.equal(s.snapshot.wallet.balance,0);
 const pending=s.claim();s.destroy();assert.equal((await pending).error,'closed');assert.equal(f.writes,0);
});
test('browser storage/focus refresh and listener cleanup',async()=>{
 const f=fixture(),handlers=new Map();const win={localStorage:f.storage,navigator:{locks:f.locks},addEventListener:(type,fn)=>handlers.set(type,fn),removeEventListener:type=>handlers.delete(type)};
 const a=browserWalletStore(win),b=f.create();a.refresh();await b.claim();handlers.get('storage')({key:'unrelated'});assert.equal(a.snapshot.wallet.balance,0);
 handlers.get('storage')({key:WALLET_KEY});assert.equal(a.snapshot.wallet.balance,3000);f.data.delete(WALLET_KEY);handlers.get('focus')();assert.equal(a.snapshot.wallet.balance,0);
 handlers.get('storage')({key:null});a.destroy();assert.equal(handlers.size,0);
});
test('refresh during queued transaction is reconciled after completion',async()=>{
 const f=fixture(),s=f.create();s.refresh();const p=s.claim();s.refresh();await p;assert.equal(s.snapshot.wallet.balance,3000);assert.equal(parseWallet(f.data.get(WALLET_KEY)).ok,true);
});
test('queued focus refresh does not hide a failed write error',async()=>{
 const f=fixture(),s=f.create();s.refresh();f.writeError=new Error();const p=s.claim();s.refresh();await p;
 assert.equal(s.snapshot.error,'write-failed');assert.equal(s.snapshot.wallet.balance,0);
});
