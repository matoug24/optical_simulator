"""Edmund 45-805 spherical doublet: exact geometric Snell refraction.

Radii/thicknesses: Edmund drawing 45805. Glass Sellmeier coefficients: SCHOTT.
Distances mm, wavelength nm. Local +axis runs from element A to element B.
The positioning datum is the midpoint between the two outer axial vertices.
Cement is a zero-thickness glass-to-glass interface; coatings use the separate
application transmission input. No fabricated coating phase or melt data.
"""
import numpy as np

GLASSES={
    'N-LAK22': ([1.14229781,.535138441,1.04088385],
               [.00585778594,.0198546147,100.834017]),
    'N-SF6': ([1.77931763,.338149866,2.08734474],
             [.013371418,.0617533621,174.01759])}
RADII=np.array([43.96,-42.90,-392.21])
VERTICES=np.array([-5.,1.,5.])


def normalized(v):
    v=np.asarray(v,dtype=float)
    return v/np.linalg.norm(v)


def glass_index(glass,wavelength_nm):
    b,c=GLASSES[glass]; lam2=(np.asarray(wavelength_nm)*.001)**2
    value=1+sum(bi*lam2/(lam2-ci) for bi,ci in zip(b,c))
    return np.sqrt(value)


def spherical_hit(point,direction,vertex,axis,radius):
    """Nearest forward root on the physical vertex hemisphere, not far sphere."""
    sphere=vertex+radius*axis; offset=point-sphere
    b=float(np.dot(offset,direction)); c=float(np.dot(offset,offset)-radius*radius)
    discriminant=b*b-c
    if discriminant < -1e-8: return None
    root=np.sqrt(max(discriminant,0.)); candidates=[]
    for distance in (-b-root,-b+root):
        if distance<=1e-8: continue
        hit=point+distance*direction
        axial=float(np.dot(hit-vertex,axis))
        # The vertex cap is within |R| of the vertex; opposite hemisphere isn't.
        if abs(axial-radius)>abs(radius)+1e-6: continue
        if (axial-radius)*np.sign(radius)>1e-7: continue
        candidates.append((hit,float(distance)))
    return min(candidates,key=lambda x:x[1]) if candidates else None


def refract(direction,normal,n_before,n_after):
    """Vector Snell law; normal is made to oppose the incident propagation."""
    normal=normalized(normal); direction=normalized(direction)
    if np.dot(normal,direction)>0: normal=-normal
    cosine=-float(np.dot(normal,direction)); ratio=n_before/n_after
    discriminant=1-ratio*ratio*(1-cosine*cosine)
    if discriminant < -1e-12: return None
    return normalized(ratio*direction+(ratio*cosine-np.sqrt(max(0.,discriminant)))*normal)


def prescription(lens):
    axis=lens.normal*(-1 if getattr(lens,'lens_flipped',False) else 1)
    vertices=[lens.centre+z*axis for z in VERTICES]
    return axis,vertices


def entry_hit(point,direction,lens):
    axis,vertices=prescription(lens)
    i=0 if np.dot(direction,axis)>0 else 2
    return spherical_hit(point,direction,vertices[i],axis,RADII[i])


def trace_doublet(point,direction,wavelength_nm,lens,apertures=True):
    axis,vertices=prescription(lens)
    indices=[1.,float(glass_index('N-LAK22',wavelength_nm)),
             float(glass_index('N-SF6',wavelength_nm)),1.]
    forward=np.dot(direction,axis)>0
    sequence=(0,1,2) if forward else (2,1,0)
    q=np.array(point,float); d=np.array(direction,float); records=[]
    failure=None; opl=0.
    for i in sequence:
        result=spherical_hit(q,d,vertices[i],axis,RADII[i])
        if result is None: failure='Missed L surface '+str(i+1); break
        hit,distance=result
        before,after=(indices[i],indices[i+1]) if forward else (indices[i+1],indices[i])
        radial=hit-lens.centre; radial-=np.dot(radial,axis)*axis
        margin=lens.radius-float(np.linalg.norm(radial))
        glass_opl=distance*before if before>1 else 0.
        opl+=glass_opl
        normal=(hit-(vertices[i]+RADII[i]*axis))/abs(RADII[i])
        outgoing=refract(d,normal,before,after)
        record={'surface':('S1','S2/S3','S4')[i], 'point':hit.tolist(),
                'incoming_direction':d.tolist(), 'outgoing_direction':outgoing.tolist() if outgoing is not None else None,
                'normal':normal.tolist(),'n_before':before,'n_after':after,
                'distance_from_previous_mm':distance,'glass_optical_path_segment_mm':glass_opl,
                'margin_mm':margin}
        records.append(record); q=hit
        if apertures and margin<0: failure='Clipped at L '+record['surface']; break
        if outgoing is None: failure='Total internal reflection at L '+record['surface']; break
        d=outgoing
    return {'success':failure is None and len(records)==3,'failure':failure,
            'point':q,'direction':d,'surfaces':records,'glass_optical_path_mm':opl}


def paraxial_properties(wavelength_nm=880.,flipped=False):
    """Measured from a near-axis trace, including EFL and both physical vertices."""
    class Lens: pass
    lens=Lens(); lens.centre=np.zeros(3); lens.normal=np.array([0.,0.,1.])
    lens.radius=12.; lens.lens_flipped=flipped
    height=.001
    result=trace_doublet(np.array([height,0.,-20.]),np.array([0.,0.,1.]),wavelength_nm,lens)
    q,d=result['point'],result['direction']; slope=d[0]/d[2]
    focus=q[2]-q[0]/slope
    return {'efl_mm':-height/slope,'bfl_mm':focus-5.,'focus_z_mm':focus,
            'n_lak22':float(glass_index('N-LAK22',wavelength_nm)),
            'n_sf6':float(glass_index('N-SF6',wavelength_nm))}
