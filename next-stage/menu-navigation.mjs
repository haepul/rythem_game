// HOME menu routing only. No gameplay, audio or persistence dependencies.
export const menuRoute=hash=>hash==='#/gacha'?'gacha':'library';
export class MenuNavigation {
 constructor({host=window,canNavigate,onChange}){
  this.host=host;this.canNavigate=canNavigate;this.onChange=onChange;
  this.menuScreen=null;this.mounted=false;this.onHistory=()=>this.readHistory();
 }
 write(screen,replace){
  const {location,history}=this.host;
  const url=location.pathname+location.search+'#/'+screen;
  history[replace?'replaceState':'pushState'](history.state,'',url);
 }
 apply(screen,options={}){
  if(screen===this.menuScreen&&!options.force)return;
  const previous=this.menuScreen;this.menuScreen=screen;
  this.onChange(screen,previous,options);
 }
 mount(){
  if(this.mounted)return;this.mounted=true;
  this.host.addEventListener('popstate',this.onHistory);
  this.host.addEventListener('hashchange',this.onHistory);
  this.readHistory();
 }
 readHistory(){
  if(!this.mounted)return;
  if(!this.canNavigate()){this.write(this.menuScreen||'library',true);return;}
  const screen=menuRoute(this.host.location.hash);
  if(this.host.location.hash!=='#/'+screen)this.write(screen,true);
  this.apply(screen,{source:'history'});
 }
 navigate(screen,{replace=false,...options}={}){
  if(!this.mounted||!['library','gacha'].includes(screen)||!this.canNavigate())return false;
  if(screen!==this.menuScreen||this.host.location.hash!=='#/'+screen)this.write(screen,replace);
  this.apply(screen,options);return true;
 }
 destroy(){
  this.host.removeEventListener('popstate',this.onHistory);
  this.host.removeEventListener('hashchange',this.onHistory);this.mounted=false;
 }
}
