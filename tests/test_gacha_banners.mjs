import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {BANNERS,BANNER_ART,validateBanners} from '../next-stage/gacha/banners.mjs';
import {BannerSelection} from '../next-stage/gacha/banner-selection.mjs';
const tick=()=>new Promise(resolve=>setImmediate(resolve));
function setup(banners=BANNERS,assets=BANNER_ART){
 const renders=[],images=[],loads=[];
 const selection=new BannerSelection({banners,assets,onSelect:(b,changed)=>renders.push([b?.id,changed]),onArt:image=>images.push(image),loadArt:(src,signal)=>new Promise((resolve,reject)=>loads.push({src,signal,resolve,reject}))});
 return {selection,renders,images,loads};
}
test('all display definitions have unique IDs and local original assets',async()=>{
 const result=validateBanners(BANNERS);assert.deepEqual(result.errors,[]);assert.equal(result.banners.length,3);
 assert.deepEqual(BANNERS.map(b=>b.id),['demo-mint','demo-lilac','demo-peach']);
 for(const b of BANNERS){for(const key of ['heroSrc','thumbnailSrc']){
  const svg=await readFile(new URL(BANNER_ART[b.artKey][key]),'utf8');assert.match(svg,/<svg/);assert.doesNotMatch(svg,/<script|<image|href=|<text/i);
 }}
});
test('invalid config reports duplicate IDs, missing fields, missing art and empty lists safely',()=>{
 const x=validateBanners([BANNERS[0],BANNERS[0],null,{...BANNERS[1],themeKey:'bad'},{...BANNERS[2],artKey:'absent'}]);
 assert.equal(x.errors.length,4);assert.deepEqual(x.banners.map(b=>b.id),['demo-mint','demo-peach']);
 assert.equal(validateBanners([]).banners.length,0);assert.ok(validateBanners(null).errors.length);
});
test('first selection; same and unknown IDs do not render or load again',async()=>{
 const x=setup();assert.equal(x.selection.selectedBannerId,'demo-mint');x.selection.setVisible(true);await tick();
 assert.equal(x.renders.length,1);assert.equal(x.loads.length,1);
 assert.equal(x.selection.select('demo-mint'),false);assert.equal(x.selection.select('unknown'),false);
 assert.equal(x.renders.length,1);assert.equal(x.loads.length,1);
});
test('rapid A B C selection ignores out-of-order image successes and failures',async()=>{
 const x=setup();x.selection.setVisible(true);await tick();x.selection.select('demo-lilac');await tick();x.selection.select('demo-peach');await tick();
 x.loads[2].resolve('peach-image');await tick();x.loads[0].resolve('stale-mint');x.loads[1].reject(Error('stale-error'));await tick();
 assert.deepEqual(x.images,['peach-image']);assert.equal(x.selection.selectedBannerId,'demo-peach');
 assert.deepEqual(x.renders.map(r=>r[0]),['demo-mint','demo-lilac','demo-peach']);
 assert.ok(x.loads[0].signal.aborted);assert.ok(x.loads[1].signal.aborted);
});
test('hide cancels pending work; reopening keeps selection and rejects stale completion',async()=>{
 const x=setup();x.selection.setVisible(true);x.selection.select('demo-lilac');await tick();
 x.selection.setVisible(false);assert.ok(x.loads[0].signal.aborted);assert.equal(x.selection.select('demo-peach'),false);
 x.loads[0].resolve('old');await tick();assert.deepEqual(x.images,[]);
 x.selection.setVisible(true);await tick();x.loads[1].resolve('new');await tick();
 assert.equal(x.selection.selectedBannerId,'demo-lilac');assert.deepEqual(x.images,['new']);assert.equal(x.renders.at(-1)[1],false);
});
test('destroy is final and late completion cannot call the view',async()=>{
 const x=setup();x.selection.setVisible(true);await tick();x.selection.destroy();x.loads[0].resolve('old');await tick();
 const n=x.renders.length;x.selection.setVisible(true);assert.equal(x.selection.select('demo-lilac'),false);assert.equal(x.renders.length,n);assert.deepEqual(x.images,[]);
});
test('load failure and missing art preserve selected banner and return a fallback',async()=>{
 const x=setup();x.selection.setVisible(true);await tick();x.loads[0].reject(Error('404'));await tick();
 assert.deepEqual(x.images,[null]);assert.equal(x.selection.selectedBannerId,'demo-mint');
 const missing=setup(BANNERS,{});missing.selection.setVisible(true);assert.deepEqual(missing.images,[null]);assert.equal(missing.renders[0][0],'demo-mint');
});
test('empty catalog has no selected ID, no loading and a safe empty render',()=>{
 const x=setup([]);x.selection.setVisible(true);assert.equal(x.selection.selectedBannerId,null);assert.deepEqual(x.renders,[[undefined,false]]);assert.equal(x.loads.length,0);assert.equal(x.selection.select('demo-mint'),false);
});
test('synchronous loader errors are handled and a fresh page starts on first banner',async()=>{
 const x=setup();x.selection.loadArt=()=>{throw Error('decode failed');};x.selection.setVisible(true);await tick();assert.deepEqual(x.images,[null]);
 x.selection.select('demo-peach');assert.equal(setup().selection.selectedBannerId,'demo-mint');
});
