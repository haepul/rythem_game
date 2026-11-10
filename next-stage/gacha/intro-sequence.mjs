// Project presentation timing, not an official game's timing. No DOM/storage/RNG.
export const INTRO_TIMING=Object.freeze({entering:350,gathering:650,revealing:450});
const freeze=value=>{if(value&&typeof value==='object'){Object.values(value).forEach(freeze);Object.freeze(value);}return value;};
export function createIntroSequence({onStage=()=>{},onFinish=()=>{},onError=()=>{},timing=INTRO_TIMING,schedule=setTimeout,unschedule=clearTimeout}={}){
 let serial=0,run=null,destroyed=false,state='idle';
 const report=e=>{try{onError(e);}catch{}};
 function clean(r){if(r.timer!==null){unschedule(r.timer);r.timer=null;}const cleanup=r.cleanup;r.cleanup=null;try{cleanup?.();}catch(e){report(e);}}
 function finish(r,reason,present=true){
  if(!r||r.done||run!==r)return;
  r.done=true;state='finished';clean(r);
  try{onFinish(r.receipt,{reason,present,id:r.id});}catch(e){report(e);}
 }
 function step(r,index){
  if(destroyed||run!==r||r.done)return;
  clean(r);
  const phase=['entering','gathering','revealing'][index];
  if(!phase){finish(r,'complete');return;}
  state=phase;
  try{
   const duration=timing[phase];if(!Number.isFinite(duration)||duration<0)throw new Error('Invalid intro timing');
   const cleanup=onStage(phase,r.receipt,{id:r.id,duration,fail:e=>{if(run===r&&!r.done){report(e);finish(r,'error');}}});
   if(run!==r||r.done||destroyed){cleanup?.();return;}
   r.cleanup=cleanup;
   // Authoritative deadline: never wait for animationend / WAAPI finished.
   r.timer=schedule(()=>{if(run===r&&!r.done&&!destroyed){r.timer=null;step(r,index+1);}},duration);
  }catch(e){report(e);finish(r,'error');}
 }
 return {
  get active(){return !!run&&!run.done;},get state(){return state;},
  start(receipt,{changed=true,enabled=true}={}){
   if(destroyed)return false;
   finish(run,'replaced',false);
   if(!receipt?.request?.requestId||!Array.isArray(receipt.results))throw new TypeError('A committed receipt is required');
   run={id:++serial,receipt:freeze(structuredClone(receipt)),done:false,timer:null,cleanup:null};
   if(!changed||!enabled)finish(run,!changed?'restored':'reduced-motion');else step(run,0);
   return true;
  },
  skip(){finish(run,'skip');},hide(){finish(run,'hidden',false);},
  syncMotion(enabled){if(!enabled)finish(run,'reduced-motion');},
  destroy(){if(destroyed)return;destroyed=true;finish(run,'destroyed',false);}
 };
}
