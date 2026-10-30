import {project,clamp} from './core.mjs';
import {NOTE_PALETTE} from './note-palette.mjs';

const palette=Object.fromEntries(['HOLD','SLIDE'].map(type=>[type,Object.fromEntries(
 ['body','core','highlight','glow'].map(key=>[key,Number(NOTE_PALETTE[type][key].replace('#','0x'))]))]));
const ease=t=>t*t*(3-2*t);
export const RIBBON_TRANSITION=.06;
// Renderer-owned state; engine notes/judges are never mutated. Audio time is the
// only clock, so pause freezes both the response and the travelling highlight.
export function ribbonActivation(stage,n,now,effects){
 const states=stage.ribbonLights??=new WeakMap(),target=n.active?1:0;
 let state=states.get(n);
 if(!state){state={from:0,to:target,at:now,last:now};states.set(n,state);}
 if(!effects||now<state.last){state.from=state.to=target;state.at=now;state.last=now;return target;}
 const value=state.from+(state.to-state.from)*ease(clamp((now-state.at)/RIBBON_TRANSITION,0,1));
 if(state.to!==target){state.from=value;state.to=target;state.at=now;}
 state.last=now;return value;
}
function strip(g,points,fraction,tint,alpha){
 g.moveTo(points[0]-points[2]*fraction,points[1]);
 for(let i=1;i<=24;i++)g.lineTo(points[i*3]-points[i*3+2]*fraction,points[i*3+1]);
 for(let i=24;i>=0;i--)g.lineTo(points[i*3]+points[i*3+2]*fraction,points[i*3+1]);
 g.closePath().fill({color:tint,alpha});
}
function edge(g,points,side,tint,alpha){
 g.moveTo(points[0]+side*points[2]*.38,points[1]);
 for(let i=1;i<=24;i++)g.lineTo(points[i*3]+side*points[i*3+2]*.38,points[i*3+1]);
 for(let i=24;i>=0;i--){const k=i*3,w=points[k+2];g.lineTo(points[k]+side*(w*.38-(.6+w*.006)),points[k+1]);}
 g.closePath().fill({color:tint,alpha});
}

export function drawSustainRibbon(stage,n,a,b,now,approach,effects){
 const g=stage.ribbon,pts=stage.ribbonPoints??=new Float64Array(75);
 const p=palette[n.type],opacity=stage.longOpacity??.7;
 const active=ribbonActivation(stage,n,now,effects);
 // Keep all 25 sample times, the exact judge path, widths and visible endpoints.
 for(let i=0;i<=24;i++){
  const t=a+(b-a)*i/24,l=n.type==='SLIDE'?n.judge.position(t):n.lane;
  const [x,y,w]=project(l,1-(t-now)/approach);
  pts[i*3]=x;pts[i*3+1]=y;pts[i*3+2]=w;
 }
 if(effects)strip(g,pts,.41,p.glow,(.025+.025*active)*opacity);
 strip(g,pts,.38,p.body,(.25+.08*active)*opacity);
 strip(g,pts,.22,p.core,(.10+.17*active)*opacity);
 strip(g,pts,.065,p.highlight,(.045+.10*active)*opacity);
 for(const side of [-1,1])edge(g,pts,side,p.highlight,.24+(.46+.2*active)*opacity);
 if(!effects||active<=0)return;
 // One tapered patch along the sampled path, rather than a detached crossbar.
 // Endpoint attenuation leaves the existing head textures in front and readable.
 const phase=((now-n.time)*.65%1+1)%1;
 const start=Math.max(2,Math.floor((phase-.12)*24)),end=Math.min(22,Math.ceil((phase+.12)*24));
 if(end>start){
  g.moveTo(pts[start*3],pts[start*3+1]);
  for(let i=start;i<=end;i++){const k=i*3,pulse=Math.max(0,1-Math.abs(i/24-phase)/.12);g.lineTo(pts[k]-pts[k+2]*.17*pulse,pts[k+1]);}
  for(let i=end;i>=start;i--){const k=i*3,pulse=Math.max(0,1-Math.abs(i/24-phase)/.12);g.lineTo(pts[k]+pts[k+2]*.17*pulse,pts[k+1]);}
  g.closePath().fill({color:p.highlight,alpha:active*opacity*.12});
 }
 // The first sample is on Y=410 only after the note has reached the deck.
 // It is drawn in the ribbon layer, behind every note head and diamond effect.
 if(a===now&&Math.abs(pts[1]-410)<.001){
  const x=pts[0],y=pts[1],w=pts[2],light=active*opacity*clamp((b-a)/.12,0,1);
  g.ellipse(x,y,w*.32,5).fill({color:p.glow,alpha:.09*light});
  g.moveTo(x-w*.27,y).lineTo(x+w*.27,y).stroke({color:p.highlight,width:2,alpha:.32*light});
 }
}
