"""Chief-path scalar angular-spectrum propagation with two Jones components.

Planar optics use oblique-pupil remapping, including grating anamorphism.
Doublets use a wavelength-dependent first-order ABCD equivalent measured with
the exact Snell solver. This is a paraxial field model, not a vector Maxwell solver.
"""
import copy
import numpy as np
from model import checked, WorkSurface, pose_frame, frame, unit
from diagnostics import chief, encounter
from polarization import source_jones, element_transfer, transported, fresnel_transmit


def interpolate(array,x,y,span):
    n=array.shape[-1]; dx=span/n
    ix=x/dx+n//2; iy=y/dx+n//2; i=np.floor(ix).astype(int); j=np.floor(iy).astype(int)
    valid=(i>=0)&(i<n-1)&(j>=0)&(j<n-1); ii=np.clip(i,0,n-2); jj=np.clip(j,0,n-2)
    a=ix-i; b=iy-j
    return ((1-a)*(1-b)*array[...,jj,ii]+a*(1-b)*array[...,jj,ii+1]+(1-a)*b*array[...,jj+1,ii]+a*b*array[...,jj+1,ii+1])*valid


def angular_spectrum(field,wavelength_mm,distance_mm,span_mm):
    if abs(distance_mm)<1e-12: return field.copy(),0.
    n=field.shape[-1]; dx=span_mm/n; pad=n//2
    extended=np.pad(field,((0,0),(pad,pad),(pad,pad)))
    frequency=np.fft.fftfreq(2*n,d=dx); fx,fy=np.meshgrid(frequency,frequency)
    valid=fx*fx+fy*fy<1/wavelength_mm**2
    kz=np.sqrt(np.maximum(1/wavelength_mm**2-fx*fx-fy*fy,0))
    # Padded, band-limited propagation suppresses periodic wrap-around aliases.
    limit=(2*span_mm)/(wavelength_mm*np.sqrt((2*span_mm)**2+4*distance_mm**2))
    valid&=(abs(fx)<=limit)&(abs(fy)<=limit)
    transfer=np.exp(2j*np.pi*distance_mm*(kz-1/wavelength_mm))*valid
    spectrum=np.fft.fft2(extended,axes=(-2,-1)); before=float(np.sum(abs(spectrum)**2))
    rejected=float(np.sum(abs(spectrum[...,~valid])**2))/max(before,1e-300)
    propagated=np.fft.ifft2(spectrum*transfer,axes=(-2,-1))
    return propagated[:,pad:pad+n,pad:pad+n],rejected


def lens_abcd(e,wavelength):
    if e['model']=='thin': return dict(A=1.,B=0.,C=-1/e['focal_length_mm'],D=1.,focal_length_mm=e['focal_length_mm'],before_mm=0.,after_mm=0.)
    sample=copy.deepcopy(e); sample.update(x_mm=0.,y_mm=0.,z_mm=0.,azimuth_deg=0.,elevation_deg=0.,roll_deg=0.)
    lens=WorkSurface(sample); half=float(np.linalg.norm(lens.vertices[-1]-lens.vertices[0]))/2
    h=1e-3; angle=1e-5; responses=[]
    for position,slope in ((h,0.),(0.,angle)):
        direction=unit([1.,slope,0]); point=np.array([-half-2,position-2*slope,0.])
        found=lens.intersect(point,direction)
        if found is None: raise ValueError('Cannot determine a near-axis lens matrix.')
        q,d,_,failure=lens.advance_lens(found[0],direction,wavelength)
        if failure: raise ValueError('Cannot determine lens matrix: '+failure)
        q=q+d*((half-q[0])/d[0]); responses.append((q[1],d[1]/d[0]))
    A,C=responses[0][0]/h,responses[0][1]/h; B,D=responses[1][0]/angle,responses[1][1]/angle
    if abs(A*D-B*C-1)>1e-4: raise ValueError('Lens first-order matrix failed its optical invariant check.')
    if abs(C)<1e-10: raise ValueError('The selected doublet has negligible optical power; use a supported thin-lens model.')
    return dict(A=float(A),B=float(B),C=float(C),D=float(D),focal_length_mm=float(-1/C),
                before_mm=float((D-1)/C),after_mm=float((A-1)/C))


def aperture(surface,uv0,uv1,blank=False):
    if surface.half:
        half=surface.body_half if blank else surface.half
        return (abs(uv0)<=half[0])&(abs(uv1)<=half[1])
    mask=uv0*uv0+uv1*uv1<=(surface.blank_radius if blank else surface.radius)**2
    if surface.upper is not None: mask&=uv1<=surface.upper
    return mask


def event_operator(surface,event,wavelength,inbasis,outbasis):
    incoming=np.array(event['incoming_direction']); outgoing=np.array(event.get('outgoing_direction') or event['incoming_direction'])
    coefficient=surface.e.get('efficiency',surface.e.get('reflectance',surface.e.get('transmission',1)))
    result=np.zeros((2,2),complex)
    for i,basis in enumerate(inbasis):
        field=basis.astype(complex)
        if surface.kind=='lens':
            if event['lens_surfaces']:
                for h in event['lens_surfaces']:
                    before=np.array(h['incoming_direction']); after=np.array(h['outgoing_direction']); normal=np.array(h['normal'])
                    field=fresnel_transmit(field,before,after,normal,h['n_before'],h['n_after']) if surface.e.get('bare_fresnel') else transported(field,before,after)
            else: field=transported(field,incoming,outgoing)
            field=element_transfer(surface.e,outgoing,outgoing,surface.normal,field,wavelength,surface.u,surface.v)
        else: field=element_transfer(surface.e,incoming,outgoing,surface.normal,field,wavelength,surface.u,surface.v)
        for j,axis in enumerate(outbasis): result[j,i]=np.dot(field,axis)*np.sqrt(coefficient)
    return result


def compute_field(config,source_id,target_id,visit=1,wavelength=None,grid=None,span=None,after=None,return_arrays=False):
    c=checked(config); settings=c['analysis']; n=grid or settings['field_grid']; width=span or settings['field_span_mm']
    if n not in (64,128,256,512) or not .01<=width<=1000: raise ValueError('Invalid field grid or span.')
    source=next((e for e in c['elements'] if e['id']==source_id and e['type']=='laser' and e['enabled']),None)
    if source is None: raise ValueError('Choose an enabled laser.')
    wl=wavelength or settings['field_wavelength_nm']; lam=wl*1e-6
    if not 300<=wl<=2500: raise ValueError('Field wavelength must be between 300 and 2500 nm.')
    after=settings['field_after'] if after is None else after
    ray=chief(c,source_id,wl); destination=encounter(ray,target_id,visit)
    if destination is None: raise ValueError('The chief ray does not reach the selected target at this wavelength.')
    surfaces={e['id']:WorkSurface(e) for e in c['elements'] if e['enabled'] and e['type']!='laser'}
    d,u,v=pose_frame(source); basis=(u,v); previous=np.array([source['x_mm'],source['y_mm'],source['z_mm']])
    coordinate=(np.arange(n)-n//2)*width/n; X,Y=np.meshgrid(coordinate,coordinate); dx=width/n
    envelope=np.exp(-(X*X+Y*Y)/source['beam_radius_mm']**2).astype(complex)
    curvature=source.get('wavefront_radius_mm',0)
    if curvature: envelope*=np.exp(1j*np.pi/(lam*curvature)*(X*X+Y*Y))
    polarization=source_jones(source,u,v)
    field=np.array([np.dot(polarization,axis)*envelope for axis in basis])
    initial=float(np.sum(abs(field)**2)*dx**2)
    field*=np.sqrt(source['power_mw']/max(initial,1e-300))
    warnings=[]; model_notes=[]; stages=[]; matrices=[]; target_surface=None; target_point=None
    if any(e.get('model')=='prescription' for e in c['elements'] if e['enabled']):
        model_notes.append('Surface prescriptions use their exact near-axis Snell matrix in this first-order field model. Individual internal stops and higher-order aberrations are resolved by geometric rays; this field calculation applies the common entrance pupil.')
    if source.get('divergence_mrad',0): model_notes.append('Coherent field uses Gaussian diffraction and the supplied wavefront curvature. Independently sampled ray-angle jitter is not added to this coherent mode.')
    if source['beam_radius_mm']<3*dx: warnings.append('Source radius is sampled by fewer than three pixels. Increase grid resolution or reduce span.')
    for event in ray['events']:
        surface=surfaces[event['id']]; hit=np.array(event['point']); distance=float(np.linalg.norm(hit-previous))
        field,rejected=angular_spectrum(field,lam,distance,width)
        if rejected>1e-3: warnings.append('Spatial frequencies were removed by the propagation sampling limit; increase field span/grid and check convergence.')
        target_surface=surface; target_point=hit; d=np.array(event['incoming_direction'])
        den=float(np.dot(d,surface.normal))
        if abs(den)<.03: raise ValueError('The field projection is too close to grazing incidence for this scalar pupil model.')
        off=X[...,None]*basis[0]+Y[...,None]*basis[1]
        physical=off-d*(off@surface.normal)[...,None]/den
        offset=hit-surface.centre
        uu=physical@surface.u+np.dot(offset,surface.u); vv=physical@surface.v+np.dot(offset,surface.v)
        clear=aperture(surface,uu,vv); before_power=float(np.sum(abs(field)**2)*dx**2)
        clear_power=float(np.sum(abs(field[:,clear])**2)*dx**2)
        stages.append(dict(id=surface.name,name=surface.e['name'],visit=event['visit'],distance_mm=distance,
                           incident_power_mw=before_power,clear_power_mw=clear_power))
        if event is destination and not after: break
        if event.get('outgoing_direction') is None: raise ValueError('This interaction has no outgoing chief ray; an after-surface field is unavailable.')
        field*=clear
        outgoing=np.array(event['outgoing_direction']); outbasis=frame(outgoing)
        if surface.kind=='lens':
            prescription=copy.deepcopy(surface.e)
            if np.dot(d,surface.normal)<0: prescription['flipped']=not prescription['flipped']
            matrix=lens_abcd(prescription,wl); matrices.append(dict(id=surface.name,**matrix))
            if abs(np.dot(d,surface.normal))<np.cos(np.deg2rad(5)): warnings.append('Lens chief incidence exceeds 5°. The first-order equivalent field lens can omit off-axis aberrations; exact rays remain available separately.')
            field,rejected=angular_spectrum(field,lam,matrix['before_mm'],width)
            if rejected>1e-3: warnings.append('Lens principal-plane propagation is undersampled.')
            phase=-np.pi/(lam*matrix['focal_length_mm'])*(X*X+Y*Y)
            illuminated=np.sum(abs(field)**2,axis=0)>np.max(np.sum(abs(field)**2,axis=0))*1e-4
            gradients=np.gradient(phase)
            slope=max(float(np.max(abs(g[illuminated]))) for g in gradients) if np.any(illuminated) else 0
            if slope>np.pi: warnings.append('Equivalent lens phase changes by more than π per illuminated pixel. Increase the grid or reduce the field span.')
            field*=np.exp(1j*phase)
            field,rejected=angular_spectrum(field,lam,matrix['after_mm'],width)
        # Map the field between chief-normal planes through the physical pupil.
        outoff=X[...,None]*outbasis[0]+Y[...,None]*outbasis[1]
        denout=float(np.dot(outgoing,surface.normal))
        if abs(denout)<.03: raise ValueError('Outgoing field is too close to grazing incidence.')
        at_surface=outoff-outgoing*(outoff@surface.normal)[...,None]/denout
        xin=at_surface@basis[0]; yin=at_surface@basis[1]
        colx=outbasis[0]-outgoing*np.dot(outbasis[0],surface.normal)/denout
        coly=outbasis[1]-outgoing*np.dot(outbasis[1],surface.normal)/denout
        mapping=np.array([[np.dot(colx,basis[0]),np.dot(coly,basis[0])],[np.dot(colx,basis[1]),np.dot(coly,basis[1])]])
        field=interpolate(field,xin,yin,width)*np.sqrt(abs(np.linalg.det(mapping)))
        operator=event_operator(surface,event,wl,basis,outbasis); field=np.einsum('ij,jyx->iyx',operator,field)
        basis=outbasis; d=outgoing; previous=np.array(event.get('exit_point',event['point'])); target_point=previous
        stages[-1]['after_power_mw']=float(np.sum(abs(field)**2)*dx**2)
        if event is destination: break
    intensity=np.sum(abs(field)**2,axis=0); power=float(intensity.sum()*dx**2)
    edge=np.zeros((n,n),bool); edge[:3]=True; edge[-3:]=True; edge[:,:3]=True; edge[:,-3:]=True
    edge_fraction=float(intensity[edge].sum()/max(intensity.sum(),1e-300))
    if edge_fraction>1e-3: warnings.append('More than 0.1% of the field power reaches the numerical window edge. Increase span and grid together.')
    if power>source['power_mw']*1.01: warnings.append('Numerical power exceeds source power. Check remapping and grid convergence.')
    if power>1e-25:
        mean=np.array([(intensity*X).sum(),(intensity*Y).sum()])/intensity.sum()
        radii=2*np.sqrt(np.array([(intensity*(X-mean[0])**2).sum(),(intensity*(Y-mean[1])**2).sum()])/intensity.sum())
        if min(radii)<4*dx: warnings.append('The beam radius is below four pixels. Focal size and peak intensity need a finer field grid.')
    else: mean=np.zeros(2); radii=np.zeros(2)
    # Surface-local image. Flux density includes the cosine projection factor.
    origin=target_surface.centre+target_surface.normal*np.dot(target_point-target_surface.centre,target_surface.normal)
    surface_off=origin-target_point+X[...,None]*target_surface.u+Y[...,None]*target_surface.v
    sx=surface_off@basis[0]; sy=surface_off@basis[1]
    surface_field=interpolate(field,sx,sy,width); surface_intensity=np.sum(abs(surface_field)**2,axis=0)*abs(np.dot(d,target_surface.normal))
    dominant=0 if np.sum(abs(surface_field[0])**2)>=np.sum(abs(surface_field[1])**2) else 1
    phase=np.angle(surface_field[dominant])
    # Report Stokes in the field's transverse basis, normalized by integrated power.
    a,b=field; norm=max(float(intensity.sum()),1e-300); product=np.sum(a*np.conjugate(b))
    polar=dict(Q=float((np.sum(abs(a)**2)-np.sum(abs(b)**2))/norm),U=float(2*product.real/norm),V=float(-2*product.imag/norm))
    stride=max(1,n//128)
    result=dict(source_id=source_id,target_id=target_id,visit=visit,wavelength_nm=wl,grid=n,span_mm=width,pixel_mm=dx,
                power_mw=power,clear_power_mw=stages[-1]['clear_power_mw'],centroid_mm=mean.tolist(),radius_mm=radii.tolist(),
                edge_power_fraction=edge_fraction,stokes=polar,stages=stages,lens_matrices=matrices,
                intensity_mw_mm2=surface_intensity[::stride,::stride].tolist(),phase_rad=phase[::stride,::stride].tolist(),
                outline=[list(target_surface.local(np.array(p))) for p in target_surface.outline()],
                warnings=list(dict.fromkeys(warnings)),model_notes=model_notes,after=after,
                method='Two Jones components; padded, band-limited scalar angular spectrum along the selected chief route. Planar pupils are remapped at incidence/diffraction angles. Doublets use wavelength-dependent first-order ABCD equivalents; higher-order lens aberrations and rigorous groove efficiency are not included.')
    if return_arrays: result.update(_field=field,_basis=basis,_point=target_point,_direction=d,_surface=target_surface)
    return result


def field_convergence(config,source_id,target_id,visit=1):
    c=checked(config); base=min(c['analysis']['field_grid'],256); rows=[]; last=None
    for n in (base,base*2):
        value=compute_field(c,source_id,target_id,visit,grid=n); changes=None
        if last:
            changes=dict(power_percent=abs(value['power_mw']-last['power_mw'])/max(value['power_mw'],1e-25)*100,
                         radius_percent=float(np.max(abs(np.array(value['radius_mm'])-last['radius_mm'])/np.maximum(value['radius_mm'],1e-5))*100))
        rows.append(dict(grid=n,power_mw=value['power_mw'],radius_mm=value['radius_mm'],changes=changes,warnings=value['warnings'])); last=value
    clean=not any(r['warnings'] for r in rows)
    return dict(rows=rows,converged=clean and max(rows[-1]['changes'].values())<1,
                note='Fixed-span grid refinement; stability below 1% is accepted only when sampling warnings are absent. Repeat with a larger span to test window truncation.')
