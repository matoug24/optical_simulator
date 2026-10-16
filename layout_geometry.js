/* Shared orthographic camera and plane-only measurement geometry. */
(function(root){
 'use strict';
 const dot=(a,b)=>a.reduce((s,v,i)=>s+v*b[i],0);
 const orthographic={
  top:{u:[1,0,0],v:[0,-1,0],depth:[0,0,1],plane:'xy'},
  front:{u:[1,0,0],v:[0,0,-1],depth:[0,-1,0],plane:'xz'},
  back:{u:[-1,0,0],v:[0,0,-1],depth:[0,1,0],plane:'xz'},
  left:{u:[0,-1,0],v:[0,0,-1],depth:[-1,0,0],plane:'yz'},
  right:{u:[0,1,0],v:[0,0,-1],depth:[1,0,0],plane:'yz'}
 };
 const planes={xy:{axes:[0,1],fixed:2,label:'XY · horizontal',fixedName:'Z'},xz:{axes:[0,2],fixed:1,label:'XZ · vertical',fixedName:'Y'},yz:{axes:[1,2],fixed:0,label:'YZ · vertical',fixedName:'X'}};
 const corners={'corner-left':{azimuth:-3*Math.PI/4,elevation:.62},'corner-right':{azimuth:3*Math.PI/4,elevation:.62}};
 function axesFor(view){return orthographic[view==='side'?'front':view]||null}
 function basis(view,azimuth=-3*Math.PI/4,elevation=.73){
  const ortho=axesFor(view);if(ortho)return ortho;
  const preset=corners[view],a=preset?.azimuth??azimuth,e=preset?.elevation??elevation;
  return {u:[-Math.cos(a),Math.sin(a),0],v:[Math.sin(e)*Math.sin(a),Math.sin(e)*Math.cos(a),-Math.cos(e)],depth:[Math.cos(e)*Math.sin(a),Math.cos(e)*Math.cos(a),Math.sin(e)]};
 }
 function raw(view,p,a,e){const b=basis(view,a,e);return [dot(b.u,p),dot(b.v,p),dot(b.depth,p)]}
 function unproject(view,screen,plane,value,a,e){
  const p=planes[plane];if(!p||!Number.isFinite(value)||screen.some(v=>!Number.isFinite(v)))return null;
  const b=basis(view,a,e),[i,j]=p.axes,k=p.fixed,det=b.u[i]*b.v[j]-b.u[j]*b.v[i];
  if(Math.abs(det)<1e-8)return null; // A plane seen edge-on has no unique inverse.
  const x=screen[0]-b.u[k]*value,y=screen[1]-b.v[k]*value,result=[0,0,0];
  result[k]=value;result[i]=(x*b.v[j]-y*b.u[j])/det;result[j]=(y*b.u[i]-x*b.v[i])/det;return result;
 }
 function screenToPlane(view,p,projection,plane,value,a,e){
  if(!projection||!Number.isFinite(projection.scale)||projection.scale<=0)return null;
  return unproject(view,[(p[0]-projection.ox)/projection.scale+projection.cx,(p[1]-projection.oy)/projection.scale+projection.cy],plane,value,a,e);
 }
 function within(point,bounds,tolerance=1e-7){return !!point&&point.every((v,i)=>Number.isFinite(v)&&v>=-tolerance&&v<=bounds[i]+tolerance)}
 function measurement(a,b,plane,value){
  const p=planes[plane];if(!p||![a,b].every(q=>Array.isArray(q)&&q.length===3&&q.every(Number.isFinite)&&Math.abs(q[p.fixed]-value)<1e-7))return null;
  const delta=b.map((v,i)=>v-a[i]);return {distance_mm:Math.hypot(...delta),delta_mm:delta};
 }
 function planeCorners(plane,value,bounds){const p=planes[plane];return [[0,0],[bounds[p.axes[0]],0],[bounds[p.axes[0]],bounds[p.axes[1]]],[0,bounds[p.axes[1]]]].map(pair=>{const q=[0,0,0];q[p.fixed]=value;p.axes.forEach((axis,i)=>q[axis]=pair[i]);return q})}
 const api={axesFor,basis,raw,unproject,screenToPlane,within,measurement,planeCorners,planes,corners};
 if(typeof module!=='undefined'&&module.exports)module.exports=api;else root.LayoutGeometry=api;
})(typeof globalThis!=='undefined'?globalThis:this);
