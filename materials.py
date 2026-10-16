"""Portable, explicitly bounded optical material definitions and local library."""
import copy
import json
import threading
import uuid
from pathlib import Path
import numpy as np

MATERIAL_FILE=Path(__file__).resolve().parent/'materials.json'
LOCK=threading.Lock()


def builtins():
    return [dict(id='air',name='Air · n = 1 approximation',model='constant',n=1.,min_nm=300.,max_nm=2500.,reference='Ambient index approximated as 1.',builtin=True),
            dict(id='constant-150',name='Generic glass · constant 1.50',model='constant',n=1.5,min_nm=300.,max_nm=2500.,reference='Illustrative nondispersive material.',builtin=True),
            dict(id='N-LAK22',name='SCHOTT N-LAK22',model='sellmeier',B=[1.14229781,.535138441,1.04088385],C=[.00585778594,.0198546147,100.834017],min_nm=365.,max_nm=2500.,reference='SCHOTT nominal Sellmeier coefficients; wavelength in micrometres. Confirm range and temperature for precision work.',builtin=True),
            dict(id='N-SF6',name='SCHOTT N-SF6',model='sellmeier',B=[1.77931763,.338149866,2.08734474],C=[.013371418,.0617533621,174.01759],min_nm=365.,max_nm=2500.,reference='SCHOTT nominal Sellmeier coefficients; wavelength in micrometres. Confirm range and temperature for precision work.',builtin=True)]


def finite(value,label,lo,hi):
    if isinstance(value,bool) or not isinstance(value,(int,float)) or not np.isfinite(value) or not lo<=value<=hi:
        raise ValueError(f'{label} must be a finite number between {lo} and {hi}.')
    return float(value)


def validate_material(data):
    if not isinstance(data,dict): raise ValueError('Material definition is missing.')
    m=copy.deepcopy(data)
    if not isinstance(m.get('name'),str) or not m['name'].strip() or len(m['name'])>100: raise ValueError('Enter a material name up to 100 characters.')
    m['name']=m['name'].strip()
    if m.get('model') not in ('constant','sellmeier','table'): raise ValueError('Unknown material dispersion model.')
    low=finite(m.get('min_nm'),'Material minimum wavelength',300,2500)
    high=finite(m.get('max_nm'),'Material maximum wavelength',300,2500)
    if low>=high: raise ValueError('Material minimum wavelength must be below maximum.')
    if not isinstance(m.get('reference',''),str) or len(m.get('reference',''))>1000: raise ValueError('Material reference must be text up to 1000 characters.')
    if m.get('id') is not None and (not isinstance(m['id'],str) or len(m['id'])>80): raise ValueError('Invalid material ID.')
    if m['model']=='constant': m['n']=finite(m.get('n'),'Refractive index',1,5)
    elif m['model']=='sellmeier':
        for key in ('B','C'):
            if not isinstance(m.get(key),list) or len(m[key])!=3: raise ValueError('Sellmeier requires three B and three C coefficients.')
            m[key]=[finite(v,'Sellmeier '+key,-1e5,1e5) for v in m[key]]
        if any((low*.001)**2<=c<=(high*.001)**2 for c in m['C']): raise ValueError('A Sellmeier pole lies inside the declared wavelength range.')
    else:
        rows=m.get('table')
        if not isinstance(rows,list) or not 2<=len(rows)<=1000: raise ValueError('Index table needs 2–1000 wavelength/index pairs.')
        clean=[]
        for row in rows:
            if not isinstance(row,list) or len(row)!=2: raise ValueError('Each index-table row needs wavelength in nm and index.')
            clean.append([finite(row[0],'Table wavelength',300,2500),finite(row[1],'Table index',1,5)])
        if any(b[0]<=a[0] for a,b in zip(clean,clean[1:])): raise ValueError('Table wavelengths must increase strictly without duplicates.')
        if low<clean[0][0] or high>clean[-1][0]: raise ValueError('Table must cover the entire declared wavelength range.')
        m['table']=clean
    indices=material_index(m,np.linspace(low,high,129))
    if np.any((indices<1)|(indices>5)): raise ValueError('Material index must remain between 1 and 5 over its range.')
    return m


def material_index(m,wavelength_nm):
    wl=np.asarray(wavelength_nm,dtype=float)
    if np.any(~np.isfinite(wl)) or np.any(wl<m['min_nm']-1e-9) or np.any(wl>m['max_nm']+1e-9):
        raise ValueError(f"{m['name']}: wavelength outside {m['min_nm']:g}–{m['max_nm']:g} nm; extrapolation is disabled.")
    if m['model']=='constant': result=np.full_like(wl,m['n'])
    elif m['model']=='table':
        rows=np.asarray(m['table']); result=np.interp(wl,rows[:,0],rows[:,1])
    else:
        l2=(wl*.001)**2
        with np.errstate(divide='ignore',invalid='ignore'):
            result=np.sqrt(1+sum(b*l2/(l2-c) for b,c in zip(m['B'],m['C'])))
    if np.any(~np.isfinite(result)) or np.any(result<1) or np.any(result>5): raise ValueError('Material has an invalid refractive index at this wavelength.')
    return result


def _read(path):
    if not path.exists(): return []
    try:
        payload=json.loads(path.read_text(encoding='utf-8'))
        if not isinstance(payload,dict) or payload.get('format')!='optics-materials-v1' or not isinstance(payload.get('materials'),list): raise ValueError('Invalid material library format.')
        items=[validate_material(m) for m in payload['materials']]
        ids=[m.get('id') for m in items]
        if any(not i or not i.startswith('material-') for i in ids) or len(set(ids))!=len(ids): raise ValueError('Material IDs must be unique saved IDs.')
        for m in items: m['builtin']=False
        return items
    except (json.JSONDecodeError,TypeError,KeyError) as exc: raise ValueError('Cannot read material library; preserve materials.json before repairing it.') from exc


def list_materials(path=None):
    with LOCK: return builtins()+_read(Path(path) if path else MATERIAL_FILE)


def save_material(data,path=None):
    item=validate_material(data); destination=Path(path) if path else MATERIAL_FILE
    with LOCK:
        items=_read(destination); ident=item.get('id')
        if ident:
            index=next((i for i,m in enumerate(items) if m['id']==ident),None)
            if index is None: raise ValueError('Save a default material as a new material.')
            items[index]=item
        else:
            if len(items)>=500: raise ValueError('At most 500 custom materials are supported.')
            item['id']='material-'+str(uuid.uuid4()); items.append(item)
        item['builtin']=False
        destination.parent.mkdir(parents=True,exist_ok=True)
        temporary=destination.with_suffix('.tmp')
        temporary.write_text(json.dumps(dict(format='optics-materials-v1',materials=items),allow_nan=False,indent=2),encoding='utf-8')
        temporary.replace(destination)
        return dict(material=item,materials=builtins()+items)
