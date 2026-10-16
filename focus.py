"""Power-weighted geometric focus within the next uninterrupted traced segment."""
import numpy as np
from model import checked, simulate, frame, boundary
from diagnostics import encounter
from materials import finite


def focus_analysis(config,source_id,target_id,visit=1,max_distance_mm=200.):
    limit=finite(max_distance_mm,'Focus search distance',.001,10000)
    c=checked(config)
    source=next((e for e in c['elements'] if e['id']==source_id and e['type']=='laser' and e['enabled']),None)
    if source is None: raise ValueError('Choose an enabled laser.')
    # Trace this source only, retaining every sample rather than the display subset.
    c['elements']=[e for e in c['elements'] if e['type']!='laser' or e['id']==source_id]
    result=simulate(c,retain_rays=True)
    chief=result['chiefs'][0]; event=encounter(chief,target_id,visit)
    if event is None or event.get('outgoing_direction') is None: raise ValueError('The chief ray needs to leave the selected element.')
    origin=np.array(event['exit_point']); axis=np.array(event['outgoing_direction']); u,v=frame(axis)
    samples=[]; excluded=0; total=len(result['rays']); warnings=[]
    low=0.; high=limit
    for ray in result['rays']:
        hit=encounter(ray,target_id,visit)
        if hit is None or hit.get('outgoing_direction') is None or hit['power_after']<=0:
            excluded+=1; continue
        q=np.array(hit['exit_point']); d=np.array(hit['outgoing_direction']); den=float(d@axis)
        if den<=1e-8:
            excluded+=1; continue
        index=ray['events'].index(hit)
        # Next physical encounter or the bench boundary ends the straight segment.
        end=np.array(ray['events'][index+1]['point']) if index+1<len(ray['events']) else np.array(ray['points'][-1])
        length=max(0.,float((end-q)@d))
        _,wall=boundary(q,d,c['bench']); length=min(length,wall)
        a=float((q-origin)@axis); low=max(low,a)
        high=min(high,a+length*den)
        base=q-origin-d*a/den
        slopes=d/den
        samples.append(dict(wavelength_nm=ray['wavelength_nm'],weight=source['power_mw']*ray['weight']*hit['power_after'],
                            intercept=[float(base@u),float(base@v)],slope=[float(slopes@u),float(slopes@v)]))
    if not samples: raise ValueError('No surviving sampled rays leave this element.')
    # Keep the cohort fixed over the whole search to prevent clipping from faking a focus.
    low=max(0.,low)+1e-6; high-=1e-6
    if high<=low: raise ValueError('No common forward plane exists before the next optic/boundary for all surviving rays. Choose a different target or reduce beam spread.')
    distances=np.linspace(low,high,121)
    def measure(items):
        weights=np.array([r['weight'] for r in items]); power=float(weights.sum()); weights/=power
        a=np.array([r['intercept'] for r in items]); b=np.array([r['slope'] for r in items])
        ca=weights@a; cb=weights@b; da=a-ca; db=b-cb
        aa=float(weights@np.sum(da*da,axis=1)); ab=float(weights@np.sum(da*db,axis=1)); bb=float(weights@np.sum(db*db,axis=1))
        stationary=-ab/bb if bb>1e-24 else None
        s=float(np.clip(stationary,low,high)) if stationary is not None else low
        offset=ca+s*cb; points=a+s*b; variance=weights@((points-offset)**2)
        rms=float(np.sqrt(max(0.,variance.sum())))
        radial=np.linalg.norm(points-offset,axis=1); order=np.argsort(radial)
        encircled=float(radial[order[min(len(order)-1,int(np.searchsorted(np.cumsum(weights[order]),.8))) ]])
        edge=stationary is None or stationary<=low+1e-5 or stationary>=high-1e-5
        return dict(distance_mm=s,rms_radius_mm=rms,encircled_80_radius_mm=encircled,radius_2sigma_mm=(2*np.sqrt(np.maximum(variance,0))).tolist(),
                    centroid_uv_mm=offset.tolist(),position_mm=(origin+s*axis+offset[0]*u+offset[1]*v).tolist(),power_mw=power,
                    ray_count=len(items),boundary_limited=edge,resolved=len(items)>=3 and bb>1e-24,
                    curve_rms_mm=np.sqrt(np.maximum(0,aa+2*ab*distances+bb*distances**2)).tolist())
    combined=measure(samples)
    rows=[]
    for wl in sorted({r['wavelength_nm'] for r in samples}):
        row=measure([r for r in samples if r['wavelength_nm']==wl]); row['wavelength_nm']=wl; rows.append(row)
    if excluded: warnings.append(f'{excluded} of {total} sampled rays did not leave the target with a usable forward direction. Results describe surviving power only.')
    if any(not row['resolved'] for row in rows): warnings.append('At least one wavelength has fewer than three rays or no angular spread; a unique focus is not resolved. Increase source rays and check convergence.')
    if combined['boundary_limited'] or any(r['boundary_limited'] for r in rows): warnings.append('A minimum lies at a search limit, or the bundle has no unique waist. Extend the requested range if possible; the next optic or bench boundary still limits the search.')
    if high<limit-1e-4: warnings.append('Search was shortened to keep the same ray cohort between this optic and the next encounter/bench boundary.')
    valid=[r['distance_mm'] for r in rows if r['resolved'] and not r['boundary_limited']]
    if max(r['rms_radius_mm'] for r in rows)<1e-6: warnings.append('Very small geometric spots omit diffraction; these radii are not physical diffraction-limited waist predictions.')
    spot=np.array([r['intercept'] for r in samples])+combined['distance_mm']*np.array([r['slope'] for r in samples])
    spot-=np.array(combined['centroid_uv_mm'])
    stride=max(1,int(np.ceil(len(samples)/1600)))
    spot_samples=[dict(uv_mm=spot[i].tolist(),wavelength_nm=samples[i]['wavelength_nm']) for i in range(0,len(samples),stride)]
    centroids=[]
    for row in rows:
        selected=[s for s in samples if s['wavelength_nm']==row['wavelength_nm']]
        w=np.array([s['weight'] for s in selected]); w/=w.sum()
        p=np.array([s['intercept'] for s in selected])+combined['distance_mm']*np.array([s['slope'] for s in selected])
        centroids.append(w@p)
    lateral=max(float(np.linalg.norm(a-b)) for a in centroids for b in centroids)
    return dict(combined=combined,wavelengths=rows,scan_distance_mm=distances.tolist(),search_interval_mm=[low,high],
                spot_samples=spot_samples,lateral_colour_separation_mm=lateral,
                origin_mm=origin.tolist(),axis=axis.tolist(),chromatic_focal_shift_mm=float(max(valid)-min(valid)) if len(valid)>1 else None,
                surviving_power_mw=combined['power_mw'],sampled_rays=total,excluded_rays=excluded,warnings=warnings,
                method='Power-weighted RMS geometric radius on planes perpendicular to the outgoing central chief ray. Each wavelength and the combined spectrum are minimized analytically within one fixed-cohort straight segment. Combined radius includes wavelength-centroid separation. This does not optimize pulse duration or include diffraction. Check ray and wavelength convergence.')
