import {test} from 'node:test';
import assert from 'node:assert/strict';
import {project,Engine} from '../next-stage/core.mjs';
import {drawBeatGuidesBefore} from './fixtures/beat-guide-before.mjs';
// Install existing recording Pixi doubles and run the existing geometry regression too.
await import('./test_judgment_3d.mjs');
const {Stage}=await import('../next-stage/renderer.mjs');
function recording(){return {segments:[],clear(){this.segments=[];return this;},moveTo(x,y){this.from=[x,y];return this;},lineTo(x,y){this.to=[x,y];return this;},stroke(style){this.segments.push({from:this.from,to:this.to,...style});return this;}};}
function run(now,approach,bpm,offset,effects=true,before=false){
 const context={grid:recording(),beatReflection:0xb1e0da};
 (before?drawBeatGuidesBefore:Stage.prototype.drawBeatGuides).call(context,now,approach,bpm,offset,effects);
 return context.grid.segments;
}
const core=lines=>lines.filter(s=>s.color===0xc5c9e9);
for(const bpm of [60,120,180,240])for(const approach of [.35,.55,1])test(`${bpm} BPM / approach ${approach}: identical original beat coordinates`,()=>{
 for(const offset of [0,.09287981859410431,-.17])for(const now of [-2,-.001,0,.125,.5,.999999,1,1.000001,2.13,200]){
  const before=run(now,approach,bpm,offset,true,true),after=core(run(now,approach,bpm,offset));
  assert.deepEqual(after.map(({from,to})=>[from,to]),before.map(({from,to})=>[from,to]));
  for(const s of after){assert.ok(s.from[1]>=110&&s.from[1]<=410);assert.ok(s.from[0]>=38&&s.to[0]<=762);assert.ok(s.alpha>=0&&s.alpha<=.16);}
 }
});
test('60/120Hz and pause/resume histories resolve the same audio timestamp',()=>{
 const a={grid:recording()},b={grid:recording()};
 for(let i=0;i<=120;i++)Stage.prototype.drawBeatGuides.call(a,i/60,1,240,.09,true);
 for(let i=0;i<=240;i++)Stage.prototype.drawBeatGuides.call(b,i/120,1,240,.09,true);
 assert.deepEqual(a.grid.segments,b.grid.segments);
 const paused=structuredClone(a.grid.segments);
 for(let i=0;i<20;i++)Stage.prototype.drawBeatGuides.call(a,2,1,240,.09,true);
 assert.deepEqual(a.grid.segments,paused);
 Stage.prototype.drawBeatGuides.call(a,2.18,1,240,.09,true);
 assert.deepEqual(a.grid.segments,run(2.18,1,240,.09));
});
test('depth increases core width/alpha until deck attenuation; zero at deck/horizon',()=>{
 const at=p=>core(run(0,1,60,1-p))[0];
 const far=at(.2),middle=at(.55),near=at(.94);
 assert.ok(far.width<middle.width&&middle.width<near.width);
 assert.ok(far.alpha<middle.alpha&&middle.alpha<near.alpha);
 assert.ok(at(.995).alpha<near.alpha*.1);assert.equal(at(1).alpha,0);assert.equal(at(0).alpha,0);
 assert.deepEqual(project(-.5,1),[38,410,181]);
});
test('no invented downbeat emphasis; effects OFF keeps all core lines',()=>{
 assert.deepEqual(run(1.25,1,120,0),run(3.25,1,120,0));
 assert.deepEqual(core(run(1.25,1,120,0)),run(1.25,1,120,0,false));
});
test('pathological density remains bounded and still uses actual beat coordinates',()=>{
 const lines=core(run(0,100,24000,0));assert.ok(lines.length<=32);assert.ok(lines.length>0);
 for(const s of lines){const p=Math.pow((s.from[1]-110)/300,1/1.55),time=100*(1-p),beatIndex=time/(60/24000);assert.ok(Math.abs(beatIndex-Math.round(beatIndex))<1e-7);}
 for(const values of [[NaN,1,120,0],[0,0,120,0],[0,1,0,0],[0,1,Infinity,0],[0,1,120,NaN],[0,-1,120,0]])assert.deepEqual(run(...values),[]);
});
test('full Stage integration keeps all non-grid geometry and Engine state unchanged',async()=>{
 const before=new Stage(),after=new Stage();await before.init({append(){}});await after.init({append(){}});before.drawBeatGuides=drawBeatGuidesBefore;
 const notes=[{type:'TAP',lane:0,time:1.3},{type:'FLICK',lane:1,time:1.2},{type:'HOLD',lane:2,time:1,end_time:2,tick_times:[1,1.5,2]},{type:'SLIDE',lane:3,end_lane:0,time:1,end_time:2,tick_times:[1,1.5,2]}];
 const engine=new Engine({notes,total:8},true);engine.step(.9);engine.step(1,[['key','down','KeyJ',1],['key','down','KeyK',1]]);engine.step(1.05);const state=JSON.stringify(engine);
 for(const effects of [true,false]){
  before.draw(engine,1.05,.55,180,0,effects);after.draw(engine,1.05,.55,180,0,effects);
  for(const name of ['track','ribbon','lineBody','judgeHighlight','inputHighlight','fx'])assert.deepEqual(after[name].commands,before[name].commands,name);
  assert.deepEqual(after.pool.map(s=>[s.x,s.y,s.width,s.height,s.visible]),before.pool.map(s=>[s.x,s.y,s.width,s.height,s.visible]));
  assert.equal(JSON.stringify(engine),state);
 }
 const layers=after.app.stage.children;assert.ok(layers.indexOf(after.grid)<layers.indexOf(after.judgeGlow));assert.ok(layers.indexOf(after.grid)<layers.indexOf(after.ribbon));
});
