// Read-only presentation adapter. No input listeners or simulation mutations.
// Maximum is the sum of PERFECT awards (200 + combo * 10), including sustain ticks.
export const SCORE_RANK_STEPS=Object.freeze({C:.45,B:.60,A:.75,S:.90});
// Presentation lifetime only; engine judgment windows and feedback are unchanged.
export const JUDGMENT_DURATION=360;
// Cumulative Engine awards include simultaneous hits and every sustain tick.
// Fail closed for absent/malformed statistics; zero judgments is not an AP claim.
export function isAPMaintained(counts){
 if(!counts||!['PERFECT','GREAT','MISS'].every(k=>Number.isSafeInteger(counts[k])&&counts[k]>=0))return false;
 return counts.PERFECT>0&&Object.entries(counts).every(([grade,count])=>Number.isSafeInteger(count)&&count>=0&&(grade==='PERFECT'||count===0));
}
const JUDGMENT_FRAMES=[
 {opacity:.72,transform:'translateY(0) scale(.95)',offset:0},
 {opacity:1,transform:'translateY(0) scale(1.05)',offset:50/360},
 {opacity:1,transform:'translateY(0) scale(1)',offset:130/360},
 {opacity:1,transform:'translateY(0) scale(1)',offset:240/360},
 {opacity:0,transform:'translateY(-3px) scale(1)',offset:1}
];
export function scoreRank(score,total){
 const candidate=Number.isSafeInteger(total)&&total>0?200*total+5*total*(total+1):0;
 const valid=Number.isSafeInteger(candidate)&&candidate>0;
 const maximum=valid?candidate:0;
 const current=Number.isFinite(score)?Math.max(0,score):0;
 const ratio=maximum?Math.min(1,current/maximum):0;
 const targets=Object.fromEntries(Object.entries(SCORE_RANK_STEPS).map(([rank,fraction])=>[rank,Math.ceil(maximum*fraction)]));
 return {ratio,maximum,valid,targets,percent:ratio===1?'100%':`${Math.floor(ratio*1000)/10}%`,rank:!valid?'D':ratio>=SCORE_RANK_STEPS.S?'S':ratio>=SCORE_RANK_STEPS.A?'A':ratio>=SCORE_RANK_STEPS.B?'B':ratio>=SCORE_RANK_STEPS.C?'C':'D'};
}
export class PlayHUD {
 constructor(root=document){this.el={};for(const id of ['score','life','life-fill','life-number','life-flash','song-progress','play-time','combo','judgment'])this.el[id]=root.getElementById(id);this.judgmentText=this.el.judgment.querySelector('span');this.number=this.el.combo.querySelector('b');this.keys=[...root.querySelectorAll('.lane-keys span')];this.cache={};this.animations={};}
 write(key,value,fn){if(this.cache[key]!==value){this.cache[key]=value;fn(value);}}
 pulse(key,el,frames,duration,effects){this.animations[key]?.cancel();if(effects)this.animations[key]=el.animate(frames,{duration,easing:'cubic-bezier(.2,.8,.2,1)'});}
 reset(){for(const a of Object.values(this.animations))a.cancel();this.cache={};this.judgmentText.textContent='';this.el.judgment.hidden=true;this.el.combo.hidden=true;}
 updateJudgment(engine,now,effects){
  const age=(now-engine.feedbackAt)*1000,grade=engine.feedback;
  const visible=['PERFECT','GREAT','MISS'].includes(grade)&&age>=0&&age<JUDGMENT_DURATION;
  const key=visible?`${engine.feedbackAt}/${grade}`:'';
  const changed=this.cache.feedback!==key,motionChanged=this.cache['judgment-effects']!==Boolean(effects);
  if(changed){this.cache.feedback=key;this.judgmentText.textContent=visible?grade:'';this.el.judgment.dataset.grade=visible?grade:'';this.el.judgment.hidden=!visible;}
  if(changed||motionChanged){
   this.cache['judgment-effects']=Boolean(effects);this.animations.judgment?.cancel();delete this.animations.judgment;
   if(visible&&effects){this.animations.judgment=this.judgmentText.animate(JUDGMENT_FRAMES,{duration:JUDGMENT_DURATION,easing:'linear',fill:'both'});this.animations.judgment.currentTime=age;}
  }
  // Recover after a pause/tab suspension without creating a second animation.
  const animation=this.animations.judgment;
  if(visible&&animation&&Math.abs(Number(animation.currentTime)-age)>50)animation.currentTime=age;
 }
 update(engine,now,duration,effects){
 const e=this.el;
 if(this.rankRoot===undefined){this.rankRoot=e.score.closest?.('.score-block');this.rankLetter=this.rankRoot?.querySelector('#score-rank');this.rankFill=this.rankRoot?.querySelector('#score-rank-fill');this.rankProgress=this.rankRoot?.querySelector('#score-rank-progress');this.rankSummary=this.rankRoot?.querySelector('#score-rank-summary');if(this.rankRoot)for(const marker of this.rankRoot.querySelectorAll('.score-rank-track i'))marker.style.setProperty('--step',`${SCORE_RANK_STEPS[marker.textContent]*100}%`);}
 if(this.rankLetter){
  this.write('score-rank-state',`${engine.score}/${engine.total}`,()=>{
   const r=scoreRank(engine.score,engine.total);this.rankLetter.textContent=r.rank;this.rankRoot.dataset.rank=r.rank;this.rankFill.style.transform=`scaleX(${r.ratio})`;this.rankProgress.value=r.ratio;
   const summary=r.valid?`MAX ${r.maximum.toLocaleString('en-US')} · ${r.percent}`:'MAX — · 계산 불가';
   if(this.rankSummary)this.rankSummary.textContent=summary;
   this.rankProgress.setAttribute('aria-valuetext',r.valid?`${r.percent}, 최대 점수 ${r.maximum}`:'유효한 총 판정 수 없음');
   this.rankRoot.title=r.valid?`전체 채보 최대 점수 ${r.maximum.toLocaleString('en-US')} 대비 ${r.percent}. 콤보 보너스로 후반 점수 비중이 높습니다.\n${Object.entries(r.targets).map(([rank,score])=>`${rank}: ${score.toLocaleString('en-US')}`).join(' / ')}`:'총 판정 수가 없거나 유효하지 않아 점수 달성률을 계산할 수 없습니다.';
  });
 }
 const previousScore=this.cache.score;
 this.write('score-effects',Boolean(effects),v=>{if(!v)this.animations.score?.cancel();});
 this.write('score',engine.score,v=>{
  e.score.textContent=String(v).padStart(6,'0').replace(/\B(?=(\d{3})+(?!\d))/g,',');
  if(previousScore!==undefined&&v>previousScore)this.pulse('score',e.score,[{transform:'scale(1.025)',opacity:.92},{transform:'scale(1)',opacity:1}],100,effects);
  else this.animations.score?.cancel();
 });
 const hp=Math.max(0,Math.min(100,engine.hp));
 const block=e.life.closest('.life-block'),previous=this.cache.hp;
 this.write('life-effects',Boolean(effects),v=>{block.dataset.motion=v?'on':'off';if(!v)this.animations.life?.cancel();});
 this.write('hp',hp,v=>{
  e.life.value=v;e['life-number'].textContent=Math.ceil(v);
  const rising=previous!==undefined&&v>previous;
  block.dataset.change=rising?'recover':'damage';
  e['life-fill'].style.transform=`scaleX(${v/100})`;
  this.animations.life?.cancel();
  const flash=e['life-flash'];
  if(flash&&effects&&previous!==undefined&&v>0&&v!==previous){
   flash.style.transform=`translateX(${Math.min(previous,v)}%) scaleX(${Math.abs(v-previous)/100})`;
   this.animations.life=flash.animate([{opacity:rising?.65:.45},{opacity:0}],{duration:rising?200:160,easing:'ease-out'});
  }
 });
 this.write('caution',hp>25&&hp<=50,v=>block.classList.toggle('caution',v));
 this.write('danger',hp<=25,v=>e.life.closest('.life-block').classList.toggle('danger',v));
 this.write('progress',Math.round(Math.max(0,Math.min(1,now/duration))*1000),v=>e['song-progress'].value=v/1000);
 const format=t=>`${Math.floor(t/60).toString().padStart(2,'0')}:${(t%60).toString().padStart(2,'0')}`;
 this.write('time',`${Math.floor(Math.max(0,now))}/${Math.floor(duration)}`,()=>e['play-time'].textContent=`${format(Math.floor(Math.max(0,now)))} / ${format(Math.floor(duration))}`);
 this.write('combo-effects',Boolean(effects),v=>{e.combo.dataset.motion=v?'on':'off';if(!v){this.animations.combo?.cancel();this.animations['ap-change']?.cancel();}});
 const previousAP=this.cache.ap;
 this.write('ap',isAPMaintained(engine.counts),v=>{
  e.combo.dataset.ap=v?'maintaining':'normal';
  if(previousAP===true&&!v)this.pulse('ap-change',e.combo,[{opacity:.86},{opacity:1}],110,effects);
 });
 this.write('combo',engine.combo,v=>{
  e.combo.hidden=v<3;this.number.textContent=v;
  this.write('combo-digits',Math.max(5,String(v).length),digits=>{this.number.style.setProperty('--combo-digits',String(digits));});
  if(v>=3)this.pulse('combo',this.number,[{transform:'scale(1.08)',opacity:.94},{transform:'scale(1.015)',opacity:1,offset:.65},{transform:'scale(1)',opacity:1}],130,effects);
  else this.animations.combo?.cancel();
 });
 this.updateJudgment(engine,now,effects);
 let mask=0;for(const contact of engine.contacts()){const lane=typeof contact==='number'?contact:contact.lane;if(lane!==null)mask|=1<<Math.max(0,Math.min(3,Math.round(lane)));}
 this.write('keys',mask,v=>this.keys.forEach((key,i)=>key.classList.toggle('pressed',Boolean(v&(1<<i)))));
 }
}
