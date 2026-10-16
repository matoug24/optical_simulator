'use strict';
let rulerActive=false,rulerPlane='xy',rulerOffsets={xy:0,xz:0,yz:0},rulerPoints=[],rulerHover=null;
const benchBounds=()=>[config.bench.width_mm,config.bench.depth_mm,config.bench.height_mm];
const isSpatialView=()=>!LayoutGeometry.axesFor(view);

function setLayoutView(next){
 view=next;const preset=LayoutGeometry.corners[next];if(preset){azimuth=preset.azimuth;elevation=preset.elevation}
 zoom=1;pan=[0,0];drag=null;$('layout-view').value=view;
 const orthographic=LayoutGeometry.axesFor(view);
 if(orthographic&&rulerPlane!==orthographic.plane){rulerPlane=orthographic.plane;rulerPoints=[];rulerHover=null}
 syncRulerControls();syncPointerControls(true);updateLayoutHint();scheduleDraw();
}
function updateLayoutHint(){
 $('interaction-hint').textContent=rulerActive?'Ruler: click A, then B · Shift-drag to pan · Esc to exit':pointerActive?'Pointer: XYZ on the selected plane · Drag to move · Esc to exit':isSpatialView()?'Click to select · Drag to orbit · Shift-drag to pan · Scroll to zoom':'Click to select · Drag to move · Shift-drag to pan · Scroll to zoom';
 canvas.style.cursor=rulerActive?'crosshair':isSpatialView()?'grab':'crosshair';
}
function rulerPlaneValid(){return !$('ruler-offset').classList.contains('invalid')&&!!LayoutGeometry.unproject(view,[0,0],rulerPlane,rulerOffsets[rulerPlane],azimuth,elevation)}
function syncRulerControls(){
 const plane=LayoutGeometry.planes[rulerPlane],input=$('ruler-offset'),bounds=benchBounds();
 if(rulerOffsets[rulerPlane]>bounds[plane.fixed]){rulerOffsets[rulerPlane]=bounds[plane.fixed];rulerPoints=[];rulerHover=null}
 if(rulerPoints.some(p=>!LayoutGeometry.within(p,bounds))){rulerPoints=[];rulerHover=null}
 $('ruler-plane').value=rulerPlane;$('ruler-offset-label').textContent=plane.fixedName+' position / mm';input.max=bounds[plane.fixed];input.value=rulerOffsets[rulerPlane];input.classList.remove('invalid');
 $('ruler-toggle').classList.toggle('active',rulerActive);$('ruler-toggle').setAttribute('aria-pressed',String(rulerActive));$('ruler-toggle').textContent=rulerActive?'Ruler on':'Ruler';
 $('ruler-controls').hidden=!rulerActive;renderRulerStatus();
}
function resetLayoutRuler(){resetPlanePointer();rulerPoints=[];rulerHover=null;rulerOffsets={xy:0,xz:0,yz:0};if($('ruler-offset'))syncRulerControls()}
function renderRulerStatus(){
 const status=$('ruler-readout');if(!rulerActive){status.hidden=true;return}status.hidden=false;
 if(!rulerPlaneValid()){status.textContent='This plane is edge-on or its position is invalid. Choose a matching side/top view, a corner view, or another plane.';return}
 const plane=LayoutGeometry.planes[rulerPlane],name=plane.fixedName+' = '+fmt(rulerOffsets[rulerPlane],2)+' mm';
 const end=rulerPoints[1]||(rulerPoints.length===1?rulerHover:null),a=rulerPoints[0],m=a&&end?LayoutGeometry.measurement(a,end,rulerPlane,rulerOffsets[rulerPlane]):null;
 if(m)status.textContent=`${rulerPoints.length===2?'Distance':'Preview'}: ${fmt(m.distance_mm,3)} mm (${fmt(m.distance_mm/10,3)} cm) · ΔX ${fmt(m.delta_mm[0],3)} · ΔY ${fmt(m.delta_mm[1],3)} · ΔZ ${fmt(m.delta_mm[2],3)} mm · ${name} · A [${a.map(v=>fmt(v,2)).join(', ')}] → B [${end.map(v=>fmt(v,2)).join(', ')}] mm`;
 else status.textContent=`${plane.label}, ${name}. ${a?'Point A set. Click point B.':'Click point A, then point B inside the working area.'} Points are constrained to this plane.`;
}
function rulerWorldAt(p){
 if(!rulerPlaneValid())return null;
 let q=LayoutGeometry.screenToPlane(view,p,projection,rulerPlane,rulerOffsets[rulerPlane],azimuth,elevation);
 if(!LayoutGeometry.within(q,benchBounds()))return null;
 // Snap to an optic centre only when it actually lies on the selected plane.
 if($('ruler-snap-elements').checked){
  const fixed=LayoutGeometry.planes[rulerPlane].fixed;
  const candidates=config.elements.map(e=>[e.x_mm,e.y_mm,e.z_mm]).filter(c=>Math.abs(c[fixed]-rulerOffsets[rulerPlane])<1e-7&&LayoutGeometry.within(c,benchBounds()));
  let best=10;
  for(const c of candidates){const s=rawProject(c),x=(s[0]-projection.cx)*projection.scale+projection.ox,y=(s[1]-projection.cy)*projection.scale+projection.oy,d=Math.hypot(x-p[0],y-p[1]);if(d<best){best=d;q=c}}
 }
 if($('ruler-snap-grid').checked&&!config.elements.some(e=>q[0]===e.x_mm&&q[1]===e.y_mm&&q[2]===e.z_mm&&$('ruler-snap-elements').checked)){
  for(const axis of LayoutGeometry.planes[rulerPlane].axes)q[axis]=Math.round(q[axis]);
 }
 return LayoutGeometry.within(q,benchBounds())?q:null;
}
function drawLayoutGrid(project){
 const bounds=benchBounds(),ortho=LayoutGeometry.axesFor(view),plane=ortho?.plane||'xy',fixed=LayoutGeometry.planes[plane].fixed;
 const farFace=view==='back'?config.bench.depth_mm:view==='right'?config.bench.width_mm:0;
 const coordinate=view==='top'?0:farFace;
 const corners=LayoutGeometry.planeCorners(plane,coordinate,bounds);polygon(corners.map(project),'#132332','#385468');
 let spacing=10;while(Math.max(...bounds)/spacing>60)spacing*=2;
 const [i,j]=LayoutGeometry.planes[plane].axes;
 for(let a=0;a<=bounds[i];a+=spacing){const p=[0,0,0],q=[0,0,0];p[fixed]=q[fixed]=coordinate;p[i]=q[i]=a;q[j]=bounds[j];line([p,q].map(project),'#25374a',.6)}
 for(let a=0;a<=bounds[j];a+=spacing){const p=[0,0,0],q=[0,0,0];p[fixed]=q[fixed]=coordinate;p[j]=q[j]=a;q[i]=bounds[i];line([p,q].map(project),'#25374a',.6)}
 if(isSpatialView()){
  for(const [x,y] of [[0,0],[bounds[0],0],[bounds[0],bounds[1]],[0,bounds[1]]])line([[x,y,0],[x,y,bounds[2]]].map(project),'#33495e',.7,true);
  line([[0,0,bounds[2]],[bounds[0],0,bounds[2]],[bounds[0],bounds[1],bounds[2]],[0,bounds[1],bounds[2]],[0,0,bounds[2]]].map(project),'#33495e',.7,true);
 }
 const origin=[0,0,0];origin[fixed]=coordinate;
 for(const axis of isSpatialView()?[0,1,2]:[i,j]){
  const p=origin.slice();p[axis]+=Math.min(28,bounds[axis]/5);const c=['#d5998f','#72b3ad','#89a4dd'][axis];line([origin,p].map(project),c,2);label('+'+'XYZ'[axis],vec.add(project(p),[5,-5]),c);
 }
 if(ortho){
  label('0',vec.add(project(origin),[-12,17]));
  for(const axis of [i,j])for(let a=50;a<=bounds[axis];a+=Math.max(50,spacing*5)){const p=origin.slice();p[axis]=a;label(fmt(a/10,0),vec.add(project(p),axis===i?[-4,17]:[-26,4]))}
  label('Grid: cm · '+(view==='top'?'looking down −Z':view==='front'?'front, looking +Y':view==='back'?'back, looking −Y':view==='left'?'left, looking +X':'right, looking −X'),[20,canvas.clientHeight-42],'#8cabbc',10);
 }
}
function drawLayoutRuler(project){
 if(!rulerActive)return;
 const plane=LayoutGeometry.planes[rulerPlane],bounds=benchBounds();
 $('ruler-offset').max=bounds[plane.fixed];
 if(rulerOffsets[rulerPlane]>bounds[plane.fixed]||rulerPoints.some(p=>!LayoutGeometry.within(p,bounds)))syncRulerControls();
 renderRulerStatus();if(!rulerPlaneValid())return;
 polygon(LayoutGeometry.planeCorners(rulerPlane,rulerOffsets[rulerPlane],bounds).map(project),'#72dbd50a','#72dbd555');
 const a=rulerPoints[0],b=rulerPoints[1]||(a?rulerHover:null);
 for(const [p,name] of [[a,'A'],[b,'B']])if(p){const s=project(p);ctx.beginPath();ctx.arc(s[0],s[1],4,0,2*Math.PI);ctx.fillStyle='#a3fff1';ctx.fill();line([[s[0]-8,s[1]],[s[0]+8,s[1]]],'#a3fff1',1);line([[s[0],s[1]-8],[s[0],s[1]+8]],'#a3fff1',1);label(name,[s[0]+9,s[1]-7],'#bcfff7',12)}
 if(a&&b){const m=LayoutGeometry.measurement(a,b,rulerPlane,rulerOffsets[rulerPlane]);if(!m)return;const x=project(a),y=project(b);line([x,y],'#a3fff1',2,rulerPoints.length<2);const text=fmt(m.distance_mm,3)+' mm',mid=[(x[0]+y[0])/2,(x[1]+y[1])/2];ctx.font='12px Segoe UI';const width=ctx.measureText(text).width;ctx.fillStyle='#0d2529ed';ctx.fillRect(mid[0]-width/2-6,mid[1]-24,width+12,20);label(text,[mid[0]-width/2,mid[1]-10],'#bafff4',12)}
}

$('layout-view').onchange=()=>setLayoutView($('layout-view').value);
$('ruler-toggle').onclick=()=>{rulerActive=!rulerActive;if(rulerActive){pointerActive=false;pointerPixel=null;syncPointerControls()}drag=null;syncRulerControls();updateLayoutHint();scheduleDraw()};
$('ruler-plane').onchange=()=>{rulerPlane=$('ruler-plane').value;rulerPoints=[];rulerHover=null;syncRulerControls();scheduleDraw()};
$('ruler-offset').oninput=()=>{const input=$('ruler-offset'),n=input.valueAsNumber;const valid=Number.isFinite(n)&&input.checkValidity();input.classList.toggle('invalid',!valid);rulerPoints=[];rulerHover=null;if(valid)rulerOffsets[rulerPlane]=n;renderRulerStatus();scheduleDraw()};
$('ruler-clear').onclick=()=>{rulerPoints=[];rulerHover=null;renderRulerStatus();scheduleDraw()};
for(const id of ['ruler-snap-grid','ruler-snap-elements'])$(id).onchange=()=>{rulerHover=null;scheduleDraw()};

function pointerWorld(p){const axes=LayoutGeometry.axesFor(view);return axes?LayoutGeometry.screenToPlane(view,p,projection,axes.plane,0,azimuth,elevation):null}
canvas.onpointerdown=ev=>{
 if(ev.button!==0)return;canvas.focus({preventScroll:true});const p=atPointer(ev),hit=hitTest(p);
 if(rulerActive&&!ev.shiftKey){drag={kind:'ruler',p,last:p,moved:false};canvas.setPointerCapture(ev.pointerId);return}
 if(hit&&!ev.shiftKey)select(hit);
 drag={kind:'layout',p,last:p,element:hit&&!ev.shiftKey&&!isSpatialView()?selectedElement():null,start:hit?clone(selectedElement()):null,pan:ev.shiftKey||(!hit&&!isSpatialView()),moved:false};canvas.setPointerCapture(ev.pointerId);
};
canvas.onpointermove=ev=>{
 const p=atPointer(ev);if(pointerActive){pointerPixel=p;scheduleDraw()}const world=rulerActive?rulerWorldAt(p):pointerWorld(p),plane=LayoutGeometry.planes[rulerActive?rulerPlane:LayoutGeometry.axesFor(view)?.plane];
 if(world&&plane)$('pointer-coords').textContent=plane.axes.map(i=>'XYZ'[i]+' '+fmt(world[i],1)).join(' · ')+' mm';else $('pointer-coords').textContent='—';
 if(rulerActive){rulerHover=world;canvas.style.cursor=rulerPlaneValid()?'crosshair':'not-allowed';scheduleDraw()}
 if(!drag){if(!rulerActive)canvas.style.cursor=isSpatialView()?'grab':config.elements.find(e=>e.id===hitTest(p))?.locked?'default':hitTest(p)?'grab':'crosshair';return}
 const dx=p[0]-drag.last[0],dy=p[1]-drag.last[1];if(Math.hypot(p[0]-drag.p[0],p[1]-drag.p[1])>3)drag.moved=true;
 if(drag.kind==='ruler'){drag.last=p;return}
 if(drag.element){
  if(drag.element.locked){drag.last=p;return}
  if(!drag.moved){drag.last=p;return}
  const from=pointerWorld(drag.p),to=pointerWorld(p),axes=LayoutGeometry.planes[LayoutGeometry.axesFor(view).plane].axes,bounds=benchBounds(),e=drag.element;
  for(const i of axes){const key=['x_mm','y_mm','z_mm'][i];e[key]=Math.max(0,Math.min(bounds[i],drag.start[key]+to[i]-from[i]));if($('prop-'+key))$('prop-'+key).value=Number(e[key].toFixed(3))}changed();renderList();
 }else if(drag.pan){pan[0]+=dx;pan[1]+=dy;scheduleDraw()}
 else{if(view!=='3d'){view='3d';$('layout-view').value='3d'}azimuth-=dx*.009;elevation=Math.max(.08,Math.min(1.5,elevation+dy*.008));scheduleDraw()}
 drag.last=p;
};
function finishLayoutDrag(ev){
 if(drag?.kind==='ruler'&&ev.type==='pointerup'&&!drag.moved){const q=rulerWorldAt(atPointer(ev));if(q){if(rulerPoints.length===2)rulerPoints=[];rulerPoints.push(q);rulerHover=null;renderRulerStatus();scheduleDraw()}else toast('Choose two points inside a visible horizontal or vertical measurement plane.')}
 if(drag?.element&&drag.moved)renderInspector();drag=null;if(canvas.hasPointerCapture(ev.pointerId))canvas.releasePointerCapture(ev.pointerId);
}
canvas.onpointerup=finishLayoutDrag;canvas.onpointercancel=finishLayoutDrag;
canvas.onpointerleave=()=>{pointerPixel=null;renderPointerReadout();if(!drag){rulerHover=null;renderRulerStatus();scheduleDraw()}};
canvas.onkeydown=ev=>{
 if(ev.key==='Escape'){if(typeof stopVisualization==='function')stopVisualization();pointerActive=false;pointerPixel=null;syncPointerControls();rulerActive=false;drag=null;rulerHover=null;syncRulerControls();updateLayoutHint();scheduleDraw();return}
 const e=selectedElement(),axes=LayoutGeometry.axesFor(view);if(rulerActive||!e||e.locked||!axes||!['ArrowLeft','ArrowRight','ArrowUp','ArrowDown'].includes(ev.key))return;
 ev.preventDefault();const step=ev.shiftKey?1:.1,bounds=benchBounds(),dx=ev.key==='ArrowRight'?step:ev.key==='ArrowLeft'?-step:0,dy=ev.key==='ArrowDown'?step:ev.key==='ArrowUp'?-step:0;
 for(let i=0;i<3;i++){const delta=axes.u[i]*dx+axes.v[i]*dy;if(delta){const key=['x_mm','y_mm','z_mm'][i];e[key]=Math.max(0,Math.min(bounds[i],e[key]+delta))}}changed();renderList();renderInspector();
};
syncRulerControls();updateLayoutHint();
