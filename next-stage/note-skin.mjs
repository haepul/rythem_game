import {NOTE_PALETTE} from './note-palette.mjs';
// Authored geometry only; generated once per Stage, never inside draw().
export function noteTexture(P,kind,critical=false){
 const p=NOTE_PALETTE[critical?'CRITICAL':kind],c=document.createElement('canvas');c.width=512;c.height=192;
 const x=c.getContext('2d');x.scale(2,2);
 const path=points=>{x.beginPath();x.moveTo(points[0],points[1]);for(let i=2;i<points.length;i+=2)x.lineTo(points[i],points[i+1]);x.closePath();};
 if(kind==='TRACE'){
  path([128,43,164,61,128,80,92,61]);x.shadowColor=p.glow;x.shadowBlur=7;x.fillStyle=p.body;x.fill();x.shadowBlur=0;
  path([128,43,128,62,92,61]);x.fillStyle=p.highlight;x.fill();path([128,62,164,61,128,80]);x.fillStyle=p.rim;x.fill();
  path([128,43,164,61,128,80,92,61]);x.strokeStyle=p.highlight;x.lineWidth=1.2;x.stroke();return P.Texture.from(c);
 }
 const sustain=kind==='HOLD'||kind==='SLIDE';
 const shape=[10,44,246,44,250,49,250,77,245,82,11,82,6,77,6,49];
 path(shape);x.fillStyle=p.shadow;x.shadowColor=p.glow;x.shadowBlur=6;x.fill();x.shadowBlur=0;
 path([10,44,246,44,247,48,247,76,9,76,9,48]);
 const g=x.createLinearGradient(0,44,0,78);g.addColorStop(0,p.highlight);g.addColorStop(.15,p.body);g.addColorStop(.43,p.core);g.addColorStop(.60,p.core);g.addColorStop(1,p.body);x.fillStyle=g;x.fill();
 x.strokeStyle=p.rim;x.lineWidth=1.2;x.stroke();
 x.fillStyle=p.core;x.fillRect(17,56,222,9);x.fillStyle='#ffffffdf';x.fillRect(17,57,222,4);
 x.fillStyle=p.highlight;x.fillRect(12,45,232,2);x.fillStyle=p.shadow;x.fillRect(11,78,234,3);
 // Colored end caps and a small inset highlight distinguish the material.
 x.fillStyle=p.rim;x.fillRect(11,49,sustain?9:6,23);x.fillRect(sustain?236:239,49,sustain?9:6,23);
 x.fillStyle=p.highlight;x.fillRect(13,50,3,7);x.fillRect(240,50,3,7);
 if(kind==='SLIDE'){path([117,69,128,63,139,69,128,75]);x.fillStyle=p.highlight;x.fill();}
 if(kind==='HOLD'){x.fillStyle=p.highlight;x.fillRect(120,68,16,3);}
 if(critical){for(const xx of [28,228]){path([xx,49,xx+3,53,xx,57,xx-3,53]);x.fillStyle=p.highlight;x.fill();}}
 if(kind==='FLICK'){
  path([82,31,128,4,174,31,160,38,128,20,96,38]);x.shadowColor=p.shadow;x.shadowBlur=3;x.fillStyle=p.rim;x.fill();x.shadowBlur=0;
  path([88,30,128,8,168,30,160,33,128,16,96,33]);const arrow=x.createLinearGradient(0,8,0,33);arrow.addColorStop(0,'#ffffff');arrow.addColorStop(1,p.highlight);x.fillStyle=arrow;x.fill();x.strokeStyle=p.highlight;x.lineWidth=1;x.stroke();
 }
 return P.Texture.from(c);
}
