/* Component tests with a minimal DOM/canvas: no browser or external state. */
const test=require('node:test'),assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs');
function setup(){
 const elements=new Map(),context=new Proxy({measureText:text=>({width:text.length*6})},{get:(o,k)=>o[k]??(()=>{})});
 function element(id){if(elements.has(id))return elements.get(id);const classes=new Set();const e={id,value:0,checked:id==='ruler-snap-elements',style:{},textContent:'',width:900,height:500,clientHeight:500,hidden:false,disabled:false,
  classList:{contains:k=>classes.has(k),add:k=>classes.add(k),remove:k=>classes.delete(k),toggle:(k,b)=>{if(b??!classes.has(k))classes.add(k);else classes.delete(k)}},
  setAttribute(){},getBoundingClientRect:()=>({left:0,top:0,width:900,height:500}),getContext:()=>context,addEventListener(){},focus(){},setPointerCapture(){},hasPointerCapture:()=>false,releasePointerCapture(){},
  checkValidity(){return Number.isFinite(this.valueAsNumber)&&this.valueAsNumber>=Number(this.min||0)&&this.valueAsNumber<=Number(this.max??Infinity)},
  get valueAsNumber(){return this.value===''?NaN:Number(this.value)}};elements.set(id,e);return e}
 const c=vm.createContext({document:{getElementById:element,addEventListener(){}},BOOT:{defaults:{bench:{width_mm:300,depth_mm:150,height_mm:100},elements:[{id:'laser',name:'Laser',type:'laser',enabled:true,x_mm:100,y_mm:75,z_mm:20,azimuth_deg:0,elevation_deg:0,roll_deg:0}]},catalog:{}},window:{devicePixelRatio:1,addEventListener(){}},requestAnimationFrame(){},ResizeObserver:class{observe(){}},setTimeout(){},clearTimeout(){},console});
 for(const file of ['layout_geometry.js','lens_geometry.js','workbench.js','lens_visuals.js','pointer_tools.js','layout_tools.js'])vm.runInContext(fs.readFileSync(__dirname+'/'+file,'utf8'),c,{filename:file});
 vm.runInContext('renderList=()=>{};renderInspector=()=>{};select=id=>{selected=id};toast=()=>{};draw();',c);
 return {c,element,run:code=>vm.runInContext(code,c)};
}
test('all view presets render and corner orbit switches to the free camera',()=>{
 const t=setup();for(const view of ['top','front','back','left','right','corner-left','corner-right','3d'])assert.doesNotThrow(()=>t.run(`setLayoutView('${view}');draw();`));
 t.run("setLayoutView('corner-left');draw();canvas.onpointerdown({button:0,clientX:850,clientY:450,pointerId:1});canvas.onpointermove({clientX:860,clientY:450});");
 assert.equal(t.run('view'),'3d');assert.equal(t.element('layout-view').value,'3d');
});
test('plane ruler measures two clicks without moving an element',()=>{
 const t=setup();t.run("$('ruler-toggle').onclick();draw();");
 t.run("function clickPoint(q){const r=rawProject(q),x=(r[0]-projection.cx)*projection.scale+projection.ox,y=(r[1]-projection.cy)*projection.scale+projection.oy;canvas.onpointerdown({button:0,clientX:x,clientY:y,pointerId:1});canvas.onpointerup({type:'pointerup',clientX:x,clientY:y,pointerId:1})};clickPoint([100,75,0]);clickPoint([103,79,0]);draw();");
 assert.match(t.element('ruler-readout').textContent,/Distance: 5.000 mm/);
 assert.equal(t.run('config.elements[0].x_mm'),100);assert.equal(t.run('rulerPoints[0][2]'),0);
 // Third click starts a fresh measurement; switching plane clears it.
 t.run('clickPoint([20,20,0]);');assert.equal(t.run('rulerPoints.length'),1);
 t.run("setLayoutView('back');draw();");assert.equal(t.run('rulerPlane'),'xz');assert.equal(t.run('rulerPoints.length'),0);
});
test('ruler refuses an edge-on plane and snaps only to coplanar centres',()=>{
 const t=setup();t.run("$('ruler-toggle').onclick();$('ruler-plane').value='xz';$('ruler-plane').onchange();draw();");
 assert.match(t.element('ruler-readout').textContent,/edge-on/);assert.equal(t.run('rulerWorldAt([450,250])'),null);
 t.run("$('ruler-plane').value='xy';$('ruler-plane').onchange();$('ruler-offset').value=20;$('ruler-offset').oninput();draw();const r=rawProject([100,75,20]);globalThis.nearCentre=[(r[0]-projection.cx)*projection.scale+projection.ox+2,(r[1]-projection.cy)*projection.scale+projection.oy];");
 assert.equal(t.run('rulerWorldAt(nearCentre)[0]'),100);assert.equal(t.run('rulerWorldAt(nearCentre)[2]'),20);
 t.run("$('ruler-offset').value='';$('ruler-offset').oninput();");assert.equal(t.run('rulerWorldAt(nearCentre)'),null);
});
test('back-view drag and left/right keyboard movement preserve the hidden coordinate',()=>{
 const t=setup();t.run("setLayoutView('back');draw();globalThis.s=rawProject([100,75,20]);globalThis.p=[(s[0]-projection.cx)*projection.scale+projection.ox,(s[1]-projection.cy)*projection.scale+projection.oy];globalThis.scale=projection.scale;canvas.onpointerdown({button:0,clientX:p[0],clientY:p[1],pointerId:1});canvas.onpointermove({clientX:p[0]+10,clientY:p[1]-5});canvas.onpointerup({type:'pointerup',clientX:p[0]+10,clientY:p[1]-5,pointerId:1});");
 assert.ok(Math.abs(t.run('config.elements[0].x_mm')-(100-10/t.run('scale')))<1e-9);assert.equal(t.run('config.elements[0].y_mm'),75);
 assert.ok(t.run('config.elements[0].z_mm')>20);
 t.run("setLayoutView('left');canvas.onkeydown({key:'ArrowRight',preventDefault(){}});");assert.equal(t.run('config.elements[0].y_mm'),74.9);
 t.run("setLayoutView('right');canvas.onkeydown({key:'ArrowRight',preventDefault(){}});");assert.equal(t.run('config.elements[0].y_mm'),75);
});

test('selecting an optic with small cursor movement preserves its position and trace',()=>{
 const t=setup();t.run("globalThis.s=rawProject([100,75,20]);globalThis.p=[(s[0]-projection.cx)*projection.scale+projection.ox,(s[1]-projection.cy)*projection.scale+projection.oy];canvas.onpointerdown({button:0,clientX:p[0],clientY:p[1],pointerId:1});canvas.onpointermove({clientX:p[0]+1,clientY:p[1]+1});canvas.onpointerup({type:'pointerup',clientX:p[0]+1,clientY:p[1]+1,pointerId:1});");
 assert.equal(t.run('revision'),0);assert.equal(t.run('config.elements[0].x_mm'),100);assert.equal(t.run('config.elements[0].y_mm'),75);
});

test('locked optics resist dragging and keyboard movement in every plane, then unlock',()=>{
 const t=setup();t.run("setElementLocked(config.elements[0],true)");
 for(const view of ['top','front','back','left','right']){
  t.run(`setLayoutView('${view}');draw();globalThis.s=rawProject([100,75,20]);globalThis.p=[(s[0]-projection.cx)*projection.scale+projection.ox,(s[1]-projection.cy)*projection.scale+projection.oy];canvas.onpointerdown({button:0,clientX:p[0],clientY:p[1],pointerId:1});canvas.onpointermove({clientX:p[0]+30,clientY:p[1]+20});canvas.onpointerup({type:'pointerup',clientX:p[0]+30,clientY:p[1]+20,pointerId:1});canvas.onkeydown({key:'ArrowRight',preventDefault(){}});`);
  assert.equal(t.run('config.elements[0].x_mm'),100);assert.equal(t.run('config.elements[0].y_mm'),75);assert.equal(t.run('config.elements[0].z_mm'),20);assert.equal(t.run('revision'),0);assert.equal(t.run('view'),view);
 }
 t.run("setElementLocked(config.elements[0],false);setLayoutView('top');canvas.onkeydown({key:'ArrowRight',preventDefault(){}})");assert.equal(t.run('config.elements[0].x_mm'),100.1);assert.equal(t.run('revision'),1);
});

test('Pointer reports XYZ on the chosen plane and follows side-view hidden coordinates',()=>{
 const t=setup();t.run("selected='laser';$('pointer-toggle').onclick();draw();globalThis.p=rawProject([120,65,20]);canvas.onpointermove({clientX:(p[0]-projection.cx)*projection.scale+projection.ox,clientY:(p[1]-projection.cy)*projection.scale+projection.oy});draw();");
 assert.match(t.element('pointer-readout').textContent,/X 120.000 mm · Y 65.000 mm · Z 20.000 mm/);
 assert.equal(t.run('pointerPosition()[2]'),20);
 t.run("setLayoutView('back');draw();");assert.equal(t.run('pointerOffset()'),75);
 t.run("setLayoutView('left');draw();");assert.equal(t.run('pointerOffset()'),100);
 assert.equal(t.run('config.elements[0].x_mm'),100);
});
test('Pointer is unavailable in spatial views and rejects invalid/outside positions',()=>{
 const t=setup();t.run("$('pointer-toggle').onclick();draw();pointerPixel=[-900,-900];draw();");assert.equal(t.run('pointerPosition()'),null);
 assert.match(t.element('pointer-readout').textContent,/outside/);
 t.run("$('pointer-offset').value='';$('pointer-offset').oninput();");assert.equal(t.run('pointerPosition()'),null);
 for(const view of ['corner-left','corner-right','3d']){t.run(`setLayoutView('${view}');$('pointer-toggle').onclick();draw();`);assert.equal(t.run('pointerActive'),false);assert.equal(t.element('pointer-toggle').disabled,true);assert.equal(t.element('pointer-readout').hidden,true)}
});
test('Pointer and ruler have separate plane state and are mutually exclusive',()=>{
 const t=setup();t.run("$('ruler-toggle').onclick();$('pointer-toggle').onclick();");assert.equal(t.run('rulerActive'),false);assert.equal(t.run('pointerActive'),true);
 t.run("$('ruler-toggle').onclick();");assert.equal(t.run('pointerActive'),false);assert.equal(t.run('rulerActive'),true);
 t.run("$('pointer-toggle').onclick();resetLayoutRuler();");assert.equal(t.run('pointerActive'),false);assert.equal(t.run('pointerPixel'),null);
});
test('physical lens surfaces and selected datum render in every view',()=>{
 const t=setup(),example=JSON.parse(fs.readFileSync(__dirname+'/examples/complex_dispersion.json','utf8')),lens=example.elements.find(e=>e.id==='spectral-lens');
 t.run('config.elements.push('+JSON.stringify(lens)+');selected='+JSON.stringify(lens.id)+';');
 for(const view of ['top','front','back','left','right','corner-left','corner-right','3d']){
  assert.doesNotThrow(()=>t.run(`setLayoutView('${view}');draw();`));assert.ok(t.run("hits.find(h=>h.id==='spectral-lens').shape.length")>2);
 }
 assert.doesNotThrow(()=>t.run("config.elements[1].flipped=true;draw();drawLensInsight(canvas,config.elements[1]);"));
});
