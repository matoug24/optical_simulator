"""Reusable optical prescriptions, saved separately from bench layouts."""
import copy
import json
import math
import threading
import uuid
from pathlib import Path
from model import CATALOG, element, default_config, checked
from materials import builtins as builtin_materials

PRODUCT_FILE=Path(__file__).resolve().parent/'products.json'
LOCK=threading.Lock()
CATEGORIES={'laser':'laser','mirror_b':'mirror','mirror_c':'mirror','mirror_e':'mirror','grating':'grating','lens':'lens','polarizer':'polarization','waveplate':'polarization'}


def builtins():
    names={'laser':'Default laser · 800 nm','mirror_b':'B · round mirror','mirror_c':'C · cut-edge mirror',
           'mirror_e':'E · end mirror','grating':'Spectrogon · 1400 lines/mm','lens':'Edmund 45-805 · doublet','polarizer':'Linear polarizer','waveplate':'Quarter-wave plate · 780 nm'}
    result=[]
    for kind,values in CATALOG.items():
        properties=copy.deepcopy(values); properties.pop('name')
        result.append(dict(id='default-'+kind,type=kind,name=names[kind],properties=properties,builtin=True,category=CATEGORIES[kind]))
    custom=copy.deepcopy(next(p for p in result if p['id']=='default-lens'))
    custom.update(id='template-lens',name='Generic lens · editable doublet')
    custom['properties'].update(r1_mm=50.,r2_mm=-50.,r3_mm=-400.,glass1='constant',glass2='constant',n1=1.5,n2=1.6)
    result.append(custom)
    thin=copy.deepcopy(custom); thin.update(id='template-thin-lens',name='Generic lens · ideal thin lens')
    thin['properties']['model']='thin'; result.append(thin)
    singlet=copy.deepcopy(custom); singlet.update(id='template-prescription-lens',name='Generic singlet · surface prescription')
    mats={m['id']:m for m in builtin_materials()}
    singlet['properties'].update(model='prescription',surfaces=[
        dict(radius_mm=50.,thickness_mm=5.,clear_diameter_mm=24.,material_after=mats['constant-150']),
        dict(radius_mm=-50.,thickness_mm=0.,clear_diameter_mm=24.,material_after=mats['air'])])
    result.append(singlet)
    calmar=copy.deepcopy(result[0])
    calmar.update(id='calmar-mendocino-780-assumed',name='Calmar Mendocino · 780 nm (assumed)',
                  assumption_note='Provisional FPL-M4RFF reference: 780 nm, about 5 nm spectral FWHM; 150 mW is a reference value, not a measurement. Beam radius 0.50 mm and divergence 0.50 mrad are estimates. Confirm the installed laser and beam profile.')
    calmar['properties'].update(wavelength_nm=780.,bandwidth_nm=5.,power_mw=150.,
                                beam_radius_mm=.50,divergence_mrad=.50,rays=33,wavelength_samples=7)
    result.append(calmar)
    return result


def validate_product(product):
    if not isinstance(product,dict) or product.get('type') not in CATALOG: raise ValueError('Choose a supported product type.')
    kind=product['type']; name=product.get('name')
    if not isinstance(name,str) or not name.strip() or len(name)>100: raise ValueError('Enter a product name between 1 and 100 characters.')
    props=product.get('properties')
    if not isinstance(props,dict): raise ValueError('Product properties are missing.')
    keys=set(CATALOG[kind])-{'name'}
    if set(props)-keys: raise ValueError('A product may contain optical properties only, without bench position or orientation.')
    values={k:copy.deepcopy(props.get(k,CATALOG[kind][k])) for k in keys}
    for key,value in values.items():
        baseline=CATALOG[kind][key]
        if isinstance(baseline,bool):
            if not isinstance(value,bool): raise ValueError(f'{key} must be true or false.')
        elif isinstance(baseline,list):
            if not isinstance(value,list): raise ValueError(f'{key} must be a list.')
        elif isinstance(baseline,(int,float)):
            if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value):
                raise ValueError(f'{key} must be a finite number.')
        elif not isinstance(value,str): raise ValueError(f'{key} must be text.')
    c=default_config(); c['elements']=[element(kind,'product-check',name=name.strip(),**values)]
    checked(c)
    ident=product.get('id')
    if ident is not None and (not isinstance(ident,str) or len(ident)>80): raise ValueError('Invalid product ID.')
    return dict(id=ident,type=kind,name=name.strip(),properties=values,builtin=False,category=CATEGORIES[kind])


def _read(path):
    if not path.exists(): return []
    payload=json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(payload,dict) or payload.get('format')!='optics-products-v1' or not isinstance(payload.get('products'),list):
        raise ValueError('The saved product library has an invalid format. Keep a copy of products.json before repairing it.')
    saved=[validate_product(p) for p in payload['products']]
    ids=[p['id'] for p in saved]
    if any(not i or not i.startswith('saved-') for i in ids) or len(set(ids))!=len(ids): raise ValueError('Saved product IDs must be unique.')
    return saved


def list_products(path=None):
    with LOCK: return builtins()+_read(Path(path) if path else PRODUCT_FILE)


def save_product(product,path=None):
    item=validate_product(product); destination=Path(path) if path else PRODUCT_FILE
    with LOCK:
        saved=_read(destination)
        if item['id']:
            if not item['id'].startswith('saved-'): raise ValueError('Defaults are templates. Save your changes as a new product.')
            index=next((i for i,p in enumerate(saved) if p['id']==item['id']),None)
            if index is None: raise ValueError('This saved product no longer exists. Save it as a new product.')
            saved[index]=item
        else:
            if len(saved)>=500: raise ValueError('The library supports up to 500 saved products.')
            item['id']='saved-'+str(uuid.uuid4()); saved.append(item)
        destination.parent.mkdir(parents=True,exist_ok=True)
        data=dict(format='optics-products-v1',products=saved)
        temporary=destination.with_suffix('.tmp')
        temporary.write_text(json.dumps(data,indent=2,allow_nan=False),encoding='utf-8')
        temporary.replace(destination)
        return dict(product=item,products=builtins()+saved)
