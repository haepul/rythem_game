// Deterministic input schedules, evaluated by the unmodified production Engine.
import {Engine} from '../next-stage/core.mjs';
const keys=['KeyD','KeyF','KeyJ','KeyK'];
export function judgmentScene(name,observe=()=>{},master=null){
 let notes=[{type:'TAP',lane:1,time:1}],events=[],end=1,steps=[];
 const down=(lane,t)=>['key','down',keys[lane],t],up=(lane,t)=>['key','up',keys[lane],t];
 if(name==='master'){
  const e=new Engine(master,true);for(let t=0;t<183;t+=1/120){e.step(t);observe(e,t);}
  e.step(183.17);observe(e,183.17);return {engine:e,now:183.17};
 }
 if(name==='great'){end=1.1;events=[down(1,end)];}
 else if(name==='miss'){end=1.17;}
 else if(name==='flick'){notes[0].type='FLICK';events=[down(1,1),['key','down','Space',1]];}
 else if(name.startsWith('hold')||name==='slide'){
  notes=[{type:name==='slide'?'SLIDE':'HOLD',lane:1,end_lane:name==='slide'?2:1,time:1,end_time:2,tick_times:[1,1.5,2]}];
  steps=[[1,[down(1,1)]]];end=name==='hold-head'?1:name==='hold-mid'||name==='slide'?1.5:2;
  if(name==='slide')steps.push([1.5,[down(2,1.45)]]);
  else if(end>1)steps.push([end,[]]);
 }
 else if(name==='four'){notes=keys.map((_,lane)=>({type:'TAP',lane,time:1}));events=keys.map((_,lane)=>down(lane,1));}
 else if(name==='dense'||name==='perfect-great'||name==='great-miss'){
  const count=name==='dense'?40:2;notes=Array.from({length:count},(_,i)=>({type:'TAP',lane:i%4,time:1+i*.05}));
  if(name==='dense')steps=notes.map(n=>[n.time,[up(n.lane,n.time-.001),down(n.lane,n.time)]]);
  else if(name==='perfect-great')steps=[[1,[down(0,1)]],[1.15,[down(1,1.15)]]];
  else steps=[[1.1,[down(0,1.1)]],[1.22,[]]];
  end=steps.at(-1)[0];
 } else events=[down(1,1)];
 const total=notes.reduce((n,x)=>n+(x.tick_times?.length||1),0),engine=new Engine({notes,total},true);
 engine.step(.9);observe(engine,.9);
 for(const [t,input] of steps.length?steps:[[end,events]]){engine.step(t,input);observe(engine,t);}
 const now=end+.055;engine.step(now);observe(engine,now);return {engine,now};
}
