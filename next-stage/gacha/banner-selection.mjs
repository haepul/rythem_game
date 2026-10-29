// Latest selection wins. No history, persistence or gameplay dependencies.
export class BannerSelection {
 constructor({banners,assets,loadArt,onSelect,onArt}){
  this.banners=banners;this.assets=assets;this.loadArt=loadArt;this.onSelect=onSelect;this.onArt=onArt;
  this.selectedBannerId=banners[0]?.id??null;this.visible=false;this.destroyed=false;this.generation=0;this.pending=null;
 }
 get selected(){return this.banners.find(b=>b.id===this.selectedBannerId)??null;}
 cancel(){this.generation++;this.pending?.abort();this.pending=null;}
 select(id){
  if(this.destroyed||!this.visible||id===this.selectedBannerId||!this.banners.some(b=>b.id===id))return false;
  this.selectedBannerId=id;this.render(true);return true;
 }
 render(changed=false){
  this.cancel();if(!this.visible||this.destroyed)return;
  const banner=this.selected;this.onSelect(banner,changed);if(!banner)return;
  const src=this.assets[banner.artKey]?.heroSrc;
  if(!src){this.onArt(null);return;}
  const generation=this.generation,controller=new AbortController();this.pending=controller;
  const settle=value=>{if(this.destroyed||!this.visible||generation!==this.generation)return;this.pending=null;this.onArt(value);};
  Promise.resolve().then(()=>controller.signal.aborted?null:this.loadArt(src,controller.signal)).then(value=>settle(value),()=>settle(null));
 }
 setVisible(visible){if(this.destroyed||this.visible===visible)return;this.visible=visible;if(visible)this.render();else this.cancel();}
 destroy(){this.destroyed=true;this.visible=false;this.cancel();}
}
export function loadBannerArt(src,signal){
 return new Promise(resolve=>{
  const image=new Image();
  const finish=value=>{image.onload=image.onerror=null;signal.removeEventListener('abort',abort);resolve(value);};
  const abort=()=>{finish(null);image.removeAttribute('src');};
  if(signal.aborted){resolve(null);return;}
  image.onload=()=>finish(image);image.onerror=()=>finish(null);
  signal.addEventListener('abort',abort,{once:true});image.src=src;
 });
}
