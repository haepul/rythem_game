import {project,clamp} from './core.mjs';
const P=globalThis.PIXI;
const color=c=>(c[0]<<16)+(c[1]<<8)+c[2];
export class Stage{
 async init(host){this.app=new P.Application();await this.app.init({width:800,height:480,resolution:Math.min(devicePixelRatio||1,2),autoDensity:true,antialias:true,backgroundAlpha:0,autoStart:false,preference:'webgl'});this.app.canvas.id='canvas';this.app.canvas.setAttribute('aria-label','4레인 리듬게임 플레이 영역');host.append(this.app.canvas);this.track=new P.Graphics();this.grid=new P.Graphics();this.ribbon=new P.Graphics();this.heads=new P.Container();this.fx=new P.Graphics();this.initJudgment();this.app.stage.addChild(this.track,this.grid,this.judgeGlow,this.ribbon,this.heads,this.judgeHighlight,this.inputHighlight,this.fx,this.diamondBurst);this.pool=[];this.textures={};for(const [name,c]of Object.entries({TAP:'#66e9d2',FLICK:'#ff69b5',HOLD:'#a5efb0',SLIDE:'#b596ff'}))this.textures[name]=this.texture(c,name==='FLICK');this.theme([102,233,210]);}
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
 theme(accent){this.accent=color(accent);const g=this.track;g.clear();g.poly([257,110,543,110,776,427,24,427]).fill({color:0x000007,alpha:.5});for(let i=0;i<64;i++){let a=i/64,b=(i+1)/64,[x,y,w]=project(-.5,a),[xx,yy,ww]=project(-.5,b);g.poly([x,y,x+w*4,y,xx+ww*4,yy,xx,yy]).fill({color:0x151c39,alpha:.55+.35*b});}for(let lane=0;lane<4;lane++){let [x,y,w]=project(lane,0),[xx,yy,ww]=project(lane,1);if(lane%2)g.poly([x-w/2,y,x+w/2,y,xx+ww/2,yy,xx-ww/2,yy]).fill({color:0x9982e9,alpha:.035});}for(let i=0;i<=4;i++){let [x,y]=project(i-.5,0),[xx,yy]=project(i-.5,1);g.moveTo(x,y).lineTo(xx,yy).stroke({color:i===0||i===4?this.accent:0xa2a8c9,width:i===0||i===4?1.6:.7,alpha:i===0||i===4?.7:.23});}this.themeJudgment(accent);}


 // All judgment geometry derives from the same projection as note arrival.
 initJudgment(){
  this.judgeGlow=new P.Container();this.lineGlow=new P.Graphics();
  this.judgeHighlight=new P.Graphics();this.inputHighlight=new P.Graphics();
  this.lineBody=new P.Graphics();this.judgeGlow.addChild(this.lineGlow,this.lineBody);this.initDiamonds();
  const canvas=document.createElement('canvas');canvas.width=256;canvas.height=128;
  const ctx=canvas.getContext('2d');ctx.scale(1,.5);
  const glow=ctx.createRadialGradient(128,112,0,128,112,110);
  glow.addColorStop(0,'#ffffffb0');glow.addColorStop(.3,'#ffffff65');
  glow.addColorStop(.7,'#ffffff18');glow.addColorStop(1,'#ffffff00');
  ctx.fillStyle=glow;ctx.fillRect(0,0,256,256);
  this.inputTexture=P.Texture.from(canvas);
  this.laneLights=[];this.judgeLanes=[];
  for(let lane=0;lane<4;lane++){
   const light=new P.Sprite(this.inputTexture);light.anchor.set(.5,.375);
   this.judgeGlow.addChild(light);this.laneLights.push(light);
   this.judgeLanes.push(project(lane,1));
  }
  this.held=new Uint8Array(4);this.wasHeld=new Uint8Array(4);
  this.releasedAt=new Float64Array(4);this.impactSlots=new Array(4).fill(null);
 }

 // Three immutable crystal textures, native 1:1.5 canvas aspect ratio.
 crystalTexture(kind){
  const canvas=document.createElement('canvas');canvas.width=128;canvas.height=192;
  const c=canvas.getContext('2d');c.scale(2,2);
  const face=(points,fill)=>{c.beginPath();c.moveTo(points[0],points[1]);for(let i=2;i<points.length;i+=2)c.lineTo(points[i],points[i+1]);c.closePath();c.fillStyle=fill;c.fill();};
  const shard=kind==='Shard',sparkle=kind==='Sparkle';
  const w=shard?11:sparkle?16:20,h=shard?35:sparkle?23:30;
  const top=[32,48-h],right=[32+w,48],bottom=[32,48+h],left=[32-w,48];
  c.shadowColor='#c7b8ff55';c.shadowBlur=3;
  face([...top,...right,...bottom,...left],'#eefaff');c.shadowBlur=0;
  // Four beveled faces surround a bright, separate central table facet.
  const ct=[32,48-h*.37],cr=[32+w*.36,48],cb=[32,48+h*.37],cl=[32-w*.36,48];
  face([...top,...right,...cr,...ct],'#f7f0ff');
  face([...right,...bottom,...cb,...cr],'#badde9');
  face([...bottom,...left,...cl,...cb],'#b6f4e1');
  face([...left,...top,...ct,...cl],'#d4c5f5');
  face([...ct,...cr,...cb,...cl],'#ffffff');
  c.beginPath();c.moveTo(...top);c.lineTo(...right);c.lineTo(...bottom);c.lineTo(...left);c.closePath();c.strokeStyle='#ffffffe0';c.lineWidth=1.1;c.stroke();
  c.beginPath();c.moveTo(...ct);c.lineTo(...cr);c.lineTo(...cb);c.lineTo(...cl);c.closePath();c.strokeStyle='#ffffffb8';c.lineWidth=.65;c.stroke();
  if(sparkle){
   const g=c.createRadialGradient(32,48,0,32,48,34);g.addColorStop(0,'#ffffffb0');g.addColorStop(.4,'#e8faff55');g.addColorStop(1,'#ffffff00');
   c.strokeStyle=g;c.lineWidth=1;c.beginPath();c.moveTo(6,48);c.lineTo(58,48);c.moveTo(32,14);c.lineTo(32,82);c.stroke();
  }
  return P.Texture.from(canvas);
 }
 // Independent geometric light, drawn once; the hollow center preserves note visibility.
 haloTexture(){
  const canvas=document.createElement('canvas');canvas.width=384;canvas.height=256;
  const c=canvas.getContext('2d');c.scale(2,2);
  const ring=(w,h,stroke,width)=>{c.beginPath();c.moveTo(96,64-h);c.lineTo(96+w,64);c.lineTo(96,64+h);c.lineTo(96-w,64);c.closePath();c.strokeStyle=stroke;c.lineWidth=width;c.stroke();};
  ring(87,54,'#c5b6ff12',5);ring(87,54,'#c5b6ff55',1.3);
  ring(72,44,'#a9ffe0b0',1.2);ring(57,34,'#edfff9dc',1);
  const g=c.createRadialGradient(96,64,0,96,64,29);
  g.addColorStop(0,'#ffffffef');g.addColorStop(.18,'#efffffbb');g.addColorStop(.48,'#8effe655');g.addColorStop(1,'#98ffe000');
  c.fillStyle=g;c.fillRect(66,34,60,60);
  return P.Texture.from(canvas);
 }
 initDiamonds(){
  this.diamondTextures={Diamond:this.crystalTexture('Diamond'),Shard:this.crystalTexture('Shard'),Sparkle:this.crystalTexture('Sparkle')};
  this.diamondBurst=new P.Container();this.lineDiamonds=[];this.burstPool=[];this.haloPool=[];
  this.haloTextureCached=this.haloTexture();
  for(let i=0;i<4;i++){const sprite=new P.Sprite(this.haloTextureCached);sprite.anchor.set(.5,.5);sprite.visible=false;this.diamondBurst.addChild(sprite);this.haloPool.push(sprite);}
  for(let i=0;i<8;i++){const sprite=new P.Sprite(this.diamondTextures.Sparkle);sprite.anchor.set(.5,.5);this.judgeGlow.addChild(sprite);this.lineDiamonds.push(sprite);}
  for(let i=0;i<32;i++){const sprite=new P.Sprite(this.diamondTextures.Diamond);sprite.anchor.set(.5,.5);sprite.visible=false;this.diamondBurst.addChild(sprite);this.burstPool.push(sprite);}
 }
 diamondPulse(age){
  if(age<0||age>=.22)return 0;
  if(age<.06){const t=age/.06;return t*t*(3-2*t);}
  if(age<.09)return 1;
  const t=(age-.09)/.13;return 1-t*t*(3-2*t);
 }
 drawDiamondLine(now,effects){
  const [left,y]=project(-.5,1),[right]=project(3.5,1);
  for(let i=0;i<8;i++){
   const s=this.lineDiamonds[i];s.visible=effects;
   if(!effects)continue;
   const phase=((now+i*.325)%2.6+2.6)%2.6;
   const pulse=this.diamondPulse(phase);
   s.position.set(left+(right-left)*(i+.5)/8,y+(i%2?1:-1));
   s.width=(7+i%3)*(1+pulse*.08);s.height=s.width*1.5;s.alpha=.012+pulse*.22;s.rotation=(i%2?1:-1)*.06*pulse;
  }
 }
 drawDiamondBurst(spark,now,grade,index){
  const a=clamp((now-spark.t)/.24,0,1),[x,y]=project(spark.lane,1);
  const perfect=grade==='PERFECT',gain=perfect?1:grade==='GREAT'?.48:.62,count=perfect?8:6;
  const halo=this.haloPool[clamp(Math.round(spark.lane),0,3)];
  halo.visible=a<1;halo.position.set(x,y);halo.rotation=0;
  const expansion=1-Math.pow(1-a,3);
  halo.width=project(spark.lane,1)[2]*(.57+.43*expansion);halo.height=halo.width*2/3;
  halo.alpha=gain*Math.min(1,(now-spark.t)/.025)*Math.pow(1-a,1.35)*.82;
  for(let i=0;i<count&&index<this.burstPool.length;i++){
   const s=this.burstPool[index++],side=i%2?1:-1,spread=16+Math.floor(i/2)*10;
   s.visible=a<1;s.position.set(x+side*spread*(1-Math.pow(1-a,2)),y-(10+i%4*6)*Math.sin(a*Math.PI*.75));
   s.texture=i%3===1?this.diamondTextures.Shard:this.diamondTextures.Diamond;
   const size=(8+(i%3)*1.6)*(1-a*.35);s.width=size;s.height=size*1.5;
   s.rotation=side*(.12+a*(i%3===1?1.2:.7));s.alpha=gain*this.diamondPulse(now-spark.t)*.9;
  }
  return index;
 }
 themeJudgment(accent){
  const [left,y]=project(-.5,1),[right]=project(3.5,1);
  this.judgeColor=color(accent.map((v,i)=>Math.round(v*.55+[181,160,246][i]*.45)));
  const g=this.lineGlow;g.clear();
  // Static stepped falloff, rebuilt only on theme changes; no blur filter.
  for(const [width,alpha] of [[28,.025],[22,.03],[16,.065],[13,.08]])
   g.moveTo(left,y).lineTo(right,y).stroke({color:this.judgeColor,width,alpha});
  const body=this.lineBody;body.clear();
  body.moveTo(left,y).lineTo(right,y).stroke({color:0xc1b3f5,width:9,alpha:.72});
  body.moveTo(left,y+2).lineTo(right,y+2).stroke({color:this.judgeColor,width:4,alpha:.42});
  for(let i=0;i<16;i++){
   const x=left+(right-left)*i/16,step=(right-left)/16;
   body.poly([x,y-4.5,x+step,y-4.5,x+step*.5,y+4.5]).fill({color:i%2?0xb8fff0:0xffffff,alpha:.15});
  }
  const h=this.judgeHighlight;h.clear();
  h.moveTo(left,y).lineTo(right,y).stroke({color:this.judgeColor,width:3,alpha:.65});
  h.moveTo(left,y).lineTo(right,y).stroke({color:0xf7ffff,width:2.2,alpha:.9});
  for(let lane=0;lane<4;lane++){
   const [x,yy,w]=this.judgeLanes[lane],light=this.laneLights[lane];
   light.position.set(x,yy);light.width=w*.96;light.height=38;
   light.tint=this.judgeColor;light.alpha=0;
  }
  this.resetJudgment();
 }
 resetJudgment(){this.wasHeld.fill(0);this.releasedAt.fill(-Infinity);this.sparkGrades=new WeakMap();for(const sprite of this.burstPool)sprite.visible=false;for(const sprite of this.haloPool)sprite.visible=false;}
 drawJudgment(engine,now,effects){
  if(this.judgeEngine!==engine||now<this.judgeNow){this.resetJudgment();this.judgeEngine=engine;}
  this.judgeNow=now;this.lineGlow.visible=effects;this.drawDiamondLine(now,effects);this.diamondBurst.visible=effects;for(const sprite of this.burstPool)sprite.visible=false;for(const sprite of this.haloPool)sprite.visible=false;
  const h=this.inputHighlight;h.clear();this.held.fill(0);
  for(const contact of engine.contacts()){
   const lane=typeof contact==='number'?contact:contact.lane;
   if(Number.isInteger(lane)&&lane>=0&&lane<4)this.held[lane]=1;
  }
  for(let lane=0;lane<4;lane++){
   if(this.wasHeld[lane]&&!this.held[lane])this.releasedAt[lane]=now;
   if(!effects)this.releasedAt[lane]=-Infinity;
   const strength=this.held[lane]?1:effects?Math.pow(clamp(1-(now-this.releasedAt[lane])/.08,0,1),2):0;
   this.wasHeld[lane]=this.held[lane];this.laneLights[lane].alpha=effects?strength*.55:0;
   if(!strength)continue;
   const [x,y,w]=this.judgeLanes[lane];
   h.moveTo(x-w*.47,y).lineTo(x+w*.47,y).stroke({color:0xeaffff,width:effects?2:1.5,alpha:strength*.85});
  }
 }
 drawImpacts(engine,now){
  // Bound overdraw during dense sustain ticks to the latest real spark per lane.
  this.impactSlots.fill(null);
  for(const spark of engine.sparks){
   const age=now-spark.t;if(age<0||age>=.24||!Number.isFinite(spark.lane))continue;
   const lane=clamp(Math.round(spark.lane),0,3),previous=this.impactSlots[lane];
   if(!previous||spark.t>=previous.t)this.impactSlots[lane]=spark;
  }
  let particleIndex=0;
  for(const spark of this.impactSlots){
   if(!spark)continue;
   if(!this.sparkGrades.has(spark)){
    // feedback describes only the last award. Simultaneous awards are ambiguous.
    const unique=engine.sparks.filter(s=>s.t===spark.t).length===1;
    this.sparkGrades.set(spark,unique&&Math.abs(engine.feedbackAt-spark.t)<1e-7?engine.feedback:'UNKNOWN');
   }
   particleIndex=this.drawDiamondBurst(spark,now,this.sparkGrades.get(spark),particleIndex);
   const a=(now-spark.t)/.24,fade=(1-a)*(1-a),[x,y,w]=project(spark.lane,1);
   const radius=w*(.12+.30*(1-Math.pow(1-a,3))),g=this.fx;
   g.moveTo(x-radius,y).lineTo(x+radius,y).stroke({color:spark.color,width:5*(1-a)+1,alpha:fade*.32});
   g.moveTo(x-radius*.75,y).lineTo(x+radius*.75,y).stroke({color:0xffffff,width:1.3,alpha:fade*.85});
   g.ellipse(x,y,radius,2+6*a).stroke({color:spark.color,width:1,alpha:fade*.55});
   for(const side of [-1,1])g.circle(x+side*radius,y-3-5*a,1.4*(1-a)).fill({color:0xf5ffff,alpha:fade*.65});
  }
 }
 head(kind,lane,time,now,approach,index){const p=1-(time-now)/approach;if(p<0||p>1.08)return index;let s=this.pool[index];if(!s){s=new P.Sprite(this.textures[kind]);s.anchor.set(.5,82/96);this.heads.addChild(s);this.pool.push(s);}s.texture=this.textures[kind];let [x,y,w]=project(lane,p);s.position.set(x,y);s.width=w*.89;s.height=36+26*Math.pow(clamp(p,0,1),1.55);s.visible=true;return index+1;}
 draw(engine,now,approach,bpm,offset,effects=true){const grid=this.grid,r=this.ribbon,fx=this.fx;grid.clear();r.clear();fx.clear();const beat=60/bpm,start=Math.ceil((now-offset)/beat);for(let k=start;k<start+Math.ceil(approach/beat)+1;k++){let p=1-(offset+k*beat-now)/approach;if(p<0||p>1)continue;let [x,y,w]=project(-.5,p);grid.moveTo(x,y).lineTo(x+w*4,y).stroke({color:0xe2ecff,alpha:.04+p*.12,width:.6+p*.5});}this.drawJudgment(engine,now,effects);

 const visible=this.visible??=[];visible.length=0;
 for(const n of engine.active)if(!n.hit)visible.push(n);
 visible.sort((a,b)=>b.time-a.time);
 for(const n of visible){
 if(!n.judge)continue;
 const a=Math.max(now,n.time),b=Math.min(now+approach,n.end_time);
 if(b>a)this.drawRibbon(n,a,b,now,approach,effects);
 }
 let count=0;for(const n of visible){if(n.judge){count=this.head(n.type,n.end_lane??n.lane,n.end_time,now,approach,count);if(!n.judge.head_done)count=this.head(n.type,n.lane,n.time,now,approach,count);else if(n.active)count=this.head(n.type,n.judge.position(now),now,now,approach,count);}else count=this.head(n.type,n.lane,n.time,now,approach,count);}for(let i=count;i<this.pool.length;i++)this.pool[i].visible=false;if(effects)this.drawImpacts(engine,now);this.app.render();}
}
