// Read-only presentation adapter. No input listeners or simulation mutations.
export class PlayHUD {
 constructor(root=document){this.el={};for(const id of ['score','life','life-fill','life-number','song-progress','play-time','combo','judgment'])this.el[id]=root.getElementById(id);this.number=this.el.combo.querySelector('b');this.keys=[...root.querySelectorAll('.lane-keys span')];this.cache={};this.animations={};}
 write(key,value,fn){if(this.cache[key]!==value){this.cache[key]=value;fn(value);}}
 pulse(key,el,frames,duration,effects){this.animations[key]?.cancel();if(effects)this.animations[key]=el.animate(frames,{duration,easing:'cubic-bezier(.2,.8,.2,1)'});}
 reset(){for(const a of Object.values(this.animations))a.cancel();this.cache={};this.el.judgment.textContent='';this.el.combo.hidden=true;}
 update(engine,now,duration,effects){
 const e=this.el;
 this.write('score',engine.score,v=>e.score.textContent=String(v).padStart(6,'0').replace(/\B(?=(\d{3})+(?!\d))/g,','));
 const hp=Math.max(0,Math.min(100,engine.hp));
 this.write('hp',hp,v=>{e.life.value=v;e['life-fill'].style.transform=`scaleX(${v/100})`;e['life-number'].textContent=Math.ceil(v);});
 this.write('danger',hp<=25,v=>e.life.closest('.life-block').classList.toggle('danger',v));
 this.write('progress',Math.round(Math.max(0,Math.min(1,now/duration))*1000),v=>e['song-progress'].value=v/1000);
 const format=t=>`${Math.floor(t/60).toString().padStart(2,'0')}:${(t%60).toString().padStart(2,'0')}`;
 this.write('time',`${Math.floor(Math.max(0,now))}/${Math.floor(duration)}`,()=>e['play-time'].textContent=`${format(Math.floor(Math.max(0,now)))} / ${format(Math.floor(duration))}`);
 this.write('combo',engine.combo,v=>{e.combo.hidden=v<3;this.number.textContent=v;if(v>=3)this.pulse('combo',this.number,[{transform:'scale(1.14)'},{transform:'scale(1)'}],130,effects);});
 const visible=now-engine.feedbackAt>=0&&now-engine.feedbackAt<.42;
 this.write('feedback',visible?`${engine.feedbackAt}/${engine.feedback}`:'',()=>{e.judgment.textContent=visible?engine.feedback:'';e.judgment.dataset.grade=engine.feedback;if(visible)this.pulse('judgment',e.judgment,[{opacity:0,transform:'translateY(4px) scale(.95)'},{opacity:1,transform:'none',offset:.18},{opacity:1,offset:.65},{opacity:0,transform:'translateY(-3px)'}],420,effects);});
 let mask=0;for(const contact of engine.contacts()){const lane=typeof contact==='number'?contact:contact.lane;if(lane!==null)mask|=1<<Math.max(0,Math.min(3,Math.round(lane)));}
 this.write('keys',mask,v=>this.keys.forEach((key,i)=>key.classList.toggle('pressed',Boolean(v&(1<<i)))));
 }
}
