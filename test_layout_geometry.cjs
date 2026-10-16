const test=require('node:test');
const assert=require('node:assert/strict');
const g=require('./layout_geometry.js');
const near=(a,b)=>a.forEach((v,i)=>assert.ok(Math.abs(v-b[i])<1e-9,`${a} ≠ ${b}`));

test('four side cameras have the expected screen directions and near-side depth',()=>{
 near(g.raw('front',[10,20,30]),[10,-30,-20]);
 near(g.raw('back',[10,20,30]),[-10,-30,20]);
 near(g.raw('left',[10,20,30]),[-20,-30,-10]);
 near(g.raw('right',[10,20,30]),[20,-30,10]);
 near(g.raw('top',[10,20,30]),[10,-20,30]);
});
test('every camera uses orthogonal unit axes, including both corners',()=>{
 for(const view of ['top','front','back','left','right','corner-left','corner-right','3d']){
  const b=g.basis(view,.4,.8),axes=[b.u,b.v,b.depth];
  for(let i=0;i<3;i++)for(let j=0;j<3;j++)assert.ok(Math.abs(axes[i].reduce((s,v,k)=>s+v*axes[j][k],0)-(i===j?1:0))<1e-12);
 }
 assert.ok(g.basis('corner-left').depth[0]<0&&g.basis('corner-left').depth[1]<0);
 assert.ok(g.basis('corner-right').depth[0]>0&&g.basis('corner-right').depth[1]<0);
});
test('visible planes round-trip across side, corner and free cameras',()=>{
 for(const view of ['top','front','back','left','right','corner-left','corner-right','3d']){
  for(const plane of Object.keys(g.planes)){
   const p=[83.2,42.7,19.3],raw=g.raw(view,p,.2,.7),fixed=g.planes[plane].fixed;
   const q=g.unproject(view,raw.slice(0,2),plane,p[fixed],.2,.7);
   if(q)near(q,p);else assert.ok(g.axesFor(view)&&g.axesFor(view).plane!==plane);
  }
 }
});
test('edge-on planes and invalid camera scales cannot create ruler points',()=>{
 assert.equal(g.unproject('front',[0,0],'xy',20),null);
 assert.equal(g.unproject('top',[0,0],'xz',20),null);
 assert.equal(g.unproject('left',[0,0],'xz',20),null);
 assert.equal(g.screenToPlane('top',[0,0],{scale:0},'xy',0),null);
});
test('ruler distances are invariant under zoom, pan and reversed/corner views',()=>{
 for(const view of ['top','front','back','left','right','corner-left','corner-right','3d']){
  const plane=g.axesFor(view)?.plane||'xy',def=g.planes[plane],a=[20,20,20],b=a.slice();b[def.axes[0]]+=3;b[def.axes[1]]+=4;
  for(const scale of [.3,2,80]){
   const projection={scale,cx:80,cy:-30,ox:410,oy:160};
   const inverse=p=>{const q=g.raw(view,p,.7,.9),s=[(q[0]-projection.cx)*scale+projection.ox,(q[1]-projection.cy)*scale+projection.oy];return g.screenToPlane(view,s,projection,plane,a[def.fixed],.7,.9)};
   const m=g.measurement(inverse(a),inverse(b),plane,a[def.fixed]);assert.ok(Math.abs(m.distance_mm-5)<1e-9);
  }
 }
});
test('measurement refuses endpoints on different planes and checks bench bounds',()=>{
 assert.equal(g.measurement([0,0,0],[3,4,1],'xy',0),null);
 assert.equal(g.measurement([0,0,0],[3,4,0],'xy',0).distance_mm,5);
 assert.ok(g.within([300,150,100],[300,150,100]));
 assert.ok(!g.within([301,150,100],[300,150,100]));
 for(const plane of Object.keys(g.planes))for(const p of g.planeCorners(plane,20,[300,150,100]))assert.equal(p[g.planes[plane].fixed],20);
});
