const test=require('node:test'),assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs');
function setup(){
 const nodes=new Map();
 function node(tag='div'){
  return {tagName:tag.toUpperCase(),children:[],value:'',hidden:false,style:{},checked:false,textContent:'',classList:{contains:()=>false},
   append(...children){this.children.push(...children)},appendChild(c){this.append(c)},
   replaceChildren(){this.children=[];if(this.tagName==='SELECT')this.value=''},
   add(o){this.children.push(o);if(this.children.length===1)this.value=String(o.value)}};
 }
 function $(id){if(!nodes.has(id))nodes.set(id,node(['analysis-source','analysis-target','analysis-visit','surface-interface','sensitivity-element'].includes(id)?'select':'div'));return nodes.get(id)}
 const base={incident_power_mw:1,after_power_mw:.9,centroid_mm:[0,0],equivalent_radius_mm:[1,1],bound_mm:2,density_mw_mm2:[[1,0],[0,0]],zoom_bound_mm:1,zoom_center_mm:[0,0],zoom_density_mw_mm2:[[1,0],[0,0]],samples:[],ray_hits:1};
 const footprints=[{source_id:'s',id:'lens',visit:2,interface:1},{source_id:'s',id:'lens',visit:1,interface:1},{source_id:'s',id:'lens',visit:2,interface:2},{source_id:'other',id:'lens',visit:3,interface:1}].map(p=>({...base,...p}));
 const c=vm.createContext({$,document:{querySelectorAll:()=>[],createElement:node},Option:function(text,value){this.text=text;this.value=value},ResizeObserver:class{observe(){}},config:{elements:[{id:'s',name:'Source',type:'laser',enabled:true},{id:'lens',name:'Lens',type:'lens',enabled:true}]},result:{footprints,chiefs:[]},fmt:String,escape:String});
 vm.runInContext(fs.readFileSync(__dirname+'/analyses.js','utf8').replace(/renderAnalysisSettings\(\);renderAnalyses\(\);\s*$/,''),c);
 vm.runInContext("globalThis.drawn=[];renderSurfaceProfile=(p,c,r)=>drawn.push({visit:p.visit,visits:p.visits?.map(v=>v.visit),face:p.interface,canvas:c,readout:r});clearPlot=()=>{};activePanel='surfaces';",c);
 return {$,run:s=>vm.runInContext(s,c)};
}
test('Surface Beams defaults to All and renders every visit of the selected interface',()=>{
 const t=setup();t.run('renderAnalyses()');
 assert.equal(t.$('analysis-visit').value,'all');assert.deepEqual(t.$('analysis-visit').children.map(o=>o.text),['All','1','2']);
 assert.equal(t.run('JSON.stringify(drawn[0].visits)'),'[1,2]');assert.equal(t.run('drawn.length'),1);assert.equal(t.run("drawn[0].canvas"),'surface-canvas');assert.equal(t.$('surface-visits').children.filter(c=>c.tagName==='CANVAS').length,0);assert.equal(t.$('surface-canvas').hidden,false);
 assert.deepEqual(t.$('surface-interface').children.map(o=>o.value),['1','2']);
});
test('individual visits remain selectable and survive rerenders',()=>{
 const t=setup();t.run("renderAnalyses();drawn=[];$('analysis-visit').value='2';$('analysis-visit').onchange();renderAnalyses()");
 assert.equal(t.$('analysis-visit').value,'2');assert.equal(t.run('drawn.every(p=>p.visit===2)'),true);assert.equal(t.$('surface-canvas').hidden,false);assert.equal(t.$('surface-visits').children.length,0);
});
test('All stays scoped to Surface Beams and other analyses get a numeric visit',()=>{
 const t=setup();t.run("renderAnalyses();activePanel='field';refreshSelection()");
 assert.equal(t.$('analysis-visit').value,'1');assert.equal(t.run('targetSelection().visit'),1);
 t.run("activePanel='surfaces';renderAnalyses()");assert.equal(t.$('analysis-visit').value,'all');
});
test('All supports interface changes and empty ray records',()=>{
 const t=setup();t.run("renderAnalyses();drawn=[];$('surface-interface').value='2';renderAnalyses()");
 assert.equal(t.run('JSON.stringify(drawn[0].visits)'),'[2]');
 t.run('result.footprints=[];renderAnalyses()');assert.equal(t.$('analysis-visit').value,'all');assert.match(t.$('surface-readout').innerHTML,/Run a simulation/);
});
test('combined density preserves integrated power across different zoom windows',()=>{
 const t=setup();
 t.run("globalThis.profiles=result.footprints.slice(0,2).map((p,i)=>({...p,zoom_bound_mm:i+1,zoom_center_mm:[i*5,0],zoom_density_mw_mm2:[[1,2],[3,4]]}));globalThis.merged=combineSurfaceVisits(profiles)");
 const expected=10*1**2+10*2**2;
 assert.ok(Math.abs(t.run('merged.zoom_density_mw_mm2.flat().reduce((a,b)=>a+b,0)*(2*merged.zoom_bound_mm/96)**2')-expected)<1e-9);
 assert.ok(Math.abs(t.run('merged.density_mw_mm2.flat().reduce((a,b)=>a+b,0)*(2*merged.bound_mm/64)**2')-8)<1e-9);
 assert.ok(t.run('merged.zoom_bound_mm>=7'));
});
test('combined moments include the separation between visits and preserve input records',()=>{
 const t=setup();t.run("globalThis.profiles=result.footprints.slice(0,2).map((p,i)=>({...p,centroid_mm:[i*4,0],incident_power_mw:1}));globalThis.merged=combineSurfaceVisits(profiles)");
 assert.equal(t.run('merged.centroid_mm[0]'),2);assert.ok(Math.abs(t.run('merged.equivalent_radius_mm[0]')-Math.sqrt(17))<1e-12);
 assert.equal(t.run('merged.incident_power_mw'),2);assert.equal(t.run('profiles[0].incident_power_mw'),1);assert.equal(t.run('profiles[0].centroid_mm[0]'),0);
});
test('visit markers use the shared diagram transform and distinct legend colours',()=>{
 const t=setup();t.run("globalThis.calls=[];globalThis.x={beginPath(){},ellipse(...a){calls.push(a)},stroke(){},setLineDash(){},moveTo(){},lineTo(){},fillText(text){calls.push(text)}};drawSurfaceVisitMarkers(x,p=>[100+p[0]*10,100-p[1]*10],10,result.footprints.slice(0,2))");
 assert.equal(t.run('calls[0][0]'),100);assert.equal(t.run('calls[0][2]'),10);assert.equal(t.run('calls[1]'),'Visit 2');assert.equal(t.run('surfaceVisitColour(0)!==surfaceVisitColour(1)'),true);
});
