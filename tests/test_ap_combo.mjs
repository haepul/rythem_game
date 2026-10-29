import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {PlayHUD,isAPMaintained} from '../next-stage/play-hud.mjs';
import {apScene} from './ap-combo-scenes.mjs';
class Element{
 dataset={};hidden=false;classList={toggle(){}};style={setProperty(){}};animations=[];writes=0;
 set textContent(v){this.text=v;this.writes++;}get textContent(){return this.text;}
 querySelector(){return this.child;}closest(){return this.parent||null;}
 animate(frames,options){const a={frames,options,currentTime:0,cancelled:false,cancel(){this.cancelled=true;}};this.animations.push(a);return a;}
}
function harness(){const els=Object.fromEntries(['score','life','life-fill','life-number','life-flash','song-progress','play-time','combo','judgment'].map(k=>[k,new Element()]));els.combo.child=new Element();els.judgment.child=new Element();els.life.parent=new Element();return new PlayHUD({getElementById:id=>els[id],querySelectorAll:()=>[]});}
for(const [name,counts,combo,ap]of [
 ['ap100',[100,0,0],100,true],['break99',[99,1,0],100,false],['aftergreat',[199,1,0],200,false],['aftermiss',[103,0,1],100,false],['four',[4,0,0],4,true],['mixed',[1,1,0],2,false],['hold-mid',[2,0,0],2,true],['slide',[2,0,0],2,true],['holdmiss',[2,0,1],1,false],['slidemiss',[2,0,1],1,false]
])test(`real Engine cumulative AP: ${name}`,()=>{
 const hud=harness();let lost=false;
 const scene=apScene(name,(e,t)=>{const previous=JSON.stringify(e);hud.update(e,t,300,true);assert.equal(JSON.stringify(e),previous);if(e.counts.GREAT||e.counts.MISS)lost=true;if(lost)assert.equal(hud.el.combo.dataset.ap,'normal');});
 assert.deepEqual(Object.values(scene.engine.counts),counts);assert.equal(scene.engine.combo,combo);assert.equal(isAPMaintained(scene.engine.counts),ap);assert.equal(hud.el.combo.dataset.ap,ap?'maintaining':'normal');
 if(name==='mixed')assert.equal(scene.engine.feedback,'PERFECT','last feedback alone would be wrong');
 if(name==='break99'){assert.equal(hud.animations['ap-change'].options.duration,110);assert.equal(hud.number.textContent,100);}
});
test('fresh song/reset, pause/resume, OFF and cached unchanged updates',()=>{
 const hud=harness(),ap=apScene('ap100'),broken=apScene('aftergreat');
 hud.update(ap.engine,ap.now,300,true);hud.update(broken.engine,broken.now,300,true);const a=hud.animations['ap-change'];
 hud.update(broken.engine,broken.now,300,false);assert.equal(a.cancelled,true);assert.equal(hud.el.combo.dataset.motion,'off');assert.equal(hud.el.combo.dataset.ap,'normal');
 const writes=hud.number.writes;for(let i=0;i<120;i++)hud.update(broken.engine,broken.now,300,false);assert.equal(hud.number.writes,writes);
 hud.update(broken.engine,broken.now+.2,300,true);assert.equal(hud.el.combo.dataset.ap,'normal');
 hud.reset();assert.equal(hud.el.combo.hidden,true);hud.update(ap.engine,ap.now,300,true);assert.equal(hud.el.combo.dataset.ap,'maintaining');
 hud.update(ap.engine,ap.now,300,false);assert.equal(hud.el.combo.dataset.ap,'maintaining');assert.equal(hud.el.combo.dataset.motion,'off');
});
test('unknown/missing/invalid cumulative results never imply AP; GOOD/BAD disqualify',()=>{
 for(const c of [null,{}, {PERFECT:0,GREAT:0,MISS:0},{PERFECT:100,GREAT:NaN,MISS:0},{PERFECT:1,GREAT:-1,MISS:0},{PERFECT:1,GREAT:0,MISS:0,GOOD:1},{PERFECT:1,GREAT:0,MISS:0,BAD:1},{PERFECT:1,GREAT:0,MISS:0,UNKNOWN:1}])assert.equal(isAPMaintained(c),false);
});
test('actual MASTER cumulative misses cannot regain AP; presentation has no engine effects',()=>{
 const master=JSON.parse(readFileSync(new URL('../next-stage/data/21-master-full.json',import.meta.url)));const hud=harness();let lost=false,updates=0;
 apScene('master',(e,t)=>{const before=JSON.stringify([e.score,e.combo,e.hp,e.counts]);hud.update(e,t,master.duration,false);assert.equal(JSON.stringify([e.score,e.combo,e.hp,e.counts]),before);if(e.counts.MISS)lost=true;if(lost)assert.equal(hud.el.combo.dataset.ap,'normal');updates++;},master);assert.ok(lost&&updates>100);
});
