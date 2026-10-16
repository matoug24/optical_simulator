"""Spherical/planar sequential prescriptions, with embedded material snapshots."""
import copy
import numpy as np
from materials import builtins, validate_material, finite


def doublet_surfaces(e):
    catalog={m['id']:m for m in builtins()}
    def material(i):
        if e['glass'+str(i)]!='constant': return copy.deepcopy(catalog[e['glass'+str(i)]])
        return dict(name='Constant glass '+str(i),model='constant',n=e['n'+str(i)],min_nm=300.,max_nm=2500.)
    return [dict(radius_mm=e['r1_mm'],thickness_mm=e['t1_mm'],clear_diameter_mm=e['clear_diameter_mm'],material_after=material(1)),
            dict(radius_mm=e['r2_mm'],thickness_mm=e['t2_mm'],clear_diameter_mm=e['clear_diameter_mm'],material_after=material(2)),
            dict(radius_mm=e['r3_mm'],thickness_mm=0.,clear_diameter_mm=e['clear_diameter_mm'],material_after=copy.deepcopy(catalog['air']))]


def sag(radius,rho):
    if radius==0: return np.zeros_like(rho,dtype=float)
    return radius-np.sign(radius)*np.sqrt(radius*radius-rho*rho)


def validate_surfaces(e):
    rows=e.get('surfaces')
    if not isinstance(rows,list) or not 2<=len(rows)<=32: raise ValueError('A lens prescription needs 2–32 surfaces.')
    positions=[0.]
    for i,row in enumerate(rows):
        if not isinstance(row,dict): raise ValueError('Each lens surface needs a definition.')
        r=finite(row.get('radius_mm'),'Surface radius',-1e6,1e6)
        if r!=0 and abs(r)<=e['diameter_mm']/2: raise ValueError('A spherical radius must exceed the blank radius; use zero for a plane.')
        clear=finite(row.get('clear_diameter_mm'),'Surface clear diameter',.01,e['diameter_mm'])
        if clear>e['clear_diameter_mm']: raise ValueError('Surface clear diameter must fit within the lens clear diameter.')
        t=finite(row.get('thickness_mm'),'Distance to next surface',0,1000)
        if i<len(rows)-1 and t<.001: raise ValueError('Adjacent surfaces need at least 0.001 mm axial separation.')
        if i==len(rows)-1 and t!=0: raise ValueError('Last surface distance must be zero.')
        row['material_after']=validate_material(row.get('material_after'))
        if i<len(rows)-1: positions.append(positions[-1]+t)
    last=rows[-1]['material_after']
    if last['model']!='constant' or last['n']!=1: raise ValueError('The last surface must exit into Air (constant index 1).')
    rho=np.linspace(0,e['diameter_mm']/2,201)
    for i in range(len(rows)-1):
        if np.any(positions[i+1]+sag(rows[i+1]['radius_mm'],rho)<=positions[i]+sag(rows[i]['radius_mm'],rho)):
            raise ValueError('Adjacent prescription surfaces cross inside the blank.')
    return rows
