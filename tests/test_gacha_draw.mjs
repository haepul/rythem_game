import test from 'node:test';
import assert from 'node:assert/strict';
import {CARDS} from '../next-stage/gacha/cards.mjs?v=20261101-day7';
import {TEST_DRAW_CONFIG as C,validateDrawConfig,drawProbabilities,DrawConfigError} from '../next-stage/gacha/draw-config.mjs?v=20261101-day7';
import {drawCards,DrawRandomError} from '../next-stage/gacha/draw-engine.mjs?v=20261101-day7';
import {bannerDetails,probabilityLabel} from '../next-stage/gacha/details.mjs?v=20261101-day7';
import {BANNERS} from '../next-stage/gacha/banners.mjs?v=20261101-day7';
import {createWalletStore} from '../next-stage/gacha/wallet-storage.mjs?v=20261101-day7';
import {WALLET_KEY,DRAW_COST} from '../next-stage/gacha/wallet-config.mjs?v=20261101-day7';
const clone=x=>structuredClone(x),sequence=values=>{let i=0;return ()=>values[i++];};
function prev(x){const b=new DataView(new ArrayBuffer(8));b.setFloat64(0,x);b.setBigUint64(0,b.getBigUint64(0)-1n);return b.getFloat64(0);}

test('six stable IDs, two per rarity; immutable project test defaults',()=>{
 assert.equal(CARDS.length,6);assert.equal(new Set(CARDS.map(c=>c.id)).size,6);
 assert.equal(validateDrawConfig(C),true);assert.equal(C.guarantee,'none');assert.equal(DRAW_COST,300);
 for(const r of ['R2','R3','R4'])assert.equal(CARDS.filter(c=>c.rarity===r).length,2);
 assert.ok(Object.isFrozen(C.pools[0].cardIds));assert.ok(Object.isFrozen(CARDS[0]));
});
for(const [roll,rarity] of [[0,'R2'],[prev(.8),'R2'],[.8,'R3'],[prev(.95),'R3'],[.95,'R4'],[prev(1),'R4']])
 test(`rarity half-open boundary ${roll} -> ${rarity}`,()=>{
  for(const [r,index] of [[0,0],[prev(.5),0],[.5,1],[prev(1),1]]){
   const [result]=drawCards(C,1,{rng:sequence([roll,r])});
   assert.equal(result.rarity,rarity);assert.equal(result.cardId,C.pools.find(p=>p.rarity===rarity).cardIds[index]);
   assert.equal(result.configVersion,C.version);assert.equal(result.schemaVersion,1);
  }
 });
for(const invalid of [1,-.1,NaN,Infinity,-Infinity,'0',null,undefined])test(`invalid RNG ${String(invalid)} at both stages`,()=>{
 assert.throws(()=>drawCards(C,1,{rng:sequence([invalid,0])}),DrawRandomError);
 assert.throws(()=>drawCards(C,1,{rng:sequence([0,invalid])}),DrawRandomError);
});
test('zero weight intervals, including empty lists and trailing zero, never selected',()=>{
 for(const selected of [0,1,2]){const c=clone(C);c.pools.forEach((p,i)=>{p.weightBps=i===selected?10000:0;if(i!==selected)p.cardIds=[];});
  for(const r of [0,.5,prev(1)])assert.equal(drawCards(c,1,{rng:sequence([r,0])})[0].rarity,c.pools[selected].rarity);
 }
});
const badConfigs=[
 ['null',()=>null],['empty config',()=>({})],['empty pools',c=>({...c,pools:[]})],
 ['sum',c=>{c.pools[0].weightBps--;return c;}],
 ...[-1,.1,NaN,Infinity,10001,'8000'].map(v=>['weight '+String(v),c=>{c.pools[0].weightBps=v;return c;}]),
 ['empty positive pool',c=>{c.pools[0].cardIds=[];return c;}],
 ['missing ID',c=>{c.pools[0].cardIds[0]='missing';return c;}],
 ['duplicate ref',c=>{c.pools[0].cardIds[1]=c.pools[0].cardIds[0];return c;}],
 ['rarity mismatch',c=>{c.pools[0].cardIds[0]='test-card-003';return c;}],
 ['duplicate rarity',c=>{c.pools[1].rarity='R2';return c;}],
 ['unknown rarity',c=>{c.pools[0].rarity='R5';return c;}],
 ['guarantee',c=>({...c,guarantee:'R3-or-higher'})],
 ['future schema',c=>({...c,schemaVersion:2})],['no version',c=>({...c,version:''})],
 ['unimplemented extra rule',c=>({...c,pity:100})]
];
for(const [label,change] of badConfigs)test(`reject config: ${label} before consuming RNG`,()=>{
 const c=change(clone(C));let calls=0;
 assert.throws(()=>drawCards(c,1,{rng:()=>{calls++;return 0;}}),DrawConfigError);assert.equal(calls,0);
 assert.throws(()=>drawProbabilities(c),DrawConfigError);
});
test('empty/duplicate/malformed card catalog rejected',()=>{
 const duplicate=clone(CARDS);duplicate[1].id=duplicate[0].id;
 for(const cards of [[],null,duplicate,[{id:'bad'}],CARDS.map(c=>({...c,rarity:'R8'}))])assert.throws(()=>drawCards(C,1,{cards,rng:()=>0}),DrawConfigError);
});
test('exact batch sizes, deterministic sequences, no hidden ten-draw guarantee or input mutation',()=>{
 const c=clone(C),cards=clone(CARDS),before=JSON.stringify({c,cards});
 const values=Array.from({length:20},(_,i)=>i%2?.5:.1);
 const result=drawCards(c,10,{cards,rng:sequence(values)});
 assert.equal(result.length,10);assert.ok(result.every(r=>r.rarity==='R2'&&r.cardId==='test-card-002'));
 assert.deepEqual(result,drawCards(c,10,{cards,rng:sequence(values)}));assert.equal(JSON.stringify({c,cards}),before);
 assert.equal(drawCards(C,1,{rng:()=>0}).length,1);
 for(const count of [0,2,9,11,-1,1.5,'1',null,NaN])assert.throws(()=>drawCards(C,count),RangeError);
 assert.throws(()=>drawCards(C,1,{rng:0}),TypeError);
});
test('late RNG failure throws rather than returning partial results',()=>{
 let result='not returned',calls=0;
 assert.throws(()=>{result=drawCards(C,10,{rng:()=>++calls===19?1:0});},DrawRandomError);
 assert.equal(calls,19);assert.equal(result,'not returned');
 assert.throws(()=>drawCards(C,1,{rng:()=>{throw new Error('rng failed');}}),/rng failed/);
});
test('RNG callbacks cannot silently change a validated batch midway',()=>{
 const c=clone(C);const result=drawCards(c,10,{rng:()=>{c.pools[0].weightBps=0;c.pools[0].cardIds=[];return 0;}});
 assert.ok(result.every(r=>r.cardId==='test-card-001'));
});
test('all banners disclose the engine config; per-card percentages sum to 100',()=>{
 const p=drawProbabilities(C);assert.deepEqual(p.rarities.map(r=>probabilityLabel(r.weightBps)),['80%','15%','5%']);
 assert.deepEqual(p.cards.map(r=>probabilityLabel(r.numeratorBps,r.denominator)),['40%','40%','7.5%','7.5%','2.5%','2.5%']);
 assert.equal(p.cards.reduce((s,r)=>s+r.numeratorBps/r.denominator,0),10000);
 for(const b of BANNERS){const d=bannerDetails(b.id,BANNERS);assert.equal(d.status,'configured');assert.equal(d.title,b.title);assert.deepEqual(d.rates,p);assert.match(d.rules,/10회 보장 없음/);assert.match(d.rules,/1회 300 \/ 10회 3000/);assert.match(d.probability,/공식 확률이 아닙니다/);}
 const changed=clone(C);changed.pools[0].weightBps=7000;changed.pools[2].weightBps=1500;
 const d=bannerDetails('demo-mint',BANNERS,{configs:{[C.version]:changed}});assert.equal(d.rates.rarities[0].weightBps,7000);
 assert.equal(drawCards(changed,1,{rng:sequence([.7,0])})[0].rarity,'R3');
});
test('unset/invalid disclosure paths never substitute valid-looking rates',()=>{
 assert.equal(bannerDetails('missing',BANNERS),null);
 assert.equal(bannerDetails('demo-mint',BANNERS,{bindings:null}).status,'invalid');
 for(const bindings of [{},{'demo-mint':null}]){const d=bannerDetails('demo-mint',BANNERS,{bindings});assert.equal(d.status,'unset');assert.equal(d.rates,null);assert.match(d.probability,/미설정/);}
 for(const configs of [{},{[C.version]:{...C,guarantee:'pity'}}]){const d=bannerDetails('demo-mint',BANNERS,{configs});assert.equal(d.status,'invalid');assert.equal(d.rates,null);assert.match(d.probability,/설정 오류/);}
});
test('fixed seed distribution sanity check (not a substitute for boundary tests)',t=>{
 let seed=123456789;const rng=()=>{seed=(Math.imul(1664525,seed)+1013904223)>>>0;return seed/4294967296;};
 const counts=Object.fromEntries(CARDS.map(c=>[c.id,0]));
 for(let i=0;i<5000;i++)for(const r of drawCards(C,10,{rng}))counts[r.cardId]++;
 const expected=[.4,.4,.075,.075,.025,.025];Object.values(counts).forEach((v,i)=>assert.ok(Math.abs(v/50000-expected[i])<.012));t.diagnostic(JSON.stringify(counts));
});
test('pure draws and failures leave existing wallet/storage untouched',async()=>{
 const data=new Map(),storage={getItem:k=>data.get(k)??null,setItem:(k,v)=>data.set(k,v)},locks={request:(n,o,fn)=>fn()};
 const store=createWalletStore({storage,locks});store.refresh();await store.claim();
 const raw=data.get(WALLET_KEY),snapshot=store.snapshot;drawCards(C,10,{rng:()=>0});
 assert.throws(()=>drawCards(C,10,{rng:()=>1}));assert.equal(data.get(WALLET_KEY),raw);assert.deepEqual(store.snapshot,snapshot);assert.equal(data.size,1);assert.equal(store.snapshot.wallet.balance,3000);
});
