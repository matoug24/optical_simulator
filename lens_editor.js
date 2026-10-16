'use strict';
let materialLibrary=[],materialDraft=null,materialBusy=false;
const materialCopy=id=>clone(materialLibrary.find(m=>m.id===id));

function surfaceDefaults(e){
 const material=i=>e['glass'+i]==='constant'?{name:'Constant glass '+i,model:'constant',n:e['n'+i],min_nm:300,max_nm:2500}:materialCopy(e['glass'+i]);
 return [1,2,3].map(i=>({radius_mm:e['r'+i+'_mm'],thickness_mm:i===3?0:e['t'+i+'_mm'],clear_diameter_mm:e.clear_diameter_mm,material_after:i===3?materialCopy('air'):material(i)}));
}
function refreshLensEditor(e){if(e===productDraft)renderProductEditor();else renderInspector()}
function renderSurfaceEditor(parent,e){
 const box=document.createElement('div');box.className='surface-editor';parent.appendChild(box);
 if(!materialLibrary.length){box.textContent='Load the material library before editing surfaces.';return}
 if(!e.surfaces?.length){e.surfaces=surfaceDefaults(e);edited(e)}
 const intro=document.createElement('p');intro.className='helper';intro.textContent='Forward order: air → surface 1 → … → air. Radius R = 0 is flat; positive R has its centre of curvature downstream. Distance is the vertex spacing to the next surface. Choose Air after a surface to create a gap. Each surface keeps a material snapshot.';box.appendChild(intro);
 e.surfaces.forEach((row,i)=>{
  const card=document.createElement('div');card.className='surface-card';const heading=document.createElement('h4');heading.textContent='Surface '+(i+1);card.appendChild(heading);
  const grid=document.createElement('div');grid.className='field-grid';card.appendChild(grid);
  for(const [key,label,lo,hi] of [['radius_mm','Signed radius / mm',-1e6,1e6],['thickness_mm','Distance to next / mm',0,1000],['clear_diameter_mm','Clear diameter / mm',.01,500]]){
   const l=document.createElement('label');l.textContent=label;const input=document.createElement('input');input.type='number';input.step='any';input.min=lo;input.max=hi;input.value=row[key];input.setAttribute('aria-label',`Surface ${i+1} ${label}`);
   if(i===e.surfaces.length-1&&key==='thickness_mm')input.disabled=true;
   input.oninput=()=>{const value=input.valueAsNumber;if(!Number.isFinite(value)||!input.checkValidity()){input.classList.add('invalid');return}input.classList.remove('invalid');row[key]=value;edited(e)};l.appendChild(input);grid.appendChild(l);
  }
  const label=document.createElement('label');label.className='field-full';label.textContent='Material after this surface';const select=document.createElement('select');select.setAttribute('aria-label','Surface '+(i+1)+' material');select.add(new Option('Embedded: '+row.material_after.name,''));
  for(const m of materialLibrary)select.add(new Option(m.name+(m.builtin?'':' · saved'),m.id));select.value='';
  if(i===e.surfaces.length-1)select.disabled=true;
  select.onchange=()=>{if(!select.value)return;row.material_after=materialCopy(select.value);edited(e);refreshLensEditor(e)};label.appendChild(select);grid.appendChild(label);
  const note=document.createElement('p');note.className='helper';const m=row.material_after;note.textContent=`${m.model} · ${m.min_nm}–${m.max_nm} nm${m.model==='constant'?' · n = '+m.n:''}${i===e.surfaces.length-1?' · exit into air':''}`;card.appendChild(note);
  const actions=document.createElement('div');actions.className='surface-actions';
  const action=(text,disabled,fn)=>{const b=document.createElement('button');b.textContent=text;b.disabled=disabled;b.onclick=()=>{fn();edited(e);refreshLensEditor(e)};actions.appendChild(b)};
  action('Move up',i===0||i===e.surfaces.length-1,()=>{[e.surfaces[i-1],e.surfaces[i]]=[e.surfaces[i],e.surfaces[i-1]]});
  action('Move down',i>=e.surfaces.length-2,()=>{[e.surfaces[i+1],e.surfaces[i]]=[e.surfaces[i],e.surfaces[i+1]]});
  action('Remove',e.surfaces.length<=2||i===e.surfaces.length-1,()=>e.surfaces.splice(i,1));card.appendChild(actions);box.appendChild(card);
 });
 const add=document.createElement('button');add.textContent='＋ Insert surface before exit';add.disabled=e.surfaces.length>=32;add.onclick=()=>{e.surfaces.splice(e.surfaces.length-1,0,{radius_mm:0,thickness_mm:5,clear_diameter_mm:e.clear_diameter_mm,material_after:materialCopy('air')});edited(e);refreshLensEditor(e)};box.appendChild(add);
 const manage=document.createElement('button');manage.className='text-button';manage.textContent='Configure materials →';manage.onclick=()=>{showSection(true);document.querySelector('.material-library').open=true;$('material-select').scrollIntoView({block:'center'})};box.appendChild(manage);
}

function renderMaterialOptions(preferred){
 const s=$('material-select');s.replaceChildren();for(const m of materialLibrary)s.add(new Option(m.name+(m.builtin?' · default':' · saved'),m.id));
 if(preferred&&materialLibrary.some(m=>m.id===preferred))s.value=preferred;
}
function chooseMaterial(id){materialDraft=materialCopy(id);renderMaterialEditor();$('material-message').textContent=''}
function renderMaterialEditor(){
 const box=$('material-editor');box.replaceChildren();const m=materialDraft;if(!m)return;
 const text=(key,label,type='text',value=m[key],commit=null)=>{const l=document.createElement('label');l.textContent=label;const input=document.createElement('input');input.type=type;input.id='material-'+key;input.value=value??'';if(type==='number')input.step='any';input.oninput=()=>{let v=type==='number'?input.valueAsNumber:input.value;if(type==='number'&&!Number.isFinite(v)){input.classList.add('invalid');return}input.classList.remove('invalid');if(commit)commit(v);else m[key]=v};l.appendChild(input);box.appendChild(l)};
 text('name','Material name');text('reference','Manufacturer / data reference');
 const l=document.createElement('label');l.textContent='Index model';const select=document.createElement('select');select.id='material-model';for(const [value,label] of [['constant','Constant index'],['sellmeier','Sellmeier · 3 terms'],['table','Measured n(λ) table']])select.add(new Option(label,value));select.value=m.model;select.onchange=()=>{m.model=select.value;m.n??=1.5;m.B??=[1,0,0];m.C??=[.01,0,0];m.table??=[[m.min_nm,1.5],[m.max_nm,1.49]];renderMaterialEditor()};l.appendChild(select);box.appendChild(l);
 text('min_nm','Minimum valid wavelength / nm','number');text('max_nm','Maximum valid wavelength / nm','number');
 if(m.model==='constant')text('n','Refractive index','number');
 if(m.model==='sellmeier'){
  for(const key of ['B','C'])for(let i=0;i<3;i++)text(key+(i+1),key+(i+1)+(key==='C'?' / μm²':''),'number',m[key][i],value=>m[key][i]=value);
  const note=document.createElement('p');note.className='helper field-full';note.textContent='n²(λ) = 1 + Σ Bᵢ λ² / (λ² − Cᵢ), with λ in μm. Enter Cᵢ as squared-wavelength coefficients, not resonance wavelengths.';box.appendChild(note);
 }
 if(m.model==='table'){
  const label=document.createElement('label');label.className='field-full';label.textContent='Wavelength / nm, index · one pair per line';const area=document.createElement('textarea');area.id='material-table';area.rows=7;area.value=m.table.map(row=>row.join(', ')).join('\n');
  area.oninput=()=>{const rows=area.value.trim().split(/\n/).map(line=>line.trim().split(/[,;\s]+/).map(Number));const bad=rows.some(row=>row.length!==2||row.some(v=>!Number.isFinite(v)));area.classList.toggle('invalid',bad);if(!bad)m.table=rows};label.appendChild(area);box.appendChild(label);
  const note=document.createElement('p');note.className='helper field-full';note.textContent='Table indices are interpolated linearly, without extrapolation. Suitable for ray angles; use a smooth manufacturer dispersion formula for femtosecond GVD because piecewise-linear data has derivative discontinuities.';box.appendChild(note);
 }
 $('material-update').disabled=materialBusy||!m.id||m.builtin;$('material-save').disabled=materialBusy;
}
async function loadMaterials(){try{const response=await fetch('/api/materials');const r=await response.json();if(!response.ok)throw Error(r.error);materialLibrary=r.materials;renderMaterialOptions('N-LAK22');chooseMaterial('N-LAK22');if(productDraft)renderProductEditor()}catch(error){$('material-message').textContent=error.message}}
async function saveMaterial(update){
 if(materialBusy||!materialDraft)return;if($('material-editor').querySelector('.invalid')){toast('Correct the highlighted material field.');return}
 const snapshot=clone(materialDraft),payload=clone(snapshot);if(!update)payload.id=null;materialBusy=true;$('material-save').disabled=true;$('material-update').disabled=true;
 try{const response=await fetch('/api/materials/save',{method:'POST',headers:{'Content-Type':'application/json','X-Optics-Token':BOOT.token},body:JSON.stringify({material:payload})}),r=await response.json();if(!response.ok)throw Error(r.error);materialLibrary=r.materials;renderMaterialOptions(r.material.id);if(JSON.stringify(materialDraft)===JSON.stringify(snapshot)){materialDraft=clone(r.material);renderMaterialEditor()}$('material-message').textContent='Saved. Choose this material in a surface prescription. Existing embedded lens data is unchanged.';toast('Material saved.')}catch(error){$('material-message').textContent=error.message}finally{materialBusy=false;$('material-save').disabled=false;$('material-update').disabled=!materialDraft.id||materialDraft.builtin}
}
$('material-select').onchange=()=>chooseMaterial($('material-select').value);
$('material-new').onclick=()=>{materialDraft={name:'New optical material',model:'constant',n:1.5,min_nm:350,max_nm:1100,reference:''};renderMaterialEditor();$('material-message').textContent='New material · unsaved'};
$('material-save').onclick=()=>saveMaterial(false);$('material-update').onclick=()=>saveMaterial(true);
loadMaterials();
