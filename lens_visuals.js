'use strict';
const lensSurfaceColour=(i,n)=>i===0?'#f3c76c':i===n-1?'#7ce4de':'#c4a4ff';
function lensWorld(e,q){const f=frame(e);return vec.add([e.x_mm,e.y_mm,e.z_mm],vec.add(vec.mul(f.n,q[0]),vec.add(vec.mul(f.u,q[1]),vec.mul(f.v,q[2]))))}
function lensArrow(a,b,color){line([a,b],color,1.3);const angle=Math.atan2(b[1]-a[1],b[0]-a[0]);if(Math.hypot(b[0]-a[0],b[1]-a[1])>5)polygon([b,[b[0]-6*Math.cos(angle-.45),b[1]-6*Math.sin(angle-.45)],[b[0]-6*Math.cos(angle+.45),b[1]-6*Math.sin(angle+.45)]],color,color)}
function drawPhysicalLens(e,project,selectedLens){
 const m=LensGeometry.model(e);if(!m)return null;const count=m.surfaces.length,all=[];
 // Pick the axial cross-section with the greatest visible transverse extent.
 const centre=[e.x_mm,e.y_mm,e.z_mm],f=frame(e),p=project(centre),u=project(vec.add(centre,f.u)),v=project(vec.add(centre,f.v));
 const radial=Math.hypot(u[0]-p[0],u[1]-p[1])>=Math.hypot(v[0]-p[0],v[1]-p[1])?1:2;
 const cut=i=>LensGeometry.profile(m,i).map(([x,h])=>{const q=[x,0,0];q[radial]=h;return project(lensWorld(e,q))});
 for(let i=0;i<count-1;i++){
  const fill=m.surfaces[i].air?'#a5c9d407':i%2?'#ba94e326':'#74bceb26';polygon([...cut(i),...cut(i+1).reverse()],fill,'#8aacc01a',.5);
 }
 for(let i=0;i<count;i++){
  const color=lensSurfaceColour(i,count),ring=Array.from({length:65},(_,j)=>project(lensWorld(e,LensGeometry.localPoint(m,i,m.radius,j*2*Math.PI/64))));all.push(...ring);
  line(ring,color,selectedLens?1.5:1,i>0&&i<count-1);line(cut(i),color,selectedLens?1.8:1.15);
  for(const angle of [0,Math.PI/2,Math.PI,3*Math.PI/2]){
   const meridian=Array.from({length:25},(_,j)=>project(lensWorld(e,LensGeometry.localPoint(m,i,m.radius*j/24,angle))));line(meridian,color+'65',.7,i>0&&i<count-1);
  }
  if(i<count-1)for(const angle of [0,Math.PI/2,Math.PI,3*Math.PI/2])line([i,i+1].map(k=>project(lensWorld(e,LensGeometry.localPoint(m,k,m.radius,angle)))),'#8bbaca80',.8);
 }
 if(selectedLens||$('normals').checked){
  const first=project(lensWorld(e,[m.sign*(m.surfaces[0].vertex-8),0,0])),last=project(lensWorld(e,[m.sign*(m.surfaces.at(-1).vertex+8),0,0]));
  lensArrow(first,last,'#d5e9f0aa');
  if(selectedLens){label('S1',[first[0]-9,first[1]-11],lensSurfaceColour(0,count),10);label('S'+count,[last[0]+4,last[1]+12],lensSurfaceColour(count-1,count),10);label('⊕ datum',[p[0]+5,p[1]+28],'#b6c9d2',9)}
 }
 return LensGeometry.hull(all);
}
function drawLensInsight(canvas,e){
 const box=canvas.getBoundingClientRect(),w=box.width||260,h=220,dpr=window.devicePixelRatio||1;canvas.width=Math.round(w*dpr);canvas.height=Math.round(h*dpr);const x=canvas.getContext('2d');x.setTransform(dpr,0,0,dpr,0,0);x.fillStyle='#0c1822';x.fillRect(0,0,w,h);
 const m=LensGeometry.model(e);if(canvas.__surfaceTable)updateLensSurfaceTable(canvas.__surfaceTable,m);if(!m){x.fillStyle='#91a8b9';x.font='11px Segoe UI';x.fillText(e.model==='thin'?'Ideal thin lens: no thickness or interfaces.':'Correct the lens prescription to show its surfaces.',12,30);return}
 const profiles=m.surfaces.map((s,i)=>LensGeometry.profile(m,i)),flat=profiles.flat(),maxX=Math.max(1,...flat.map(q=>Math.abs(q[0]))),scale=Math.min((w-44)/(2*maxX+4),(h-62)/(2*m.radius)),cx=w/2,cy=h/2;
 const to=q=>[cx+q[0]*scale,cy-q[1]*scale];const path=points=>{x.beginPath();points.forEach((q,i)=>{const p=to(q);i?x.lineTo(...p):x.moveTo(...p)})};
 for(let i=0;i<profiles.length-1;i++){path([...profiles[i],...profiles[i+1].slice().reverse()]);x.closePath();x.fillStyle=m.surfaces[i].air?'#91b5c60b':i%2?'#a782d64d':'#66b5e64d';x.fill()}
 x.strokeStyle='#7f9caa';x.setLineDash([3,4]);x.beginPath();x.moveTo(cx,22);x.lineTo(cx,h-20);x.stroke();x.setLineDash([]);
 profiles.forEach((points,i)=>{path(points);x.strokeStyle=lensSurfaceColour(i,profiles.length);x.lineWidth=1.8;x.stroke();const p=to([m.sign*m.surfaces[i].vertex,0]);x.fillStyle=x.strokeStyle;x.beginPath();x.arc(p[0],p[1],2.5,0,2*Math.PI);x.fill();if(i===0||i===profiles.length-1){x.font='11px Segoe UI';x.textAlign='center';x.fillText('S'+(i+1),p[0],cy-m.radius*scale-10)}});
 x.textAlign='left';x.font='10px Segoe UI';x.fillStyle='#9bb3c2';x.fillText('Datum at midpoint · true scale',10,h-8);x.fillText('Local pose axis + →',10,14);
}
function updateLensSurfaceTable(table,m){table.innerHTML=m?'<table><thead><tr><th>Surface</th><th>Vertex offset</th><th>Radius</th><th>Material after</th></tr></thead><tbody>'+m.surfaces.map((s,i)=>'<tr><td style="color:'+lensSurfaceColour(i,m.surfaces.length)+'">S'+(i+1)+'</td><td>'+fmt(m.sign*s.vertex,2)+' mm</td><td>'+(s.radius===0?'Flat':fmt(s.radius,2)+' mm')+'</td><td>'+escape(s.material)+'</td></tr>').join('')+'</tbody></table>':''}
function renderLensInsight(parent,e){
 const card=section(parent,'Lens cross-section'),canvas=document.createElement('canvas');canvas.className='lens-insight-canvas';canvas.__optic=e;canvas.setAttribute('aria-label','Lens cross-section with surface numbers and midpoint datum');card.appendChild(canvas);
 const m=LensGeometry.model(e),note=document.createElement('p');note.className='helper';
 note.textContent=e.model==='thin'?'Ideal thin lenses have no physical surfaces. Choose a doublet or surface prescription to inspect thickness and curvature.':'S1 is the first prescribed face; the last S-number is the opposite face. Flip reverses them relative to the local pose axis. The dashed centre line is the XYZ position. Smaller |R| means stronger curvature; R = 0 is flat.';card.appendChild(note);
 const table=document.createElement('div');table.className='lens-surface-table';canvas.__surfaceTable=table;updateLensSurfaceTable(table,m);card.appendChild(table);
 requestAnimationFrame(()=>{if(canvas.isConnected!==false)drawLensInsight(canvas,e)});
}
function refreshLensInsights(){document.querySelectorAll('.lens-insight-canvas').forEach(c=>drawLensInsight(c,c.__optic))}
window.addEventListener('resize',refreshLensInsights);
