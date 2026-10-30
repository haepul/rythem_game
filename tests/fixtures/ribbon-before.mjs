import {NOTE_PALETTE} from '../../next-stage/note-palette.mjs';
import {project} from '../../next-stage/core.mjs';
// Exact pre-change method from 3d1180b, used only by comparison tests.
export function drawRibbonBefore(n,a,b,now,approach,effects){
 const r=this.ribbon,pts=this.ribbonPoints??=(new Float64Array(75));
 const c=Number(NOTE_PALETTE[n.type].body.replace('#','0x')),opacity=this.longOpacity??.7;
 for(let i=0;i<=24;i++){
 const t=a+(b-a)*i/24,l=n.type==='SLIDE'?n.judge.position(t):n.lane;
 const [x,y,w]=project(l,1-(t-now)/approach);
 pts[i*3]=x;pts[i*3+1]=y;pts[i*3+2]=w;
 }
 const strip=(fraction,alpha)=>{
 r.moveTo(pts[0]-pts[2]*fraction,pts[1]);
 for(let i=1;i<=24;i++)r.lineTo(pts[i*3]-pts[i*3+2]*fraction,pts[i*3+1]);
 for(let i=24;i>=0;i--)r.lineTo(pts[i*3]+pts[i*3+2]*fraction,pts[i*3+1]);
 r.closePath().fill({color:c,alpha:alpha*opacity});
 };
 if(effects)strip(.41,.045);strip(.38,n.active?.34:.23);strip(.24,n.active?.16:.10);strip(.025,n.active?.13:.07);
 for(const side of [-1,1]){
 r.moveTo(pts[0]+side*pts[2]*.38,pts[1]);
 for(let i=1;i<=24;i++)r.lineTo(pts[i*3]+side*pts[i*3+2]*.38,pts[i*3+1]);
 r.stroke({color:c,width:1.25,alpha:(n.active?.9:.72)*opacity});
 }
 if(effects&&n.active){
 const t=a+((now*.45)%1)*(b-a),[x,y,w]=project(n.judge.position(t),1-(t-now)/approach);
 r.moveTo(x-w*.3,y).lineTo(x+w*.3,y).stroke({color:0xffffff,alpha:.28,width:1.5});
 }
 }
