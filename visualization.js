/* Playback uses geometric arc length in mm, independently of the camera. */
(function(root){
 'use strict';
 function prepare(ray){
  const points=ray.points||[],distance=[0];
  for(let i=1;i<points.length;i++)distance.push(distance.at(-1)+Math.hypot(...points[i].map((v,j)=>v-points[i-1][j])));
  return {ray,points,distance,length:distance.at(-1)||0};
 }
 function front(path,travel){
  if(!path.points.length)return {points:[],tip:null,finished:true};
  const d=Math.max(0,travel),points=[path.points[0]];
  for(let i=1;i<path.points.length;i++){
   if(path.distance[i]<=d){points.push(path.points[i]);continue}
   const size=path.distance[i]-path.distance[i-1],t=size>0?(d-path.distance[i-1])/size:0;
   if(t>0)points.push(path.points[i-1].map((v,j)=>v+t*(path.points[i][j]-v)));
   break;
  }
  return {points,tip:points.at(-1),finished:d>=path.length};
 }
 const api={prepare,front,speed_mm_s:50};
 if(typeof module!=='undefined'&&module.exports)module.exports=api;else root.BeamPlaybackGeometry=api;
})(typeof globalThis!=='undefined'?globalThis:this);

if(typeof document!=='undefined'){
 const playback={active:false,ready:false,frame:null,timer:null,paths:[],length:0,travel:0,last:null};
 function syncPlayback(){
  const button=$('visualize');button.textContent=playback.active?'Stop visualization':'Visualize';button.classList.toggle('active',playback.active);button.setAttribute('aria-pressed',String(playback.active));
  const status=$('visualization-status');status.hidden=!playback.active;
  if(playback.active)status.textContent=playback.ready?'Visualizing · 5 cm/s · '+fmt(Math.min(playback.travel,playback.length)/10,1)+' cm travelled · repeats until stopped':'Updating beam paths…';
 }
 function playbackFrame(time){
  if(!playback.active)return;
  if(playback.ready&&!document.hidden&&playback.last!==null){playback.travel+=Math.max(0,time-playback.last)/1000*BeamPlaybackGeometry.speed_mm_s;playback.travel%=playback.length+25}
  playback.last=document.hidden?null:time;syncPlayback();scheduleDraw();playback.frame=requestAnimationFrame(playbackFrame);
 }
 function stopVisualization(){
  playback.active=false;playback.ready=false;playback.last=null;
  if(playback.frame!==null)cancelAnimationFrame(playback.frame);if(playback.timer!==null)clearTimeout(playback.timer);
  playback.frame=playback.timer=null;syncPlayback();scheduleDraw();
 }
 function visualizationResultReady(){
  if(!playback.active)return;
  const rays=[...(result.rays||[]),...(result.spectral_chiefs||[]),...(result.chiefs||[])];
  playback.paths=rays.map(BeamPlaybackGeometry.prepare).filter(p=>p.points.length>1&&p.length>0);
  if(!playback.paths.length){stopVisualization();toast('Add an enabled laser inside the bench to visualize its beam.');return}
  playback.length=Math.max(...playback.paths.map(p=>p.length));playback.travel=0;playback.last=null;playback.ready=true;syncPlayback();
 }
 function visualizationChanged(){
  if(!playback.active)return;playback.ready=false;playback.last=null;syncPlayback();
  if(playback.timer===null)playback.timer=setTimeout(()=>{playback.timer=null;if(playback.active)run()},180);
 }
 function drawBeamPlayback(project){
  if(!playback.ready)return;
  const coloured=$('wavelength-colours').checked;
  for(const path of playback.paths){
   const f=BeamPlaybackGeometry.front(path,playback.travel);if(!f.tip)continue;
   const ray=path.ray,colour=coloured?wavelengthColor(ray.wavelength_nm,ray.source_id,.45):'#f4be6570';
   line(f.points.map(project),colour,1);
   if(!f.finished){const tip=project(f.tip);ctx.beginPath();ctx.arc(tip[0],tip[1],2.4,0,Math.PI*2);ctx.fillStyle=coloured?wavelengthColor(ray.wavelength_nm,ray.source_id):'#ffe5aa';ctx.fill()}
  }
 }
 $('visualize').onclick=()=>{
  if(playback.active){stopVisualization();return}
  const invalid=$('bench-view').querySelector('input.invalid');if(invalid){toast('Correct the highlighted field before visualizing.');invalid.focus();return}
  playback.active=true;playback.ready=false;playback.last=null;syncPlayback();playback.frame=requestAnimationFrame(playbackFrame);run();
 };
 // Export hooks into the shared classic-script environment.
 globalThis.stopVisualization=stopVisualization;globalThis.visualizationChanged=visualizationChanged;globalThis.visualizationResultReady=visualizationResultReady;
 globalThis.drawBeamPlayback=drawBeamPlayback;globalThis.beamPlayback=playback;
 document.addEventListener('visibilitychange',()=>{playback.last=null});
 syncPlayback();
}
