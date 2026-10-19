// Opt-in diagnostics only (?perf=1). Observes frames; never changes game state.
const output=document.createElement('output');
output.id='performance-check';output.setAttribute('aria-label','성능 진단');
output.style.cssText='position:fixed;bottom:4px;left:4px;z-index:1000;pointer-events:none;max-width:95vw;padding:5px 8px;background:#10182de8;color:#d9fff4;font:11px monospace;white-space:pre-wrap';
document.body.append(output);
const groups=new Map();let last=0,lastScene='',paint=0,pending=[];
const scene=()=>document.querySelector('#settings[open]')?'modal':document.querySelector('#loading[open]')?'loading':!document.querySelector('#play').hidden?(document.querySelector('#count-in').hidden?'play':'ready'):!document.querySelector('#result').hidden?'result':'menu';
const percentile=(a,p)=>a.length?[...a].sort((a,b)=>a-b)[Math.min(a.length-1,Math.floor(a.length*p))]:0;
for(const name of ['keydown','pointerdown'])window.addEventListener(name,e=>{if(e.isTrusted&&pending.length<100)pending.push(performance.now());},{passive:true});
function frame(t){requestAnimationFrame(frame);if(document.hidden){last=0;pending=[];return;}
 const s=scene();if(!groups.has(s))groups.set(s,{frames:[],input:[]});const g=groups.get(s);
 if(last&&lastScene===s){g.frames.push(t-last);if(g.frames.length>3600)g.frames.shift();}
 for(const received of pending){g.input.push(Math.max(0,performance.now()-received));if(g.input.length>200)g.input.shift();}pending=[];last=t;lastScene=s;
 if(t-paint<1000)return;paint=t;
 output.textContent=[...groups].map(([key,v])=>{const mean=v.frames.reduce((a,b)=>a+b,0)/(v.frames.length||1);return `${key}: n=${v.frames.length} FPS=${mean?(1000/mean).toFixed(1):'—'} mean=${mean.toFixed(2)}ms p95=${percentile(v.frames,.95).toFixed(2)}ms >33ms=${v.frames.filter(x=>x>33.34).length} input→RAF p95=${percentile(v.input,.95).toFixed(2)}ms (${v.input.length})`;}).join('\n');
}
requestAnimationFrame(frame);
