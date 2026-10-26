import assert from 'node:assert/strict';
import {Engine,project} from '../next-stage/core.mjs';
// Recording Pixi doubles verify geometry, lifecycle and allocations; not GPU output.
const allocations={canvas:0,texture:0,sprite:0};
class Container{children=[];addChild(...c){this.children.push(...c);}}
class Graphics extends Container{
 commands=[];clear(){this.commands=[];return this;}
}
for(const name of ['poly','rect','moveTo','lineTo','stroke','fill','ellipse','circle','closePath'])Graphics.prototype[name]=function(...args){this.commands.push([name,...args]);return this;};
class Sprite{constructor(texture){allocations.sprite++;this.texture=texture;this.anchor={set(){}};this.position={set:(x,y)=>{this.x=x;this.y=y;}};}}
globalThis.PIXI={Container,Graphics,Sprite,Texture:{from(){allocations.texture++;return {};}},Application:class{stage=new Container();canvas={setAttribute(){}};async init(){}render(){}}};
globalThis.devicePixelRatio=1;
globalThis.document={createElement(){allocations.canvas++;const context=new Proxy({createRadialGradient(){return {addColorStop(){}};},createLinearGradient(){return {addColorStop(){}};}},{get:(o,k)=>o[k]??(()=>{})});return {getContext:()=>context};}};
const {Stage}=await import('../next-stage/renderer.mjs');
const stage=new Stage();await stage.init({append(){}});
assert.deepEqual(project(-.5,1),[38,410,181]);assert.deepEqual(project(3.5,1),[762,410,181]);
const layers=stage.app.stage.children;
assert.ok(layers.indexOf(stage.judgeGlow)<layers.indexOf(stage.ribbon));
assert.ok(layers.indexOf(stage.ribbon)<layers.indexOf(stage.heads));
assert.ok(layers.indexOf(stage.heads)<layers.indexOf(stage.judgeHighlight));
assert.ok(layers.indexOf(stage.diamondBurst)>layers.indexOf(stage.inputHighlight));
assert.equal(stage.lineBody.commands.filter(c=>c[0]==='rect').length,5);
assert.ok(stage.lineBody.commands.some(c=>c[0]==='rect'&&c[2]===448));
assert.ok(stage.lineBody.commands.some(c=>c[0]==='poly'&&c[1][1]===410&&c[1][5]===444));
assert.ok(stage.judgeHighlight.commands.some(c=>c[0]==='stroke'&&c[1].width===2.2));
const staticBody=JSON.stringify(stage.lineBody.commands);
const notes=['TAP','FLICK','HOLD','SLIDE'].map((type,lane)=>({type,lane,time:1,...(lane>1?{end_time:2,end_lane:lane,tick_times:[1,1.5,2]}:{})}));
let engine=new Engine({notes,total:8},true);engine.step(.9);
stage.draw(engine,1,.55,120,0,true);
for(let lane=0;lane<4;lane++)assert.equal(stage.pool.find(s=>s.x===project(lane,1)[0]&&s.y===410)?.y,410);
assert.equal(stage.pool.find(s=>s.y===410).height,78,'Thicker heads keep their arrival anchor');
// Warm note pool before measuring the hot path. Diamonds are fixed at init.
const before={...allocations};
engine.step(1,[['key','down','KeyD',1],['key','down','KeyF',1],['key','down','Space',1],['key','down','KeyJ',1],['key','down','KeyK',1]]);
assert.equal(engine.counts.PERFECT,4);
stage.draw(engine,1,.55,120,0,true);
assert.ok(stage.faceReflection.commands.some(c=>c[0]==='fill'&&c[1].alpha>0));
stage.draw(engine,1.081,.55,120,0,true);
assert.ok(stage.faceReflection.commands.filter(c=>c[0]==='fill').every(c=>c[1].alpha===0));
for(const hz of [60,120])for(let frame=0;frame<30;frame++)stage.draw(engine,1+frame/hz,.55,120,0,true);
assert.deepEqual(allocations,before,'No hot-path canvas/texture/sprite allocations after head warmup');
assert.equal(JSON.stringify(stage.lineBody.commands),staticBody,'Static mesh not rebuilt per frame');
assert.equal(stage.burstPool.length,32);assert.equal(stage.haloPool.length,4);assert.equal(stage.lineDiamonds.length,8);
stage.draw(engine,1.1,.55,120,0,false);
assert.equal(stage.lineGlow.visible,false);assert.equal(stage.diamondBurst.visible,false);
assert.ok(stage.lineDiamonds.every(s=>!s.visible));assert.equal(JSON.stringify(stage.lineBody.commands),staticBody);
assert.equal(stage.faceReflection.commands.length,0);assert.ok(stage.inputHighlight.commands.length>0);
for(const [delta,expected,score] of [[0,'PERFECT',210],[.1,'GREAT',105],[.3,'MISS',0]]){
 const e=new Engine({notes:[{type:'TAP',lane:0,time:1}],total:1});e.step(.9);e.step(1+delta,[['key','down','KeyD',1+delta]]);
 assert.equal(e.counts[expected],1);assert.equal(e.score,score);
}
// Held sustain heads/ticks/tails remain engine-owned; rendering does not award.
engine.step(1.5);engine.step(2);assert.equal(engine.counts.PERFECT,8);assert.equal(engine.counts.MISS,0);
assert.equal(engine.score,200*8+5*8*9);
console.log('PASS: geometry, layers, static body, OFF, 80ms reflection, 60/120Hz hot path, fixed pools, TAP/FLICK/HOLD/SLIDE engine scores');
