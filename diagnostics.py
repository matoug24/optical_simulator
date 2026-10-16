"""Surface-local beam records and finite-difference alignment diagnostics.

Footprint projection and central finite differences follow the established GVD
app, extended to arbitrary elements, visits, wavelengths and lens interfaces.
"""
import copy
import math
import numpy as np
from model import checked, WorkSurface, pose_frame, pose_from_frame, unit, rotate, frame, trace, simulate, grating, grating_angles
from polarization import source_jones, unpack, stokes


def footprints(config,surfaces,rays):
    lookup={s.name:s for s in surfaces}; sources={e['id']:e for e in config['elements'] if e['type']=='laser'}
    groups={}
    for ray in rays:
        source=sources[ray['source_id']]; weight=source['power_mw']*ray['weight']
        for event in ray['events']:
            s=lookup[event['id']]
            entries=event['lens_surfaces'] or [event]
            for entry in entries:
                interface=entry.get('surface',0); key=(source['id'],s.name,event['visit'],interface)
                if key not in groups:
                    outline_surface=copy.copy(s)
                    if s.kind=='lens' and s.e['model']=='prescription' and interface:
                        outline_surface.radius=s.e['surfaces'][interface-1]['clear_diameter_mm']/2
                    bound=max(.01,*[abs(v) for point in s.outline(True) for v in s.local(np.array(point))])*1.06
                    groups[key]=dict(source_id=source['id'],source_name=source['name'],id=s.name,name=s.e['name'],
                                     kind=s.kind,visit=event['visit'],interface=interface,bound_mm=bound,
                                     outline=[list(s.local(np.array(p))) for p in outline_surface.outline()],
                                     blank=[list(s.local(np.array(p))) for p in s.outline(True)],samples=[])
                group=groups[key]; pos=np.array(entry['point']); uv=s.local(pos)
                pin=weight*entry.get('power_before',event['power_before'])
                clipped=entry.get('margin_mm',event['margin_mm'])<0
                pout=0. if clipped else weight*entry.get('power_after',event['power_after'])
                incoming=np.array(entry.get('incoming_direction',event['incoming_direction']))
                efield=unpack(entry.get('jones_before',event['jones_before']))
                u=s.u-incoming*np.dot(s.u,incoming)
                u=unit(u) if np.linalg.norm(u)>1e-10 else frame(incoming)[0]; v=np.cross(incoming,u)
                polar=stokes(efield,incoming,u,v)
                group['samples'].append(dict(uv=list(uv),wavelength_nm=ray['wavelength_nm'],power_mw=pin,
                                             after_power_mw=pout,margin_mm=float(entry.get('margin_mm',event['margin_mm'])),
                                             Q=polar['Q'],U=polar['U'],V=polar['V']))
    result=[]
    for group in groups.values():
        samples=group['samples']; weights=np.array([p['power_mw'] for p in samples]); positions=np.array([p['uv'] for p in samples])
        power=float(weights.sum()); after=float(sum(p['after_power_mw'] for p in samples))
        if power>1e-25:
            mean=np.average(positions,axis=0,weights=weights); cov=((positions-mean).T*weights)@(positions-mean)/power
            polar={key:float(sum(p[key]*p['power_mw'] for p in samples)/power) for key in ('Q','U','V')}
            polar['degree']=float(np.sqrt(sum(v*v for v in polar.values())))
            centroid=mean.tolist(); radius=(2*np.sqrt(np.maximum(np.diag(cov),0))).tolist()
        else: centroid=None; radius=None; polar=dict(Q=0.,U=0.,V=0.,degree=0.)
        bound=group['bound_mm']; hist=np.histogram2d(positions[:,1],positions[:,0],bins=64,range=[[-bound,bound],[-bound,bound]],weights=weights)[0]
        zoom_bound=max(*(radius or [0]),.02)*3; zoom_centre=centroid or [0,0]
        zoom_hist=np.histogram2d(positions[:,1],positions[:,0],bins=96,
            range=[[zoom_centre[1]-zoom_bound,zoom_centre[1]+zoom_bound],[zoom_centre[0]-zoom_bound,zoom_centre[0]+zoom_bound]],weights=weights)[0]
        group.update(incident_power_mw=power,after_power_mw=after,centroid_mm=centroid,equivalent_radius_mm=radius,
                     stokes=polar,ray_hits=len(samples),density_mw_mm2=(hist/(2*bound/64)**2).tolist(),
                     zoom_density_mw_mm2=(zoom_hist/(2*zoom_bound/96)**2).tolist(),zoom_bound_mm=zoom_bound,zoom_center_mm=zoom_centre)
        stride=max(1,math.ceil(len(samples)/2000)); group['samples']=samples[::stride]
        group['sample_stride']=stride; result.append(group)
    return result


def chief(config,source_id,wavelength=None):
    source=next((e for e in config['elements'] if e['id']==source_id and e['type']=='laser' and e['enabled']),None)
    if source is None: raise ValueError('Choose an enabled laser source.')
    surfaces=[WorkSurface(e) for e in config['elements'] if e['enabled'] and e['type']!='laser']
    d,u,v=pose_frame(source); p=np.array([source['x_mm'],source['y_mm'],source['z_mm']])
    return trace(p,d,wavelength or source['wavelength_nm'],surfaces,config,source_jones(source,u,v),source['wavelength_nm'])


def encounter(ray,target_id,visit=1):
    return next((e for e in ray['events'] if e['id']==target_id and e['visit']==visit),None)


def solve_grating(config,source_id,target_id,deviation_deg,visit=1):
    c=checked(config)
    if not isinstance(deviation_deg,(int,float)) or not math.isfinite(deviation_deg) or abs(deviation_deg)>170:
        raise ValueError('Target deviation must be between -170 and +170 degrees.')
    e=next((e for e in c['elements'] if e['id']==target_id and e['type']=='grating' and e['enabled']),None)
    if e is None: raise ValueError('Choose an enabled diffraction grating.')
    ray=chief(c,source_id); event=encounter(ray,target_id,visit)
    if event is None: raise ValueError('The source chief ray must reach this grating before its orientation can be solved.')
    s=WorkSurface(e); incoming=np.array(event['incoming_direction']); g=s.v
    longitudinal=float(np.dot(incoming,g)); transverse=incoming-longitudinal*g
    amplitude=np.linalg.norm(transverse)
    if amplitude<1e-10: raise ValueError('A beam along the grooves has no dispersion-plane deviation.')
    wanted=longitudinal*g+amplitude*rotate(-transverse/amplitude,g,np.deg2rad(deviation_deg))
    difference=wanted-incoming; size=np.linalg.norm(difference)
    shift=e['order']*event['wavelength_nm']*1e-6*e['lines_per_mm']
    if size<1e-10 or abs(shift)>size+1e-10: raise ValueError('No propagating order gives this deviation at the selected wavelength and groove density.')
    direction=unit(difference); ratio=shift/size
    candidates=[]
    for sign in (-1,1):
        tangent=ratio*direction+sign*np.sqrt(max(0,1-ratio*ratio))*np.cross(g,direction)
        normal=unit(np.cross(tangent,g)); outgoing=grating(incoming,normal,g,event['wavelength_nm']*1e-6,e['lines_per_mm'],e['order'])
        if outgoing is not None and np.linalg.norm(outgoing-wanted)<1e-7: candidates.append((float(np.dot(normal,s.normal)),normal,tangent))
    if not candidates: raise ValueError('No reflective solution matches this target. Try the opposite deviation sign.')
    _,normal,tangent=max(candidates,key=lambda p:p[0])
    e.update(pose_from_frame(s.centre,normal,tangent))
    solved=WorkSurface(e); outgoing=grating(incoming,solved.normal,solved.v,event['wavelength_nm']*1e-6,e['lines_per_mm'],e['order'])
    return dict(config=c,angles=grating_angles(solved,incoming,outgoing),outgoing_direction=outgoing.tolist(),
                note='Only the grating orientation was changed. Other optics were held fixed. Check the new route after running.')


def sensitivity(config,source_id,target_id,visit=1,element_id=None,tilt_step_mrad=.02,shift_step_mm=.01):
    c=checked(config)
    if not 1e-5<=tilt_step_mrad<=10 or not 1e-5<=shift_step_mm<=10: raise ValueError('Sensitivity steps must be between 0.00001 and 10.')
    target=next((WorkSurface(e) for e in c['elements'] if e['id']==target_id and e['type']!='laser' and e['enabled']),None)
    if target is None: raise ValueError('Choose an enabled target element.')
    baseline=chief(c,source_id); base_event=encounter(baseline,target_id,visit)
    if base_event is None: raise ValueError('The chief ray does not reach the selected target visit.')
    baseline_route=[(e['id'],e['visit']) for e in baseline['events'][:baseline['events'].index(base_event)+1]]
    rows=[]
    for optic in c['elements']:
        if not optic['enabled'] or (element_id and optic['id']!=element_id): continue
        for axis in ('x_mm','y_mm','z_mm','tilt_u','tilt_v','roll'):
            step=shift_step_mm if axis.endswith('_mm') else tilt_step_mrad; measurements=[]; issues=[]
            for sign in (-1,1):
                perturbed=copy.deepcopy(c); item=next(e for e in perturbed['elements'] if e['id']==optic['id'])
                if axis.endswith('_mm'): item[axis]+=sign*step
                else:
                    normal,u,v=pose_frame(item); around=u if axis=='tilt_u' else v if axis=='tilt_v' else normal
                    angle=sign*step*.001; item.update(pose_from_frame([item['x_mm'],item['y_mm'],item['z_mm']],rotate(normal,around,angle),rotate(u,around,angle)))
                try: ray=chief(perturbed,source_id); event=encounter(ray,target_id,visit)
                except ValueError: event=None
                if event is None: measurements.append(None); issues.append('Target missed in a perturbed trace'); continue
                route=[(e['id'],e['visit']) for e in ray['events'][:ray['events'].index(event)+1]]
                if route!=baseline_route: issues.append('Optical route changed; derivative is not a smooth alignment response')
                position=target.local(np.array(event['point'])); d=np.array(event['incoming_direction']); dn=abs(np.dot(d,target.normal))
                measurements.append(np.array([*position,np.dot(d,target.u)/max(dn,1e-10)*1000,np.dot(d,target.v)/max(dn,1e-10)*1000,event['power_before']*100]))
            derivative=(measurements[1]-measurements[0])/(2*step) if all(x is not None for x in measurements) and not issues else None
            rows.append(dict(id=optic['id'],name=optic['name'],axis=axis,step=step,unit='mm' if axis.endswith('_mm') else 'mrad',
                             du= float(derivative[0]) if derivative is not None else None,dv=float(derivative[1]) if derivative is not None else None,
                             dangle_u=float(derivative[2]) if derivative is not None else None,dangle_v=float(derivative[3]) if derivative is not None else None,
                             dpower_percent=float(derivative[4]) if derivative is not None else None,issue='; '.join(set(issues))))
    return dict(rows=rows,target=target.e['name'],visit=visit,
                note='Chief-ray central differences, in fixed target coordinates. Power is the chief-ray coefficient, not full bundle coupling. Missing or changed routes invalidate the local derivative.')


def convergence(config,source_id,target_id,visit=1,tolerance_percent=1.,levels=3):
    c=checked(config)
    if not .01<=tolerance_percent<=20 or levels not in (2,3,4): raise ValueError('Choose 2–4 levels and a tolerance from 0.01 to 20%.')
    source=next((e for e in c['elements'] if e['id']==source_id and e['type']=='laser' and e['enabled']),None)
    if source is None: raise ValueError('Choose an enabled laser.')
    # Nested spatial/angle samples use separate fixed seeds in the tracer.
    base=max(source['rays'],33); rows=[]; previous=None; consecutive=0
    for level in range(levels):
        cc=copy.deepcopy(c)
        for item in cc['elements']:
            if item['type']=='laser': item['enabled']=item['id']==source_id
        item=next(e for e in cc['elements'] if e['id']==source_id)
        item['wavelength_samples']=min(31,max(source['wavelength_samples'],3)+2*level) if item['bandwidth_nm'] else 1
        item['rays']=min(4096,100000//item['wavelength_samples'],base*(4**level))
        if rows and item['rays']==rows[-1]['rays_per_wavelength'] and item['wavelength_samples']==rows[-1]['wavelength_samples']:
            break  # Repeating capped settings is not a numerical refinement.
        result=simulate(cc); profile=next((p for p in result['footprints'] if p['source_id']==source_id and p['id']==target_id and p['visit']==visit),None)
        if profile is None: raise ValueError('No sampled rays reach this surface visit.')
        power=profile['incident_power_mw']; centroid=profile['centroid_mm']; radii=profile['equivalent_radius_mm']
        values=np.array([power,*(centroid or [0,0]),*(radii or [0,0])])
        errors=None
        if previous is not None:
            scale=max(max(radii or [0]),.01)
            errors=dict(power_percent=float(abs(values[0]-previous[0])/max(abs(values[0]),source['power_mw']*1e-4)*100),
                        centroid_percent_of_radius=float(np.linalg.norm(values[1:3]-previous[1:3])/scale*100),
                        radius_percent=float(np.max(abs(values[3:]-previous[3:]))/scale*100))
            consecutive=consecutive+1 if max(errors.values())<=tolerance_percent else 0
        rows.append(dict(rays_per_wavelength=item['rays'],wavelength_samples=item['wavelength_samples'],total_rays=result['metrics']['sampled_rays'],
                         incident_power_mw=power,centroid_mm=centroid,radius_mm=radii,changes=errors))
        previous=values
    return dict(rows=rows,converged=consecutive>=2,tolerance_percent=tolerance_percent,
                status='Converged over two refinements' if consecutive>=2 else 'Not confirmed — increase sampling or relax tolerance',
                note='Checks surface incident power, centroid and 2σ beam radii. A finite sampling comparison does not certify the physical model. Spatial and spectral sampling both increase.')
