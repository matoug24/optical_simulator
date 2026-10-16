const test=require('node:test'),assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs');
const G=require('./visualization.js');
test('beam advances at 50 mm/s through reflected and vertical segments by arc length',()=>{
 const p=G.prepare({points:[[0,0,0],[30,0,0],[30,40,0],[30,40,20]]});
 assert.equal(p.length,90);assert.deepEqual(G.front(p,G.speed_mm_s).tip,[30,20,0]);assert.deepEqual(G.front(p,80).tip,[30,40,10]);
 assert.deepEqual(G.front(p,100).points,p.points);assert.equal(G.front(p,100).finished,true);
});
test('all branches share a launch clock and diverge only after their shared segment',()=>{
 const a=G.prepare({points:[[0,0,0],[30,0,0],[30,40,0]]}),b=G.prepare({points:[[0,0,0],[30,0,0],[30,-40,0]]});
 assert.deepEqual(G.front(a,20).tip,G.front(b,20).tip);
 assert.deepEqual(G.front(a,50).tip,[30,20,0]);assert.deepEqual(G.front(b,50).tip,[30,-20,0]);
});
test('empty, duplicate and zero-length points do not break playback',()=>{
 assert.equal(G.front(G.prepare({points:[]}),1).tip,null);
 const p=G.prepare({points:[[0,0,0],[0,0,0],[10,0,0]]});assert.deepEqual(G.front(p,5).tip,[5,0,0]);assert.deepEqual(G.front(p,-1).tip,[0,0,0]);
});
function setup(){
 const nodes=new Map(),frames=new Map(),timers=new Map(),listeners=new Map();let next=0;
 const $=id=>{if(!nodes.has(id))nodes.set(id,{textContent:'',hidden:false,checked:true,classList:{toggle(){}},setAttribute(){},querySelector:()=>null});return nodes.get(id)};
 const c=vm.createContext({$,document:{hidden:false,addEventListener:(k,f)=>listeners.set(k,f)},result:{rays:[{points:[[0,0,0],[100,0,0]],source_id:'s',wavelength_nm:780}],chiefs:[],spectral_chiefs:[]},fmt:n=>n.toFixed(1),run:()=>{c.runs++},runs:0,scheduleDraw(){},toast(){},line(){},wavelengthColor:()=>'',ctx:{beginPath(){},arc(){},fill(){}},requestAnimationFrame:f=>{frames.set(++next,f);return next},cancelAnimationFrame:id=>frames.delete(id),setTimeout:f=>{timers.set(++next,f);return next},clearTimeout:id=>timers.delete(id)});
 vm.runInContext(fs.readFileSync(__dirname+'/visualization.js','utf8'),c);
 function frame(time){const [id,f]=frames.entries().next().value;frames.delete(id);f(time)}
 return {c,$,frames,timers,listeners,frame,run:s=>vm.runInContext(s,c)};
}
test('Visualize traces, animates in real seconds, repeats and stops cleanly',()=>{
 const t=setup();t.$('visualize').onclick();assert.equal(t.c.runs,1);assert.equal(t.run('beamPlayback.active'),true);
 t.run('visualizationResultReady()');t.frame(0);t.frame(1000);assert.equal(t.run('beamPlayback.travel'),50);
 t.frame(2000);assert.equal(t.run('beamPlayback.travel'),100);t.frame(3000);assert.equal(t.run('beamPlayback.travel'),25);
 t.$('visualize').onclick();assert.equal(t.frames.size,0);assert.equal(t.run('beamPlayback.active'),false);assert.equal(t.$('visualization-status').hidden,true);
});
test('moving an optic schedules one retrace and resets playback to the new paths',()=>{
 const t=setup();t.$('visualize').onclick();t.run('visualizationResultReady()');t.frame(0);t.frame(1000);
 t.run('visualizationChanged();visualizationChanged()');assert.equal(t.timers.size,1);assert.equal(t.run('beamPlayback.ready'),false);
 [...t.timers.values()][0]();assert.equal(t.c.runs,2);t.run('visualizationResultReady()');assert.equal(t.run('beamPlayback.travel'),0);
});
test('all available ray families animate and an empty trace stops with no orphan frames',()=>{
 const t=setup();t.$('visualize').onclick();t.run('result.spectral_chiefs=[result.rays[0]];result.chiefs=[result.rays[0]];visualizationResultReady()');assert.equal(t.run('beamPlayback.paths.length'),3);
 t.run('result={rays:[],chiefs:[]};visualizationResultReady()');assert.equal(t.run('beamPlayback.active'),false);assert.equal(t.frames.size,0);
});
test('visibility changes pause the playback clock instead of jumping ahead',()=>{
 const t=setup();t.$('visualize').onclick();t.run('visualizationResultReady()');t.frame(0);t.frame(1000);t.listeners.get('visibilitychange')();t.frame(100000);assert.equal(t.run('beamPlayback.travel'),50);
});
