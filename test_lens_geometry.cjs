const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs');
const g=require('./lens_geometry.js');
const example=JSON.parse(fs.readFileSync(__dirname+'/examples/complex_dispersion.json','utf8'));
const lens=example.elements.find(e=>e.id==='spectral-lens');
test('Edmund vertices and flip preserve the midpoint position datum',()=>{
 const a=g.model(lens),b=g.model({...lens,flipped:true});assert.equal(a.total,10);
 assert.deepEqual(a.surfaces.map(s=>s.vertex),[-5,1,5]);
 assert.deepEqual(b.surfaces.map(s=>b.sign*s.vertex),[5,-1,-5]);
 assert.equal(a.surfaces[0].material,'N-LAK22');assert.equal(a.surfaces[1].material,'N-SF6');
});
test('drawn curvature lies on the prescribed sphere and plane',()=>{
 const m=g.model(lens);
 for(let i=0;i<m.surfaces.length;i++)for(const [x,h] of g.profile(m,i)){
  const s=m.surfaces[i];assert.ok(Math.abs((x-s.vertex-s.radius)**2+h*h-s.radius*s.radius)<1e-7);
 }
 assert.equal(g.sag(0,12),0);assert.ok(g.sag(43.96,12)>Math.abs(g.sag(-392.21,12)));
 const flipped=g.model({...lens,flipped:true});
 for(const h of [0,3,12])assert.ok(Math.abs(g.localPoint(m,0,h,0)[0]+g.localPoint(flipped,0,h,0)[0])<1e-12);
});
test('custom assemblies retain air gaps, apertures and each surface',()=>{
 const c=JSON.parse(fs.readFileSync(__dirname+'/examples/complex_telescope.json','utf8')),e=c.elements.find(e=>e.id==='focusing-assembly'),m=g.model(e);
 assert.equal(m.surfaces.length,4);assert.equal(m.total,20);assert.equal(m.surfaces[1].air,true);
 assert.equal(m.surfaces[2].vertex-m.surfaces[1].vertex,10);
 const plate=example.elements.find(e=>e.id==='glass-plate'),p=g.model(plate);assert.ok(p.surfaces.every(s=>s.radius===0));
 assert.deepEqual(g.profile(p,0).map(q=>q[0]),Array(65).fill(-1.5));
});
test('invalid or ideal prescriptions do not invent physical surfaces',()=>{
 assert.equal(g.model({...lens,model:'thin'}),null);assert.equal(g.model({...lens,r1_mm:1}),null);
 assert.equal(g.model({...lens,t1_mm:NaN}),null);
 assert.deepEqual(g.hull([[0,0],[1,0],[1,1],[0,1],[.5,.5]]),[[0,0],[1,0],[1,1],[0,1]]);
});
