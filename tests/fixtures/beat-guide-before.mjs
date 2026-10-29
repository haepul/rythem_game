// Frozen pre-change grid loop from renderer SHA256 1d2035cfdad178912fca4020836e2078e986210c469c7d2eac59d2a5b21a80e1.
// All other Stage layers are the current, unchanged implementation.
import {project} from '../../next-stage/core.mjs';
export function drawBeatGuidesBefore(now,approach,bpm,offset){
 const grid=this.grid;grid.clear();const beat=60/bpm,start=Math.ceil((now-offset)/beat);
 for(let k=start;k<start+Math.ceil(approach/beat)+1;k++){
  let p=1-(offset+k*beat-now)/approach;if(p<0||p>1)continue;
  let [x,y,w]=project(-.5,p);grid.moveTo(x,y).lineTo(x+w*4,y).stroke({color:0xaabbd8,alpha:.025+p*.085,width:.55+p*.3});
 }
}
