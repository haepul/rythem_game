import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {PlayHUD,JUDGMENT_DURATION} from '../next-stage/play-hud.mjs';
import {judgmentScene} from './judgment-text-scenes.mjs';
class Element {
 dataset={};hidden=false;writes=0;value='';classList={toggle(){}};style={setProperty(){}};animations=[];text='';
 set textContent(value){this.text=value;this.writes++;} get textContent(){return this.text;}
 querySelector(){return this.child;} closest(){return this.parent||null;}
 animate(frames,options){const animation={frames,options,currentTime:0,cancelled:false,cancel(){this.cancelled=true;}};this.animations.push(animation);return animation;}
}
function harness(){
 const els=Object.fromEntries(['score','life','life-fill','life-number','life-flash','song-progress','play-time','combo','judgment'].map(k=>[k,new Element()]));
 els.judgment.child=new Element();els.combo.child=new Element();els.life.parent=new Element();
 const root={getElementById:id=>els[id],querySelectorAll:()=>Array.from({length:4},()=>new Element())};
 return {hud:new PlayHUD(root),els,text:els.judgment.child};
}
for(const [name,grade,counts] of [
 ['perfect','PERFECT',[1,0,0]],['great','GREAT',[0,1,0]],['miss','MISS',[0,0,1]],['flick','PERFECT',[1,0,0]],
 ['hold-head','PERFECT',[1,0,0]],['hold-mid','PERFECT',[2,0,0]],['hold-tail','PERFECT',[3,0,0]],['slide','PERFECT',[2,0,0]],
 ['four','PERFECT',[4,0,0]],['dense','PERFECT',[40,0,0]],['perfect-great','GREAT',[1,1,0]],['great-miss','MISS',[0,1,1]]]){
 test(`Engine → full PlayHUD: ${name}`,()=>{
  const {hud,els,text}=harness();const scene=judgmentScene(name,(e,t)=>hud.update(e,t,200,true));
  assert.deepEqual(Object.values(scene.engine.counts),counts);
  assert.equal(text.textContent,grade);assert.equal(els.judgment.dataset.grade,grade);assert.equal(els.judgment.hidden,false);
  assert.ok(text.animations.filter(a=>!a.cancelled).length<=1);
  assert.equal(els.judgment.animations.length,0,'position wrapper is never animated');
  const before=JSON.stringify(scene.engine);hud.update(scene.engine,scene.now+.01,200,true);assert.equal(JSON.stringify(scene.engine),before,'HUD cannot award or mutate');
 });
}
test('360ms lifetime matches at 60 and 120Hz; no delayed old grade or animation',()=>{
 for(const hz of [60,120]){
  const {hud,els,text}=harness(),{engine}=judgmentScene('perfect');
  for(let frame=0;frame<=hz*.5;frame++){const now=engine.feedbackAt+frame/hz;hud.updateJudgment(engine,now,true);assert.equal(els.judgment.hidden,(now-engine.feedbackAt)*1000>=JUDGMENT_DURATION);}
  assert.equal(text.textContent,'');assert.equal(text.animations.length,1);assert.equal(text.animations[0].cancelled,true);
 }
});
test('effects OFF cancels current animation, keeps readable grade; ON uses remaining age',()=>{
 const {hud,text}=harness(),{engine}=judgmentScene('perfect');
 hud.updateJudgment(engine,1,true);hud.updateJudgment(engine,1.1,false);assert.equal(text.textContent,'PERFECT');assert.equal(text.animations[0].cancelled,true);
 hud.updateJudgment(engine,1.2,true);assert.equal(text.animations.length,2);assert.ok(Math.abs(hud.animations.judgment.currentTime-200)<.01);
 hud.updateJudgment(engine,1.4,false);assert.equal(text.textContent,'');
});
test('late HUD sampling seeks into pulse; pause drift recovers without allocating',()=>{
 const {hud}=harness(),{engine}=judgmentScene('great');hud.updateJudgment(engine,1.13,true);
 const animation=hud.animations.judgment;assert.ok(Math.abs(animation.currentTime-30)<.01);
 animation.currentTime=360;hud.updateJudgment(engine,1.14,true);assert.equal(hud.animations.judgment,animation);assert.ok(Math.abs(animation.currentTime-40)<.01);
});
test('idle writes are cached, restart cancels and same event time can display again',()=>{
 const {hud,text,els}=harness(),{engine}=judgmentScene('perfect');hud.updateJudgment(engine,1,true);const writes=text.writes;
 for(let i=0;i<100;i++)hud.updateJudgment(engine,1.05,true);assert.equal(text.writes,writes);assert.equal(text.animations.length,1);
 hud.reset();assert.equal(els.judgment.hidden,true);assert.equal(text.textContent,'');assert.equal(text.animations[0].cancelled,true);
 hud.updateJudgment(engine,1,true);assert.equal(text.textContent,'PERFECT');assert.equal(text.animations.length,2);
});
test('empty or future feedback is not fabricated; MISS creates no success sparks',()=>{
 const {hud,text}=harness(),{engine}=judgmentScene('miss');assert.equal(engine.sparks.length,0);
 hud.updateJudgment(engine,.5,true);assert.equal(text.textContent,'');hud.updateJudgment(engine,1.2,true);assert.equal(text.textContent,'MISS');
});
test('actual MASTER chart latest engine result and stats remain authoritative',()=>{
 const master=JSON.parse(readFileSync(new URL('../next-stage/data/21-master-full.json',import.meta.url)));
 const {hud,text}=harness();let checked=0;
 const {engine}=judgmentScene('master',(e,t)=>{const before=JSON.stringify([e.score,e.combo,e.hp,e.counts]);hud.update(e,t,master.duration,true);assert.equal(JSON.stringify([e.score,e.combo,e.hp,e.counts]),before);if(!hud.el.judgment.hidden){assert.equal(text.textContent,e.feedback);checked++;}},master);
 assert.ok(checked>100);assert.ok(engine.counts.MISS>0);assert.ok(text.animations.filter(a=>!a.cancelled).length<=1);
});
