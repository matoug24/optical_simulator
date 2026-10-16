'use strict';
let productLibrary=[], productDraft=null, productSelected=null, productDirty=false, productSaving=false;
const categoryNames={laser:'Laser',mirror:'Mirror',grating:'Diffraction grating',lens:'Lens',polarization:'Polarization optic'};
const categoryFor=type=>type.startsWith('mirror')?'mirror':['polarizer','waveplate'].includes(type)?'polarization':type;

function opticalSummary(type,p){
 if(type==='polarizer')return `Linear polarizer · axis ${fmt(p.axis_deg,1)}° · extinction ${fmt(p.extinction_db,1)} dB`;
 if(type==='waveplate')return `Waveplate · retardance ${fmt(p.retardance_deg,1)}° at ${fmt(p.reference_wavelength_nm,1)} nm`;
 if(type==='laser')return `${fmt(p.wavelength_nm,1)} nm · ${fmt(p.power_mw,1)} mW · radius ${fmt(p.beam_radius_mm,2)} mm`;
 if(type==='lens'&&p.model==='prescription')return `Surface prescription · ${(p.surfaces||[]).length} surfaces · Ø ${fmt(p.clear_diameter_mm,1)} mm`;
 if(type==='lens')return p.model==='thin'?`Ideal thin lens · f ${fmt(p.focal_length_mm,1)} mm · Ø ${fmt(p.clear_diameter_mm,1)} mm`:`Spherical doublet · Ø ${fmt(p.clear_diameter_mm,1)} mm · ${p.glass1==='constant'?'n '+fmt(p.n1,4):p.glass1} / ${p.glass2==='constant'?'n '+fmt(p.n2,4):p.glass2}`;
 if(type==='grating')return `${fmt(p.lines_per_mm,0)} lines/mm · order ${p.order} · ${fmt(p.clear_width_mm,1)} × ${fmt(p.clear_height_mm,1)} mm`;
 return `Ø ${fmt(p.clear_diameter_mm,1)} mm · ${fmt(p.reflectance*100,1)}% reflectance${type==='mirror_c'?' · cut edge '+fmt(p.upper_edge_mm,1)+' mm':''}`;
}

async function loadProducts(){
 try{const response=await fetch('/api/products');const data=await response.json();if(!response.ok)throw new Error(data.error||'Unable to read products.');productLibrary=data.products;renderAddProducts();renderProductList();if(!productDraft){const initial=productLibrary.find(p=>p.id==='template-lens');if(initial)chooseProduct(initial.id)}}
 catch(error){toast('Product library: '+error.message);$('add-description').textContent=error.message;$('product-errors').textContent=error.message;$('product-save-new').disabled=true}
}

function showSection(products){
 $('bench-view').hidden=products;$('products-view').hidden=!products;
 for(const [id,active] of [['bench-tab',!products],['products-tab',products]]){$(id).classList.toggle('active',active);$(id).setAttribute('aria-selected',String(active))}
 for(const id of ['run','save','load'])$(id).hidden=products;
 if(!products)scheduleDraw();else if(!productDraft&&productLibrary.length)chooseProduct(productLibrary.find(p=>p.id==='template-lens')?.id||productLibrary[0].id);
}

function renderAddProducts(preferredId){
 const select=$('add-product'),previous=preferredId||select.value,category=$('add-category').value;select.replaceChildren();
 if(!category){select.add(new Option('Choose a category first',''));select.disabled=true;$('add-selected').disabled=true;$('add-description').textContent='Choose a default or one of your saved products.';return}
 const available=productLibrary.filter(p=>p.category===category);
 for(const [title,builtin] of [['Defaults & templates',true],['Your saved products',false]]){const group=document.createElement('optgroup');group.label=title;for(const p of available.filter(p=>p.builtin===builtin))group.appendChild(new Option(p.name,p.id));if(group.children.length)select.appendChild(group)}
 if(available.some(p=>p.id===previous))select.value=previous;
 select.disabled=!available.length;updateAddDescription();
}

function updateAddDescription(){const p=productLibrary.find(p=>p.id===$('add-product').value);$('add-selected').disabled=!p;$('add-description').textContent=p?opticalSummary(p.type,p.properties)+(p.assumption_note?' '+p.assumption_note:''):'No products available in this category.'}

function renderProductList(){
 const category=$('manage-category').value,list=$('product-list');list.replaceChildren();
 for(const [title,builtin] of [['Defaults & templates',true],['Your saved products',false]]){
  const heading=document.createElement('h3');heading.className='product-group-label';heading.textContent=title;list.appendChild(heading);
  const items=productLibrary.filter(p=>p.category===category&&p.builtin===builtin);
  if(!items.length){const empty=document.createElement('p');empty.className='helper';empty.textContent='Save a configuration to add it here.';list.appendChild(empty)}
  for(const p of items){const b=document.createElement('button');b.className='product-card'+(p.id===productSelected?' selected':'');b.innerHTML=`<span class="optic-icon" style="color:${colors[p.type]}">${icons[p.type]}</span><span><strong>${escape(p.name)}</strong><small>${escape(opticalSummary(p.type,p.properties))}</small></span>`;b.onclick=()=>chooseProduct(p.id);list.appendChild(b)}
 }
}

function chooseProduct(id){const p=productLibrary.find(p=>p.id===id);if(!p)return;productSelected=id;productDraft={type:p.type,name:p.name,...clone(p.properties)};productDirty=false;$('manage-category').value=p.category;$('product-errors').replaceChildren();renderProductList();renderProductEditor()}

function updateProductStatus(){
 const saved=productLibrary.find(p=>p.id===productSelected&&!p.builtin);
 $('product-status').textContent=productDirty?'UNSAVED CHANGES':saved?'SAVED PRODUCT':'DEFAULT TEMPLATE';$('product-status').classList.toggle('stale',productDirty);
 $('product-update').disabled=!saved||productSaving;$('product-save-new').disabled=!productDraft||productSaving;
 $('product-title').textContent=productDraft?.name||'Select a product';
}

function renderProductEditor(){
 const parent=$('product-editor');parent.replaceChildren();const e=productDraft;if(!e){updateProductStatus();return}
 const label=document.createElement('label');label.className='name-field';label.textContent='Product name';const input=document.createElement('input');input.id='product-name';input.maxLength=100;input.value=e.name;input.placeholder='e.g. 532 nm alignment laser or custom NIR lens';input.oninput=()=>{e.name=input.value;productDirty=true;updateProductStatus()};label.appendChild(input);parent.appendChild(label);
 const definition=productLibrary.find(p=>p.id===productSelected),note=document.createElement('p');note.className='helper';note.textContent=(definition?.builtin?'Use this default as a starting point. Give your configuration a name and save it as a new product.':'Edit this saved product and update it, or save a new variant with a different name.')+(definition?.assumption_note?' '+definition.assumption_note:'');parent.appendChild(note);
 renderOpticalProperties(parent,e);updateProductStatus();
}

function prescriptionFrom(e){const properties={};for(const key of Object.keys(BOOT.catalog[e.type]))if(key!=='name')properties[key]=clone(e[key]??BOOT.catalog[e.type][key]);return properties}

function draftFromBench(e){productSelected=null;productDraft={type:e.type,name:e.name,...prescriptionFrom(e)};productDirty=true;$('manage-category').value=categoryFor(e.type);showSection(true);renderProductList();renderProductEditor()}

async function saveProduct(update){
 if(!productDraft||productSaving)return;
 const invalid=$('product-editor').querySelector('input.invalid');if(invalid){invalid.focus();toast('Correct the highlighted product field.');return}
 if(!productDraft.name.trim()){toast('Enter a product name.');$('product-name').focus();return}
 const snapshot=clone(productDraft),selectedId=productSelected;productSaving=true;updateProductStatus();$('product-errors').replaceChildren();
 try{
  const product={id:update?selectedId:null,type:snapshot.type,name:snapshot.name,properties:prescriptionFrom(snapshot)};
  const response=await fetch('/api/products/save',{method:'POST',headers:{'Content-Type':'application/json','X-Optics-Token':BOOT.token},body:JSON.stringify({product})});
  const data=await response.json();if(!response.ok)throw new Error(data.error||'Unable to save product.');productLibrary=data.products;
  // Keep edits made while saving; otherwise show the newly saved definition.
  if(JSON.stringify(productDraft)===JSON.stringify(snapshot)){productSelected=data.product.id;productDraft={type:data.product.type,name:data.product.name,...clone(data.product.properties)};productDirty=false;renderProductEditor()}
  renderProductList();renderAddProducts();toast(update?'Saved product updated.':'New product saved and available on the bench.');
 }catch(error){const p=document.createElement('div');p.className='message error';p.textContent=error.message;$('product-errors').appendChild(p)}
 finally{productSaving=false;updateProductStatus()}
}

$('bench-tab').onclick=()=>showSection(false);$('products-tab').onclick=()=>showSection(true);
$('add-category').onchange=()=>renderAddProducts();$('add-product').onchange=updateAddDescription;
$('add-selected').onclick=()=>{const p=productLibrary.find(p=>p.id===$('add-product').value);if(p)addElement(p)};
$('manage-products').onclick=()=>{const category=$('add-category').value;if(category){$('manage-category').value=category;const p=productLibrary.find(p=>p.id===$('add-product').value);if(p)chooseProduct(p.id)}showSection(true)};
$('manage-category').onchange=()=>{const p=productLibrary.find(p=>p.category===$('manage-category').value);if(p)chooseProduct(p.id)};
$('product-save-new').onclick=()=>saveProduct(false);$('product-update').onclick=()=>saveProduct(true);
