// Keep game/audio paused until the visual exit finishes. Cancellation prevents
// stale resume callbacks if navigation or a restart closes the dialog first.
export class SettingsMotion {
 constructor(dialog,reduced){this.dialog=dialog;this.reduced=reduced;this.token=0;this.animation=null;}
 cancel(){this.token++;this.animation?.cancel();this.animation=null;this.dialog.inert=false;}
 exit(action){if(this.animation)return;const d=this.dialog;if(!d.open)return;
 if(this.reduced()){action();return;}
 const token=++this.token;d.inert=true;
 this.animation=d.animate([{opacity:1,transform:'scale(1)'},{opacity:0,transform:'scale(.975)'}],{duration:150,easing:'ease-in',fill:'forwards'});
 this.animation.finished.then(()=>{if(token!==this.token)return;this.animation.cancel();this.animation=null;d.inert=false;if(d.open)action();}).catch(()=>{});
 }
}
