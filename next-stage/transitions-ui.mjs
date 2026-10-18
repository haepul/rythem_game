export function loadingView(status,progress){
 const messages={idle:'음악과 채보를 준비하고 있습니다',loading:'음악 파일을 다운로드하고 있습니다',decoding:'음악을 재생할 수 있도록 디코딩하고 있습니다',ready:'채보와 렌더러 준비를 확인하고 있습니다'};
 return {message:messages[status]||'',progress:status==='loading'&&!progress?null:Math.max(0,Math.min(1,progress||0))};
}
export function resultTheme(failed,ap,fc){return {outcome:failed?'failed':'clear',award:failed?'':ap?'ap':fc?'fc':''};}
export class TransitionUI{
 constructor(root=document){this.loading=root.getElementById('loading');this.message=root.getElementById('loading-message');this.progress=root.getElementById('load-progress');this.count=root.getElementById('count-in');this.last='';this.number='';this.anim=null;}
 load(status,progress){const v=loadingView(status,progress),key=`${status}/${v.progress}`;if(key===this.last)return;this.last=key;this.loading.dataset.status=status;if(status==='error')return;this.message.textContent=v.message;if(v.progress===null)this.progress.removeAttribute('value');else this.progress.value=v.progress;}
 countdown(value,effects){value=String(value);if(this.number===value)return;this.number=value;this.count.textContent=value;this.anim?.cancel();if(effects)this.anim=this.count.animate([{opacity:.6},{opacity:1}],{duration:170});}
 reset(){this.last='';this.number='';this.anim?.cancel();}
}
