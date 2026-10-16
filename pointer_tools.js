'use strict';
let pointerActive=false,pointerPixel=null,pointerOffsets={xy:null,xz:null,yz:null};
function pointerAxes(){return LayoutGeometry.axesFor(view)}
function pointerOffset(){return pointerOffsets[pointerAxes()?.plane]??0}
function syncPointerControls(clear=false){
 const axes=pointerAxes(),button=$('pointer-toggle');if(clear)pointerPixel=null;
 if(!axes){pointerActive=false;pointerPixel=null}
 button.disabled=!axes;button.title=axes?'Show XYZ on the current view plane':'Pointer is available in Top, Front, Back, Left and Right views';button.classList.toggle('active',pointerActive);button.setAttribute('aria-pressed',String(pointerActive));button.textContent=pointerActive?'Pointer on':'Pointer';
 $('pointer-controls').hidden=!pointerActive;$('pointer-readout').hidden=!pointerActive;
 if(!axes)return;
 const plane=LayoutGeometry.planes[axes.plane],bound=[config.bench.width_mm,config.bench.depth_mm,config.bench.height_mm][plane.fixed];
 if(pointerOffsets[axes.plane]===null&&pointerActive){const e=selectedElement();pointerOffsets[axes.plane]=Math.max(0,Math.min(bound,e?[e.x_mm,e.y_mm,e.z_mm][plane.fixed]:0))}
 if(pointerOffset()>bound){pointerOffsets[axes.plane]=bound;pointerPixel=null}
 $('pointer-plane-name').textContent=plane.label;$('pointer-offset-label').textContent=plane.fixedName+' position / mm';$('pointer-offset').value=pointerOffset();$('pointer-offset').max=bound;$('pointer-offset').classList.remove('invalid');renderPointerReadout();
}
function resetPlanePointer(){pointerActive=false;pointerPixel=null;pointerOffsets={xy:null,xz:null,yz:null};syncPointerControls()}
function pointerPosition(){
 const axes=pointerAxes();if(!pointerActive||!axes||!pointerPixel||$('pointer-offset').classList.contains('invalid'))return null;
 const q=LayoutGeometry.screenToPlane(view,pointerPixel,projection,axes.plane,pointerOffset(),azimuth,elevation);
 return LayoutGeometry.within(q,[config.bench.width_mm,config.bench.depth_mm,config.bench.height_mm])?q:null;
}
function renderPointerReadout(){
 const output=$('pointer-readout');output.hidden=!pointerActive;if(!pointerActive)return;
 if($('pointer-offset').classList.contains('invalid')){output.textContent='Enter a valid plane position inside the working volume.';return}
 const axes=pointerAxes(),q=pointerPosition(),plane=axes&&LayoutGeometry.planes[axes.plane];if(!plane)return;
 const fixed=plane.fixedName+' = '+fmt(pointerOffset(),3)+' mm';
 output.textContent=q?q.map((v,i)=>'XYZ'[i]+' '+fmt(v,3)+' mm').join(' · ')+' · '+plane.label+' ('+fixed+' fixed)':pointerPixel?'Cursor outside the working area.':'Move over the layout · '+plane.label+' · '+fixed+' is fixed, not inferred from object depth.';
}
function drawPlanePointer(project){
 if(!pointerActive)return;
 const axes=pointerAxes();if(!axes){syncPointerControls();return}
 const plane=LayoutGeometry.planes[axes.plane],bounds=[config.bench.width_mm,config.bench.depth_mm,config.bench.height_mm];$('pointer-offset').max=bounds[plane.fixed];
 if(pointerOffset()>bounds[plane.fixed])syncPointerControls(true);
 renderPointerReadout();const q=pointerPosition();if(!q){$('pointer-coords').textContent='—';return}
 $('pointer-coords').textContent=q.map((v,i)=>'XYZ'[i]+' '+fmt(v,2)).join(' · ')+' mm';
 const p=project(q),w=canvas.getBoundingClientRect().width,h=canvas.getBoundingClientRect().height;
 line([[p[0]-10,p[1]],[p[0]+10,p[1]]],'#b3e6ff',1);line([[p[0],p[1]-10],[p[0],p[1]+10]],'#b3e6ff',1);
 const left=Math.max(4,Math.min(w-151,p[0]+15)),top=Math.max(80,Math.min(h-75,p[1]-54));ctx.fillStyle='#0b2132ed';ctx.fillRect(left,top,147,65);ctx.strokeStyle='#5d98b2';ctx.strokeRect(left,top,147,65);
 for(let i=0;i<3;i++)label('XYZ'[i]+'  '+fmt(q[i],3)+' mm',[left+9,top+17+i*18],'#beeaff',11);
}
$('pointer-toggle').onclick=()=>{
 if(!pointerAxes())return;pointerActive=!pointerActive;pointerPixel=null;drag=null;
 if(pointerActive){rulerActive=false;rulerHover=null;syncRulerControls()}
 syncPointerControls();updateLayoutHint();scheduleDraw();
};
$('pointer-offset').oninput=()=>{
 const input=$('pointer-offset'),n=input.valueAsNumber,valid=Number.isFinite(n)&&input.checkValidity();input.classList.toggle('invalid',!valid);pointerPixel=null;
 if(valid&&pointerAxes())pointerOffsets[pointerAxes().plane]=n;renderPointerReadout();scheduleDraw();
};
syncPointerControls();
