/* Geometry for drawing the same spherical/planar surfaces used by the tracer. */
(function(root){
 'use strict';
 function sag(radius,height){return radius===0?0:radius-Math.sign(radius)*Math.sqrt(Math.max(0,radius*radius-height*height))}
 function model(e){
  if(e.type!=='lens'||e.model==='thin')return null;
  let rows;
  if(e.model==='prescription')rows=(e.surfaces||[]).map(s=>({radius:s.radius_mm,spacing:s.thickness_mm,clear:s.clear_diameter_mm,material:s.material_after?.name||'Material',air:s.material_after?.model==='constant'&&s.material_after.n===1}));
  else rows=[{radius:e.r1_mm,spacing:e.t1_mm,clear:e.clear_diameter_mm,material:e.glass1==='constant'?'n = '+e.n1:e.glass1},
             {radius:e.r2_mm,spacing:e.t2_mm,clear:e.clear_diameter_mm,material:e.glass2==='constant'?'n = '+e.n2:e.glass2},
             {radius:e.r3_mm,spacing:0,clear:e.clear_diameter_mm,material:'Air',air:true}];
  const radius=e.diameter_mm/2;
  if(rows.length<2||!Number.isFinite(radius)||radius<=0||rows.some(s=>![s.radius,s.spacing,s.clear].every(Number.isFinite)||s.spacing<0||s.clear<=0||(s.radius!==0&&Math.abs(s.radius)<=radius)))return null;
  const total=rows.slice(0,-1).reduce((sum,s)=>sum+s.spacing,0);let axial=-total/2;
  for(let i=0;i<rows.length;i++){rows[i]={...rows[i],vertex:axial,index:i+1};axial+=rows[i].spacing}
  return {surfaces:rows,radius,total,sign:e.flipped?-1:1};
 }
 function profile(m,index,count=65){const s=m.surfaces[index];return Array.from({length:count},(_,i)=>{const h=m.radius*(2*i/(count-1)-1);return [m.sign*(s.vertex+sag(s.radius,h)),h]})}
 function localPoint(m,index,height,angle){const s=m.surfaces[index];return [m.sign*(s.vertex+sag(s.radius,height)),height*Math.cos(angle),height*Math.sin(angle)]}
 function hull(points){
  const p=points.map(q=>q.slice(0,2)).sort((a,b)=>a[0]-b[0]||a[1]-b[1]);if(p.length<=2)return p;
  const cross=(o,a,b)=>(a[0]-o[0])*(b[1]-o[1])-(a[1]-o[1])*(b[0]-o[0]);const lower=[],upper=[];
  for(const q of p){while(lower.length>=2&&cross(lower.at(-2),lower.at(-1),q)<=0)lower.pop();lower.push(q)}
  for(const q of p.slice().reverse()){while(upper.length>=2&&cross(upper.at(-2),upper.at(-1),q)<=0)upper.pop();upper.push(q)}
  lower.pop();upper.pop();return lower.concat(upper);
 }
 const api={model,sag,profile,localPoint,hull};if(typeof module!=='undefined'&&module.exports)module.exports=api;else root.LensGeometry=api;
})(typeof globalThis!=='undefined'?globalThis:this);
