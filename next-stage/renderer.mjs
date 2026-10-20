import {project,clamp} from './core.mjs';
const P=globalThis.PIXI;
const color=c=>(c[0]<<16)+(c[1]<<8)+c[2];
export class Stage{
 async init(host){this.app=new P.Application();await this.app.init({width:800,height:480,resolution:Math.min(devicePixelRatio||1,2),autoDensity:true,antialias:true,backgroundAlpha:0,autoStart:false,preference:'webgl'});this.app.canvas.id='canvas';this.app.canvas.setAttribute('aria-label','4레인 리듬게임 플레이 영역');host.append(this.app.canvas);this.track=new P.Graphics();this.grid=new P.Graphics();this.ribbon=new P.Graphics();this.heads=new P.Container();this.fx=new P.Graphics();this.app.stage.addChild(this.track,this.grid,this.ribbon,this.heads,this.fx);this.pool=[];this.textures={};for(const [name,c]of Object.entries({TAP:'#66e9d2',FLICK:'#ff69b5',HOLD:'#a5efb0',SLIDE:'#b596ff'}))this.textures[name]=this.texture(c,name==='FLICK');this.theme([102,233,210]);}
 // Four immutable, double-density textures; no filters or per-frame canvases.
 texture(tint,flick){
 const c=document.createElement('canvas');c.width=512;c.height=192;
 const x=c.getContext('2d');x.scale(2,2);
 x.shadowColor=tint;x.shadowBlur=4;
 x.fillStyle=flick?'#893057':'#244f60';
 x.beginPath();x.roundRect(6,42,244,40,4);x.fill();x.shadowBlur=0;
 const g=x.createLinearGradient(0,44,0,81);
 g.addColorStop(0,'#f8ffff');g.addColorStop(.14,tint);
 g.addColorStop(.43,tint);g.addColorStop(.5,'#f5ffff');
 g.addColorStop(.65,tint);g.addColorStop(1,'#557c91');
 x.fillStyle=g;x.beginPath();x.roundRect(8,44,240,36,3);x.fill();
 x.strokeStyle=tint;x.lineWidth=1;x.stroke();
 const band=x.createLinearGradient(12,0,244,0);
 band.addColorStop(0,'#ffffff88');band.addColorStop(.2,'#ffffff');
 band.addColorStop(.8,'#ffffff');band.addColorStop(1,'#ffffff88');
 x.fillStyle=band;x.fillRect(13,57,230,7);
 x.fillStyle='#ffffffeb';x.fillRect(13,45,230,2);
 x.fillStyle='#10233770';x.fillRect(13,77,230,2);
 x.fillStyle='#ffffffb0';x.fillRect(12,48,3,22);x.fillRect(241,48,3,22);
 if(flick){
 x.lineJoin='round';x.lineWidth=5;x.strokeStyle='#79264f';x.fillStyle='#fffafd';
 x.beginPath();x.moveTo(82,33);x.lineTo(128,5);x.lineTo(174,33);
 x.lineTo(158,38);x.lineTo(128,21);x.lineTo(98,38);x.closePath();x.stroke();x.fill();
 }
 return P.Texture.from(c);
 }
 // Sample the judge's exact path. One continuous fill avoids segment seams.
 drawRibbon(n,a,b,now,approach,effects){
 const r=this.ribbon,pts=this.ribbonPoints??=(new Float64Array(75));
 const c=n.type==='HOLD'?0xa5efb0:0xb596ff;
 for(let i=0;i<=24;i++){
 const t=a+(b-a)*i/24,l=n.type==='SLIDE'?n.judge.position(t):n.lane;
 const [x,y,w]=project(l,1-(t-now)/approach);
 pts[i*3]=x;pts[i*3+1]=y;pts[i*3+2]=w;
 }
 const strip=(fraction,alpha)=>{
 r.moveTo(pts[0]-pts[2]*fraction,pts[1]);
 for(let i=1;i<=24;i++)r.lineTo(pts[i*3]-pts[i*3+2]*fraction,pts[i*3+1]);
 for(let i=24;i>=0;i--)r.lineTo(pts[i*3]+pts[i*3+2]*fraction,pts[i*3+1]);
 r.closePath().fill({color:c,alpha});
 };
 strip(.38,n.active?.24:.16);strip(.22,n.active?.09:.055);
 for(const side of [-1,1]){
 r.moveTo(pts[0]+side*pts[2]*.38,pts[1]);
 for(let i=1;i<=24;i++)r.lineTo(pts[i*3]+side*pts[i*3+2]*.38,pts[i*3+1]);
 r.stroke({color:c,width:1.25,alpha:n.active?.9:.72});
 }
 if(effects&&n.active){
 const t=a+((now*.45)%1)*(b-a),[x,y,w]=project(n.judge.position(t),1-(t-now)/approach);
 r.moveTo(x-w*.3,y).lineTo(x+w*.3,y).stroke({color:0xffffff,alpha:.28,width:1.5});
 }
 }
 theme(accent){this.accent=color(accent);const g=this.track;g.clear();g.poly([257,110,543,110,776,427,24,427]).fill({color:0x000007,alpha:.5});for(let i=0;i<64;i++){let a=i/64,b=(i+1)/64,[x,y,w]=project(-.5,a),[xx,yy,ww]=project(-.5,b);g.poly([x,y,x+w*4,y,xx+ww*4,yy,xx,yy]).fill({color:0x151c39,alpha:.55+.35*b});}for(let lane=0;lane<4;lane++){let [x,y,w]=project(lane,0),[xx,yy,ww]=project(lane,1);if(lane%2)g.poly([x-w/2,y,x+w/2,y,xx+ww/2,yy,xx-ww/2,yy]).fill({color:0x9982e9,alpha:.035});}for(let i=0;i<=4;i++){let [x,y]=project(i-.5,0),[xx,yy]=project(i-.5,1);g.moveTo(x,y).lineTo(xx,yy).stroke({color:i===0||i===4?this.accent:0xa2a8c9,width:i===0||i===4?1.6:.7,alpha:i===0||i===4?.7:.23});}g.moveTo(38,410).lineTo(762,410).stroke({color:this.accent,width:10,alpha:.12});g.moveTo(38,410).lineTo(762,410).stroke({color:this.accent,width:4,alpha:.45});g.moveTo(38,410).lineTo(762,410).stroke({color:0xffffff,width:1.5});}
 head(kind,lane,time,now,approach,index){const p=1-(time-now)/approach;if(p<0||p>1.08)return index;let s=this.pool[index];if(!s){s=new P.Sprite(this.textures[kind]);s.anchor.set(.5,82/96);this.heads.addChild(s);this.pool.push(s);}s.texture=this.textures[kind];let [x,y,w]=project(lane,p);s.position.set(x,y);s.width=w*.89;s.height=36+26*Math.pow(clamp(p,0,1),1.55);s.visible=true;return index+1;}
 draw(engine,now,approach,bpm,offset,effects=true){const grid=this.grid,r=this.ribbon,fx=this.fx;grid.clear();r.clear();fx.clear();const beat=60/bpm,start=Math.ceil((now-offset)/beat);for(let k=start;k<start+Math.ceil(approach/beat)+1;k++){let p=1-(offset+k*beat-now)/approach;if(p<0||p>1)continue;let [x,y,w]=project(-.5,p);grid.moveTo(x,y).lineTo(x+w*4,y).stroke({color:0xe2ecff,alpha:.04+p*.12,width:.6+p*.5});}for(const contact of engine.contacts()){let lane=typeof contact==='number'?contact:contact.lane;let [x,y,w]=project(lane,1);fx.rect(x-w/2+3,y-8,w-6,11).fill({color:this.accent,alpha:.3});}
 const visible=this.visible??=[];visible.length=0;
 for(const n of engine.active)if(!n.hit)visible.push(n);
 visible.sort((a,b)=>b.time-a.time);
 for(const n of visible){
 if(!n.judge)continue;
 const a=Math.max(now,n.time),b=Math.min(now+approach,n.end_time);
 if(b>a)this.drawRibbon(n,a,b,now,approach,effects);
 }
 let count=0;for(const n of visible){if(n.judge){count=this.head(n.type,n.end_lane??n.lane,n.end_time,now,approach,count);if(!n.judge.head_done)count=this.head(n.type,n.lane,n.time,now,approach,count);else if(n.active)count=this.head(n.type,n.judge.position(now),now,now,approach,count);}else count=this.head(n.type,n.lane,n.time,now,approach,count);}for(let i=count;i<this.pool.length;i++)this.pool[i].visible=false;if(effects)for(const p of engine.sparks){let a=clamp((now-p.t)/.35,0,1),[x,y,w]=project(p.lane,1);fx.ellipse(x,y,w*.3+25*a,6+24*a).stroke({color:p.color,alpha:1-a,width:2});for(let j=0;j<6;j++){let angle=j*Math.PI/3;fx.circle(x+Math.cos(angle)*a*40,y-10-Math.sin(angle)*a*35,2*(1-a)).fill({color:0xffffff,alpha:1-a});}}this.app.render();}
}
