import assert from 'node:assert/strict';
import test from 'node:test';
import {ribbonActivation} from '../next-stage/ribbon-light.mjs';
import {drawRibbonBefore} from './fixtures/ribbon-before.mjs';
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

const make=async()=>{const s=new Stage();await s.init({append(){}});return s;};
const note=(type,lane=1,end_lane=3)=>({type,lane,end_lane,time:1,end_time:2.4,tick_times:[1,1.7,2.4]});
for(const type of ['HOLD','SLIDE'])for(const opacity of [.1,.7,1])test(type+' path and opacity '+opacity,async()=>{
 const s=await make(),before=await make(),e=new Engine({notes:[note(type)],total:3},true),n=e.notes[0];s.longOpacity=before.longOpacity=opacity;
 const data=JSON.stringify(e);drawRibbonBefore.call(before,n,1,1.85,.85,1,true);s.drawRibbon(n,1,1.85,.85,1,true);
 assert.deepEqual(s.ribbonPoints,before.ribbonPoints);assert.equal(s.ribbonPoints.length,75);assert.equal(JSON.stringify(e),data);
 const fills=s.ribbon.commands.filter(c=>c[0]==='fill');assert.equal(fills.length,6);assert.ok(fills.every(c=>c[1].alpha>=0&&c[1].alpha<=.9));assert.ok(fills.at(-1)[1].alpha>=.28);
 const points=s.ribbonPoints;s.ribbon.clear();s.drawRibbon(n,1,1.85,.85,1,false);assert.equal(s.ribbonPoints,points);assert.equal(s.ribbon.commands.filter(c=>c[0]==='fill').length,5);assert.equal(s.ribbon.commands.filter(c=>c[0]==='ellipse').length,0);
});
test('60ms response, release, frozen audio time, frame-rate independence and OFF',()=>{
 for(const hz of [60,120]){const s={},n={active:false};assert.equal(ribbonActivation(s,n,1,true),0);n.active=true;assert.equal(ribbonActivation(s,n,1,true),0);
  for(let i=1;i<=Math.floor(hz*.03);i++)ribbonActivation(s,n,1+i/hz,true);
  assert.ok(Math.abs(ribbonActivation(s,n,1.03,true)-.5)<1e-8);assert.equal(ribbonActivation(s,n,1.06,true),1);assert.equal(ribbonActivation(s,n,1.06,true),1);
  n.active=false;assert.equal(ribbonActivation(s,n,1.06,true),1);assert.ok(Math.abs(ribbonActivation(s,n,1.09,true)-.5)<1e-8);assert.equal(ribbonActivation(s,n,1.12,true),0);
  n.active=true;assert.equal(ribbonActivation(s,n,1.12,false),1);assert.equal(ribbonActivation(s,n,.5,true),1);
 }
});
for(const type of ['HOLD','SLIDE'])test(type+' real Engine keyboard/touch release, rejoin, tail and rendering purity',async()=>{
 const e=new Engine({notes:[note(type)],total:3},true),s=await make(),n=e.notes[0];e.step(.95);
 const inputs=type==='HOLD'?[['key','down','KeyF',1]]:[['touch','down','a',project(1,1)[0],410,1]];
 e.step(1,inputs);e.step(1.02);assert.equal(n.active,true);s.draw(e,1.02,1,120,0,true);s.draw(e,1.08,1,120,0,true);
 assert.ok(s.ribbon.commands.some(c=>c[0]==='ellipse'&&c[2]===410));
 e.step(1.1,type==='HOLD'?[['key','up','KeyF',1.1]]:[['touch','up','a',project(1,1)[0],410,1.1]]);assert.equal(n.active,false);
 s.draw(e,1.1,1,120,0,true);s.draw(e,1.17,1,120,0,true);assert.ok(!s.ribbon.commands.some(c=>c[0]==='ellipse'));
 for(let t=1.2;t<2.4;t+=.01){const x=project(n.judge.position(t),1)[0];e.step(t,type==='HOLD'?(t===1.2?[['key','down','KeyF',t]]:[]):[['touch',t===1.2?'down':'move','b',x,410,t]]);}
 assert.equal(n.active,true);const state=JSON.stringify(e);s.draw(e,2.39,1,120,0,true);assert.equal(JSON.stringify(e),state);
 const commands=JSON.stringify(s.ribbon.commands);s.draw(e,2.39,1,120,0,true);assert.equal(JSON.stringify(s.ribbon.commands),commands,'Pause freezes ribbon lighting');
 e.step(2.4);assert.equal(n.hit,true);assert.equal(n.judge.tail_hit,true);
});
test('straight and reverse slides keep exact 25 judge samples',async()=>{
 for(const [lane,end_lane] of [[1,1],[0,3],[3,0]]){const s=await make(),b=await make(),e=new Engine({notes:[note('SLIDE',lane,end_lane)],total:3},true),n=e.notes[0];drawRibbonBefore.call(b,n,1.5,2.4,1.5,1,true);s.drawRibbon(n,1.5,2.4,1.5,1,true);assert.deepEqual(s.ribbonPoints,b.ribbonPoints);}
});
test('dense overlaps reuse points and warm texture/sprite pools; heads remain above ribbons',async()=>{
 const notes=Array.from({length:32},(_,i)=>note(i%2?'SLIDE':'HOLD',i%4,(i+1)%4));notes.push({type:'TAP',lane:0,time:1.5},{type:'FLICK',lane:3,time:1.5});
 const e=new Engine({notes,total:98},true),s=await make();e.step(1.1,[['key','down','KeyD',1],['key','down','KeyF',1],['key','down','KeyJ',1],['key','down','KeyK',1]]);s.draw(e,1.1,1,120,0,true);
 const points=s.ribbonPoints,pool={...allocations},engine=JSON.stringify(e);for(let i=0;i<20;i++)s.draw(e,1.1+i/120,1,120,0,true);
 assert.deepEqual(allocations,pool);assert.equal(s.ribbonPoints,points);assert.equal(JSON.stringify(e),engine);
 assert.ok(s.app.stage.children.indexOf(s.ribbon)<s.app.stage.children.indexOf(s.heads));assert.equal(s.burstPool.length,32);assert.equal(s.haloPool.length,4);
});
