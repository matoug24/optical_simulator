"""Spectral phase and FFT pulse reconstruction along a fixed optical ray family.

Includes geometric/material optical path and the grating's phase ramp; optional
local coherent-field sampling adds spatial filtering, diffraction and Jones phase.
The temporal FFT/FWHM method is reused from the established GVD optics module.
"""
import copy
import numpy as np
from model import checked, WorkSurface, pose_frame, frame
from diagnostics import chief, encounter
from polarization import unpack, source_jones
from optics import fwhm
from waveoptics import compute_field, interpolate

C_MM_FS=.000299792458


def phase_interpolate(x,y,points):
    """Cubic Hermite interpolation of continuous phase, preserving quadratics."""
    slope=np.gradient(y,x,edge_order=2)
    index=np.clip(np.searchsorted(x,points)-1,0,len(x)-2)
    step=x[index+1]-x[index]; t=np.clip((points-x[index])/step,0,1)
    return ((2*t**3-3*t**2+1)*y[index]+(t**3-2*t**2+t)*step*slope[index]
            +(-2*t**3+3*t**2)*y[index+1]+(t**3-t**2)*step*slope[index+1])


def temporal_envelope(spectrum):
    # E(t)=integral S(omega) exp(-i omega t): positive spectral GDD is an up-chirp.
    n=spectrum.shape[-1]
    return np.fft.fftshift(np.fft.fft(np.fft.ifftshift(spectrum,axes=(-1,)),axis=-1),axes=(-1,))/n


def instantaneous_wavelength(envelope,derivative,omega0):
    intensity=np.sum(abs(envelope)**2,axis=0)
    offset=-np.imag(np.sum(np.conjugate(envelope)*derivative,axis=0))/np.maximum(intensity,1e-300)
    omega=omega0+offset
    good=(intensity>max(float(intensity.max())*1e-3,1e-30))&(omega>0)
    return [float(2*np.pi*C_MM_FS/w*1e6) if valid else None for w,valid in zip(omega,good)]


def surface_point(surface,uv,event,after):
    u,v=uv
    if surface.kind=='lens' and surface.e['model']!='thin':
        direction=np.array(event.get('outgoing_direction') if after else event['incoming_direction'])
        forward=np.dot(direction,surface.axis)>0
        last=len(surface.radii)-1
        index=(last if forward else 0) if after else (0 if forward else last)
        radius=surface.radii[index]; rho=u*u+v*v
        if radius and rho>=radius*radius: raise ValueError('Pulse sample point is outside the spherical cap.')
        sag=radius-np.sign(radius)*np.sqrt(radius*radius-rho) if radius else 0.
        return surface.vertices[index]+u*surface.u+v*surface.v+sag*surface.axis
    return surface.centre+u*surface.u+v*surface.v


def pulse_analysis(config,source_id,target_id,visit=1):
    c=checked(config); settings=c['analysis']
    source=next((e for e in c['elements'] if e['id']==source_id and e['type']=='laser' and e['enabled']),None)
    target=next((WorkSurface(e) for e in c['elements'] if e['id']==target_id and e['type']!='laser' and e['enabled']),None)
    if source is None or target is None: raise ValueError('Choose an enabled source and target element.')
    if source['bandwidth_nm']<=0: raise ValueError('Pulse analysis needs a nonzero laser spectral bandwidth.')
    centre=source['wavelength_nm']; omega0=2*np.pi*C_MM_FS/(centre*1e-6)
    sigma=omega0*source['bandwidth_nm']/centre/2.355
    count=settings['pulse_samples']; offsets=np.linspace(-8*sigma,8*sigma,count); omega=omega0+offsets
    wavelengths=2*np.pi*C_MM_FS/omega*1e6
    after=settings.get('pulse_after',True); uv=[settings['pulse_u_mm'],settings['pulse_v_mm']]
    baseline=chief(c,source_id); base=encounter(baseline,target_id,visit)
    if base is None: raise ValueError('The central wavelength does not reach this target visit.')
    if after and base.get('outgoing_direction') is None: raise ValueError('The central wavelength has no outgoing ray at this target; choose the before-interaction pulse.')
    end=baseline['events'].index(base)+1; wanted=[(e['id'],e['visit']) for e in baseline['events'][:end]]
    phase=np.full(count,np.nan); transmission=np.zeros(count); jones=np.zeros((count,3),complex); valid=np.zeros(count,bool)
    warnings=[]; point=surface_point(target,uv,base,after)
    for optic in c['elements']:
        if optic['id'] not in {e['id'] for e in baseline['events'][:end]} or optic.get('model')!='prescription': continue
        models={row['material_after']['model'] for row in optic['surfaces']}
        if 'table' in models: warnings.append('A traversed lens uses a piecewise-linear index table. Its derivative discontinuities can distort GDD/TOD and pulse shape; prefer a smooth manufacturer dispersion formula.')
    if target.margin(point)<0: raise ValueError('The pulse sample point is outside the target clear aperture.')
    for i,wl in enumerate(wavelengths):
        if omega[i]<=0 or not 300<=wl<=2500: continue
        ray=chief(c,source_id,float(wl)); event=encounter(ray,target_id,visit)
        if event is None: continue
        index=ray['events'].index(event)+1
        if [(e['id'],e['visit']) for e in ray['events'][:index]]!=wanted: continue
        if after and (event.get('outgoing_direction') is None or event['power_after']<=0): continue
        direction=np.array(event['outgoing_direction'] if after else event['incoming_direction'])
        hit=np.array(event.get('exit_point',event['point']) if after else event['point'])
        phase[i]=event['phase_after_rad' if after else 'phase_before_rad']+2*np.pi/(wl*1e-6)*float(np.dot(direction,point-hit))
        transmission[i]=event['power_after' if after else 'power_before']
        jones[i]=unpack(event['jones_after' if after else 'jones_before']); valid[i]=True
    delta_lambda=wavelengths-centre
    if source.get('pulse_profile')=='sech2': power=1/np.cosh(np.clip(delta_lambda/source['bandwidth_nm']*(2*np.arccosh(np.sqrt(2))),-100,100))**2
    else: power=np.exp(-4*np.log(2)*(delta_lambda/source['bandwidth_nm'])**2)
    # Convert a density per wavelength to a density per angular frequency.
    power*=omega0**2/np.maximum(omega**2,1e-20); power[omega<=0]=0
    significant=power>power.max()*1e-4
    if np.any(significant&~valid): warnings.append('Some significant wavelengths miss, clip or follow a different route. Their spectral amplitude is set to zero; inspect the Beam Tracker.')
    fit=valid&(abs(offsets)<=2.5*sigma)&(power>power.max()*1e-6)
    if fit.sum()<8: raise ValueError('Too few wavelengths reach the same target route for a reliable spectral-phase fit.')
    x=offsets/sigma; reference=phase[np.argmin(abs(offsets))]
    coefficients=np.polynomial.polynomial.polyfit(x[fit],phase[fit]-reference,5,w=np.sqrt(power[fit]))
    optical_gdd=float(2*coefficients[2]/sigma**2); optical_tod=float(6*coefficients[3]/sigma**3)
    delay=float(coefficients[1]/sigma)
    # Analytic eikonal phase is continuous: do not wrap it before interpolation.
    phase[valid]-=reference+coefficients[0]+coefficients[1]*x[valid]
    phase[~valid]=np.interp(x[~valid],x[valid],phase[valid])
    source_gdd=source.get('source_gdd_fs2',0); source_tod=source.get('source_tod_fs3',0)
    extra_gdd=source_gdd+settings['extra_gdd_fs2']+settings['fibre_length_m']*settings['fibre_beta2_fs2_m']
    extra_tod=source_tod+settings['extra_tod_fs3']+settings['fibre_length_m']*settings['fibre_beta3_fs3_m']
    transfer=jones*np.sqrt(transmission[:,None])
    local_field=settings['pulse_use_field']; field_nodes=0
    if local_field:
        # Refine the spatial spectral response with the pulse sampling control,
        # and retain the full spectral window for non-Gaussian spectral tails.
        field_nodes=(count+1)//2
        nodes=np.linspace(-8*sigma,8*sigma,field_nodes); samples=np.zeros((len(nodes),3),complex)
        for j,offset in enumerate(nodes):
            wl=2*np.pi*C_MM_FS/(omega0+offset)*1e6
            try:
                node_ray=chief(c,source_id,float(wl)); node_hit=encounter(node_ray,target_id,visit)
                if node_hit is None: continue
                node_end=node_ray['events'].index(node_hit)+1
                if [(e['id'],e['visit']) for e in node_ray['events'][:node_end]]!=wanted: continue
                field=compute_field(c,source_id,target_id,visit,wavelength=float(wl),grid=settings['field_grid'],after=after,return_arrays=True)
                displacement=point-field['_point']; xx=np.dot(displacement,field['_basis'][0]); yy=np.dot(displacement,field['_basis'][1])
                value=interpolate(field['_field'],np.array(xx),np.array(yy),field['span_mm'])
                reference_amplitude=np.sqrt(2*source['power_mw']/(np.pi*source['beam_radius_mm']**2))
                samples[j]=(value[0]*field['_basis'][0]+value[1]*field['_basis'][1])/reference_amplitude
                if field['warnings']: warnings.extend(field['warnings'])
            except ValueError: pass
        for k in range(3): transfer[:,k]=np.interp(offsets,nodes,samples[:,k].real,left=0,right=0)+1j*np.interp(offsets,nodes,samples[:,k].imag,left=0,right=0)
        transfer[~valid]=0
        local_spectrum=np.sum(abs(samples)**2,axis=1)*np.interp(nodes,offsets,power)
        if local_spectrum.max()>0 and np.count_nonzero(local_spectrum>=local_spectrum.max()/2)<6:
            warnings.append('Local spectral response has fewer than six envelope samples across its half-maximum region. Pulse width and shape may be undersampled; increase spectral samples and check pulse convergence.')
    elif np.linalg.norm(np.array(base['uv'])-uv)>source['beam_radius_mm']:
        warnings.append('Chief-family mode phase is evaluated at the selected surface point. Enable local coherent-field sampling to include spatial spectral filtering there.')
    derivative=np.gradient(phase,offsets)+extra_gdd*offsets+extra_tod*offsets**2/2
    # Zero-pad the spectral domain to resolve temporal FWHM, not just time extent.
    maximum=32*sigma
    source_delay=source_gdd*offsets+source_tod*offsets**2/2
    extent=max(4096*np.pi/maximum,4*float(np.max(abs(derivative[significant]))),4*float(np.max(abs(source_delay[significant]))))+200/sigma
    required=max(4096,int(extent*maximum/np.pi)); n=2**int(np.ceil(np.log2(required)))
    if n>262144: warnings.append('Temporal FFT is capped; extreme dispersion can wrap the pulse.'); n=262144
    frequency=(np.arange(n)-n//2)*(2*maximum/n)
    amplitude=np.sqrt(np.interp(frequency,offsets,power,left=0,right=0))
    phase_fine=phase_interpolate(offsets,phase,frequency)+extra_gdd*frequency**2/2+extra_tod*frequency**3/6
    spectral=np.array([amplitude*(np.interp(frequency,offsets,transfer[:,k].real)+1j*np.interp(frequency,offsets,transfer[:,k].imag))*np.exp(1j*phase_fine) for k in range(3)])
    source_spectral=amplitude*np.exp(1j*(source_gdd*frequency**2/2+source_tod*frequency**3/6))
    source_temporal=temporal_envelope(source_spectral)
    temporal=temporal_envelope(spectral); reference_temporal=temporal_envelope(amplitude)
    intensity=np.sum(abs(temporal)**2,axis=0); reference_intensity=abs(reference_temporal)**2; input_intensity=abs(source_temporal)**2
    dt=np.pi/maximum; time=(np.arange(n)-n//2)*dt; normalizer=max(float(reference_intensity.max()),1e-300)
    if intensity.max()>0 and max(float(intensity[0]),float(intensity[-1]))>intensity.max()*1e-5: warnings.append('Pulse reaches the FFT time boundary; the result can be aliased.')
    if max(float(input_intensity[0]),float(input_intensity[-1]))>input_intensity.max()*1e-5: warnings.append('Source pulse reaches the FFT time boundary; reduce source dispersion or bandwidth.')
    if not intensity.max()>0: warnings.append('No transmitted spectral power reaches this pulse target.')
    active=np.where(intensity>intensity.max()*1e-4)[0] if intensity.max()>0 else np.array([],int)
    source_active=np.where(input_intensity>input_intensity.max()*1e-4)[0]
    halfwidth=max(4/sigma,abs(float(time[active[0]]))*1.1 if active.size else 0,abs(float(time[active[-1]]))*1.1 if active.size else 0,abs(float(time[source_active[0]]))*1.1,abs(float(time[source_active[-1]]))*1.1)
    indices=np.where(abs(time)<=halfwidth)[0]; stride=max(1,len(indices)//1800); indices=indices[::stride]
    spectral_strength=np.sum(abs(transfer)**2,axis=1)
    target_direction=np.array(base['outgoing_direction'] if after else base['incoming_direction']); target_basis=frame(target_direction)
    components=np.array([np.dot(axis,temporal) for axis in target_basis]); dominant=int(np.argmax(np.sum(abs(components)**2,axis=1)))
    output_component=components[dominant]/np.sqrt(normalizer)
    _,source_u,source_v=pose_frame(source); input_jones=source_jones(source,source_u,source_v)
    input_axes=[np.dot(input_jones,axis) for axis in (source_u,source_v)]
    input_component=source_temporal*max(input_axes,key=abs)/np.sqrt(normalizer)
    output_derivative=temporal_envelope(-1j*frequency*spectral)
    source_derivative=temporal_envelope(-1j*frequency*source_spectral)
    input_wavelength=instantaneous_wavelength(source_temporal[None,:],source_derivative[None,:],omega0)
    output_wavelength=instantaneous_wavelength(temporal,output_derivative,omega0)
    # Keep the carrier envelope at native FFT resolution, even when the broad
    # intensity plot is decimated. Carrier oscillations are synthesized separately.
    peak_time=float(time[np.argmax(intensity)])
    carrier_indices=np.where(abs(time-peak_time)<=max(300,3*dt))[0]
    return dict(source_id=source_id,target_id=target_id,visit=visit,after=after,local_field=local_field,
                field_grid_used=settings['field_grid'] if local_field else None,field_envelope_samples=field_nodes,
                model_notes=[f"Local field transfer uses {field_nodes} envelope wavelengths and the selected {settings['field_grid']} field grid. Check field-grid convergence separately; higher-order lens wave aberrations are omitted."] if local_field else [],
                optical_gdd_fs2=optical_gdd,optical_tod_fs3=optical_tod,added_gdd_fs2=extra_gdd,added_tod_fs3=extra_tod,
                net_gdd_fs2=optical_gdd+extra_gdd,net_tod_fs3=optical_tod+extra_tod,group_delay_fs=delay,
                reference_fwhm_fs=fwhm(time,reference_intensity),input_fwhm_fs=fwhm(time,input_intensity),output_fwhm_fs=fwhm(time,intensity),
                source_gdd_fs2=source_gdd,source_tod_fs3=source_tod,carrier_wavelength_nm=centre,carrier_period_fs=centre*1e-6/C_MM_FS,output_peak_time_fs=peak_time,
                energy_ratio=float(np.sum(abs(spectral)**2)/max(np.sum(amplitude**2),1e-300)),relative_peak=float(intensity.max()/normalizer),
                time_fs=time[indices].tolist(),input_intensity=(input_intensity[indices]/normalizer).tolist(),reference_intensity=(reference_intensity[indices]/normalizer).tolist(),
                output_intensity=(intensity[indices]/normalizer).tolist(),wavelength_nm=wavelengths.tolist(),
                input_instantaneous_wavelength_nm=[input_wavelength[i] for i in indices],output_instantaneous_wavelength_nm=[output_wavelength[i] for i in indices],
                carrier_envelope_time_fs=time[carrier_indices].tolist(),input_envelope_real=input_component[carrier_indices].real.tolist(),input_envelope_imag=input_component[carrier_indices].imag.tolist(),output_envelope_real=output_component[carrier_indices].real.tolist(),output_envelope_imag=output_component[carrier_indices].imag.tolist(),
                spectral_transmission=spectral_strength.tolist(),spectral_phase_rad=phase.tolist(),source_spectral_phase_rad=(source_gdd*offsets**2/2+source_tod*offsets**3/6).tolist(),net_spectral_phase_rad=(phase+extra_gdd*offsets**2/2+extra_tod*offsets**3/6).tolist(),fft_points=n,spectral_samples=count,
                warnings=list(dict.fromkeys(warnings)),
                method='Continuous geometric/material eikonal plus grating phase ramps, evaluated at a fixed surface point; third-order coefficients are fitted near the source frequency. Source/coating/user/fibre dispersion are included. Jones components are Fourier transformed separately. Local scalar-field transfer is optional; otherwise this is a chief-ray-family temporal mode, not a spatially resolved pulse-front calculation.')


def pulse_convergence(config,source_id,target_id,visit=1):
    c=checked(config); n=min(c['analysis']['pulse_samples'],257); rows=[]
    for count in (n,2*n-1):
        cc=copy.deepcopy(c); cc['analysis']['pulse_samples']=count
        r=pulse_analysis(cc,source_id,target_id,visit)
        rows.append(dict(samples=count,output_fwhm_fs=r['output_fwhm_fs'],net_gdd_fs2=r['net_gdd_fs2'],energy_ratio=r['energy_ratio'],warnings=r['warnings']))
    a,b=rows; valid=all(r['output_fwhm_fs'] is not None for r in rows)
    change=abs(b['output_fwhm_fs']-a['output_fwhm_fs'])/max(b['output_fwhm_fs'],1e-10)*100 if valid else None
    return dict(rows=rows,width_change_percent=change,converged=valid and change<1 and not any(r['warnings'] for r in rows),
                note='Spectral phase refinement, with an adaptive temporal FFT. Field-grid errors need the separate physical-optics convergence check.')
