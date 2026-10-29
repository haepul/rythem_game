import {Engine} from '../next-stage/core.mjs';
import {judgmentScene} from './judgment-text-scenes.mjs';
const keys=['KeyD','KeyF','KeyJ','KeyK'];
export function apScene(name='ap100',observe=()=>{},master){
 if(['four','hold-mid','slide','master'].includes(name))return judgmentScene(name,observe,master);
 if(name==='mixed'){
  const engine=new Engine({notes:[{type:'TAP',lane:0,time:1},{type:'TAP',lane:1,time:1.1}],total:2},true);
  engine.step(.9);engine.step(1.1,[['key','down','KeyD',1.1],['key','down','KeyF',1.1]]);observe(engine,1.1);
  return {engine,now:1.155};
 }
 if(name==='holdmiss'||name==='slidemiss'){
  const engine=new Engine({notes:[{type:name==='holdmiss'?'HOLD':'SLIDE',lane:0,end_lane:0,time:1,end_time:2,tick_times:[1,1.5,2]}],total:3},true);
  for(const [t,events]of [[1,[['key','down','KeyD',1]]],[1.3,[['key','up','KeyD',1.3]]],[1.5,[]],[1.51,[['key','down','KeyD',1.51]]],[2,[]]]){engine.step(t,events);observe(engine,t);}
  return {engine,now:2.055};
 }
 const count=name==='aftergreat'?200:name==='aftermiss'?104:100;
 // Leave real future notes: this is AP maintenance during play, not completion.
 const notes=Array.from({length:count+16},(_,i)=>({type:'TAP',lane:i%4,time:1+i*.25}));
 const engine=new Engine({notes,total:notes.length},true);let now=0;
 for(let i=0;i<count;i++){
  const n=notes[i],miss=name==='aftermiss'&&i===3,great=(name==='break99'||name==='aftergreat')&&i===99;
  now=n.time+(miss?.17:great?.1:0);
  const events=miss?[]:[['key','up',keys[n.lane],now-.001],['key','down',keys[n.lane],now]];
  engine.step(now,events);observe(engine,now);
 }
 return {engine,now:now+.055};
}
