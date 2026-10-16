"""Free-placement, nearest-hit 3D optics. All internal lengths are millimetres.

Reuses the established GVD vector laws and exact spherical/Snell primitives.
No prescribed component sequence or automatic realignment is used.
"""
from __future__ import annotations
import copy
import math
import numpy as np
from materials import material_index
from prescriptions import validate_surfaces

from optics import Surface, pose_frame, pose_from_frame, reflection, lens_direction, unit, frame, rotate
from doublet import spherical_hit, refract, glass_index

POSE = dict(x_mm=150., y_mm=75., z_mm=20., azimuth_deg=0., elevation_deg=0., roll_deg=0.)
CATALOG = {
    'laser': dict(name='Laser source', wavelength_nm=800., bandwidth_nm=0., power_mw=10.,
                  beam_radius_mm=.45, divergence_mrad=0., rays=33, wavelength_samples=3),
    'mirror_b': dict(name='B · round mirror', diameter_mm=16., clear_diameter_mm=16., reflectance=.99),
    'mirror_c': dict(name='C · cut-edge mirror', diameter_mm=10., clear_diameter_mm=10.,
                     upper_edge_mm=1.8, reflectance=.99),
    'mirror_e': dict(name='E · end mirror', diameter_mm=28., clear_diameter_mm=28., reflectance=.99),
    'grating': dict(name='D · diffraction grating', width_mm=30., height_mm=30.,
                    clear_width_mm=27., clear_height_mm=27., lines_per_mm=1400., order=-1,
                    efficiency=.90),
    'lens': dict(name='L · achromatic lens', model='doublet', diameter_mm=25., clear_diameter_mm=24.,
                 focal_length_mm=75., transmission=.995, flipped=False, r1_mm=43.96,
                 r2_mm=-42.90, r3_mm=-392.21, t1_mm=6., t2_mm=4.,
                 glass1='N-LAK22', glass2='N-SF6', n1=1.65, n2=1.80, surfaces=[]),
}

from polarization import source_jones, pack, unpack, transported, element_transfer, fresnel_transmit, stokes


def grating(direction,normal,grooves,wavelength_mm,lines_per_mm,order):
    """Established vector grating law, with roundoff-safe grazing-order cutoff."""
    n,g=unit(normal),unit(grooves); tangent=unit(np.cross(g,n))
    qg=float(np.dot(direction,g)); qt=float(np.dot(direction,tangent))+order*wavelength_mm*lines_per_mm
    qn2=1-qg*qg-qt*qt
    if qn2 < -1e-12: return None
    sign=-1 if np.dot(direction,n)>0 else 1
    return unit(qg*g+qt*tangent+sign*np.sqrt(max(0,qn2))*n)

CATALOG['polarizer']=dict(name='Linear polarizer',diameter_mm=25.,clear_diameter_mm=22.,transmission=.98,axis_deg=0.,extinction_db=30.)
CATALOG['waveplate']=dict(name='Waveplate',diameter_mm=25.,clear_diameter_mm=22.,transmission=.995,axis_deg=0.,retardance_deg=90.,reference_wavelength_nm=780.,retardance_model='inverse_wavelength')
CATALOG['laser'].update(wavefront_radius_mm=0.,polarization_angle_deg=0.,ellipticity_deg=0.,source_gdd_fs2=0.,source_tod_fs3=0.,pulse_profile='gaussian')
for _kind,_values in CATALOG.items():
    if _kind!='laser':
        _values.update(polarization_model='scalar',s_factor=1.,p_factor=1.,s_phase_deg=0.,p_phase_deg=0.,coating_gdd_fs2=0.,coating_tod_fs3=0.)
CATALOG['lens']['bare_fresnel']=False


def analysis_defaults():
    return dict(field_grid=256,field_span_mm=4.,field_wavelength_nm=780.,field_after=False,
                pulse_samples=129,pulse_use_field=False,pulse_after=True,pulse_u_mm=0.,pulse_v_mm=0.,
                extra_gdd_fs2=0.,extra_tod_fs3=0.,fibre_length_m=0.,fibre_beta2_fs2_m=0.,fibre_beta3_fs3_m=0.)


def element(kind, ident, **changes):
    e=dict(id=ident, type=kind, enabled=True, **POSE, **copy.deepcopy(CATALOG[kind]))
    e.update(changes)
    return e


def default_config():
    return dict(format='optics-workbench-v1', name='Untitled optical bench',
                bench=dict(width_mm=300., depth_mm=150., height_mm=100.), max_interactions=48, elements=[])


def folded_config():
    elements = [element('laser', 'laser-1'), element('mirror_b', 'mirror-b-1'),
                element('mirror_c', 'mirror-c-1'), element('lens', 'lens-1'), element('mirror_e', 'mirror-e-1')]
    poses = [(20,35,0),(100,35,-45),(100,105,135),(200,105,0),(250,105,45)]
    for e,(x,y,az) in zip(elements,poses):
        e.update(x_mm=x, y_mm=y, azimuth_deg=az)
    return dict(format='optics-workbench-v1', name='Folded beam example',
                bench=dict(width_mm=300., depth_mm=150., height_mm=100.), max_interactions=48, elements=elements)


def analysis_config():
    """Explicit opt-in demonstration; startup remains empty."""
    c=default_config(); c['name']='780 nm analysis example'
    source=element('laser','laser-demo',x_mm=20,y_mm=40,wavelength_nm=780,bandwidth_nm=5,
                   power_mw=150,beam_radius_mm=.5,divergence_mrad=.5,rays=129,wavelength_samples=7,
                   name='780 nm reference source')
    g=element('grating','grating-demo',x_mm=260,y_mm=40,azimuth_deg=-45)
    c['elements']=[source,g]
    from diagnostics import solve_grating
    c=solve_grating(c,source['id'],g['id'],-11)['config']
    g=c['elements'][1]; surface=WorkSurface(g)
    direction=grating(np.array([1.,0,0]),surface.normal,surface.v,.000780,g['lines_per_mm'],g['order'])
    az=float(np.rad2deg(np.arctan2(direction[1],direction[0])))
    for kind,ident,distance,props in [('lens','lens-demo',100,{}),('waveplate','waveplate-demo',140,{'axis_deg':45.})]:
        pos=surface.centre+distance*direction
        c['elements'].append(element(kind,ident,x_mm=float(pos[0]),y_mm=float(pos[1]),azimuth_deg=az,**props))
    pos=surface.centre+180*direction; normal=unit(direction-np.array([0.,1,0]))
    c['elements'].append(element('mirror_e','mirror-demo',x_mm=float(pos[0]),y_mm=float(pos[1]),
                                 azimuth_deg=float(np.rad2deg(np.arctan2(normal[1],normal[0])))))
    return checked(c)


def spectral_focus_config():
    c=analysis_config(); c['name']='Spectral crossing and chirped pulse example'
    source,g,lens,_,mirror=c['elements']; source.update(y_mm=25.,bandwidth_nm=10.,source_gdd_fs2=20000.,name='780 nm / 10 nm illustrative source')
    g.update(x_mm=275.,y_mm=25.)
    surface=WorkSurface(g); direction=grating(np.array([1.,0,0]),surface.normal,surface.v,.000780,g['lines_per_mm'],g['order'])
    for optic,distance in ((lens,150),(mirror,230)):
        position=surface.centre+distance*direction; optic.update(x_mm=float(position[0]),y_mm=float(position[1]))
    c['elements']=[source,g,lens,mirror]
    return checked(c)


def checked(config):
    if not isinstance(config,dict) or config.get('format') != 'optics-workbench-v1':
        raise ValueError('Load an Optics Workbench JSON file (optics-workbench-v1).')
    c=copy.deepcopy(config)
    if not isinstance(c.get('name'),str) or len(c['name'])>100: raise ValueError('Use a layout name up to 100 characters.')
    def num(obj,key,low,high,integer=False):
        value=obj.get(key)
        if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value):
            raise ValueError(f'{key} must be a finite number.')
        if not low <= value <= high or (integer and int(value)!=value):
            raise ValueError(f'{key} must be between {low} and {high}'+(' and an integer.' if integer else '.'))
    if not isinstance(c.get('bench'),dict): raise ValueError('Bench dimensions are missing.')
    for k in ('width_mm','depth_mm','height_mm'): num(c['bench'],k,10,5000)
    num(c,'max_interactions',1,128,True)
    if not isinstance(c.get('elements'),list) or len(c['elements'])>60: raise ValueError('Use at most 60 elements.')
    c['analysis']={**analysis_defaults(),**c.get('analysis',{})}
    settings=c['analysis']
    for key,lo,hi in [('field_span_mm',.01,1000),('field_wavelength_nm',300,2500),('extra_gdd_fs2',-1e9,1e9),('extra_tod_fs3',-1e12,1e12),('fibre_length_m',0,10000),('fibre_beta2_fs2_m',-1e9,1e9),('fibre_beta3_fs3_m',-1e12,1e12),('pulse_u_mm',-1000,1000),('pulse_v_mm',-1000,1000)]: num(settings,key,lo,hi)
    if settings['field_grid'] not in (64,128,256,512): raise ValueError('Field grid must be 64, 128, 256 or 512.')
    if settings['pulse_samples'] not in (65,129,257,513): raise ValueError('Pulse spectral samples must be 65, 129, 257 or 513.')
    for key in ('field_after','pulse_use_field','pulse_after'):
        if not isinstance(settings[key],bool): raise ValueError(key+' must be true or false.')
    ids=set(); sources=0; samples=0
    for e in c['elements']:
        if not isinstance(e,dict) or e.get('type') not in CATALOG: raise ValueError('Unknown optical element type.')
        for key,value in CATALOG[e['type']].items(): e.setdefault(key,copy.deepcopy(value))
        if not isinstance(e.get('id'),str) or not e['id'] or len(e['id'])>80 or e['id'] in ids:
            raise ValueError('Every element needs a unique ID.')
        ids.add(e['id'])
        e.setdefault('locked',False)
        if not isinstance(e['locked'],bool): raise ValueError('Locked must be true or false.')
        if not isinstance(e.get('enabled'),bool): raise ValueError('Enabled must be true or false.')
        if not isinstance(e.get('name'),str) or len(e['name'])>100: raise ValueError('Use an element name up to 100 characters.')
        for k in ('x_mm','y_mm','z_mm'): num(e,k,-5000,10000)
        for k in ('azimuth_deg','elevation_deg','roll_deg'): num(e,k,-3600,3600)
        t=e['type']
        if t=='laser':
            for k,lo,hi in [('wavelength_nm',350,2500),('bandwidth_nm',0,200),('power_mw',.0001,1e6),
                            ('beam_radius_mm',.0001,100),('divergence_mrad',0,100)]: num(e,k,lo,hi)
            num(e,'rays',1,4096,True); num(e,'wavelength_samples',1,31,True)
            if e['wavelength_samples']%2!=1: raise ValueError('Use an odd number of wavelength samples from 1 to 31.')
            nodes=np.polynomial.hermite.hermgauss(e['wavelength_samples'])[0]*np.sqrt(2)
            if e['wavelength_nm']+float(nodes[0])*e['bandwidth_nm']/2.355<300: raise ValueError('Sampled wavelengths must stay above 300 nm.')
            if e['wavelength_nm']+float(nodes[-1])*e['bandwidth_nm']/2.355>2500: raise ValueError('Sampled wavelengths must stay below 2500 nm.')
            for key,lo,hi in [('wavefront_radius_mm',-1e9,1e9),('polarization_angle_deg',-3600,3600),('ellipticity_deg',-45,45),('source_gdd_fs2',-1e9,1e9),('source_tod_fs3',-1e12,1e12)]: num(e,key,lo,hi)
            if e['pulse_profile'] not in ('gaussian','sech2'): raise ValueError('Unknown pulse spectrum shape.')
            if e['enabled']:
                sources+=1; samples+=e['rays']*(e['wavelength_samples'] if e['bandwidth_nm'] else 1)
                if not inside(np.array([e['x_mm'],e['y_mm'],e['z_mm']]),c['bench']):
                    raise ValueError(f"{e['name']}: laser centre must be inside the working volume.")
        else:
            coefficient='efficiency' if t=='grating' else 'transmission' if t in ('lens','polarizer','waveplate') else 'reflectance'
            num(e,coefficient,0,1)
            if t=='grating':
                for k in ('width_mm','height_mm','clear_width_mm','clear_height_mm'): num(e,k,.01,500)
                if e['clear_width_mm']>e['width_mm'] or e['clear_height_mm']>e['height_mm']:
                    raise ValueError('Grating clear aperture must fit inside its blank.')
                num(e,'lines_per_mm',1,4000); num(e,'order',-5,5,True)
            else:
                num(e,'diameter_mm',.01,500); num(e,'clear_diameter_mm',.01,500)
                if e['clear_diameter_mm']>e['diameter_mm']: raise ValueError('Clear diameter must fit inside the optic diameter.')
            if e['polarization_model'] not in ('scalar','sp'): raise ValueError('Unknown polarization response.')
            for key,lo,hi in [('s_factor',0,1),('p_factor',0,1),('s_phase_deg',-3600,3600),('p_phase_deg',-3600,3600),('coating_gdd_fs2',-1e9,1e9),('coating_tod_fs3',-1e12,1e12)]: num(e,key,lo,hi)
            if t in ('polarizer','waveplate'): num(e,'axis_deg',-3600,3600)
            if t=='polarizer': num(e,'extinction_db',0,100)
            if t=='waveplate':
                num(e,'retardance_deg',-3600,3600); num(e,'reference_wavelength_nm',300,2500)
                if e['retardance_model'] not in ('constant','inverse_wavelength'): raise ValueError('Unknown retardance model.')
            if t=='lens' and not isinstance(e['bare_fresnel'],bool): raise ValueError('Bare Fresnel must be true or false.')
            if t=='mirror_c': num(e,'upper_edge_mm',-e['clear_diameter_mm']/2+.0001,e['clear_diameter_mm']/2)
            if t=='lens':
                if e.get('model') not in ('thin','doublet','prescription'): raise ValueError('Unknown lens model.')
                if not isinstance(e.get('flipped'),bool): raise ValueError('Lens flipped must be true or false.')
                if not isinstance(e.get('surfaces'),list): raise ValueError('Lens surfaces must be a list.')
                if e['model']=='prescription': validate_surfaces(e)
                if e['model']=='thin':
                    num(e,'focal_length_mm',-5000,5000)
                    if abs(e['focal_length_mm'])<.01: raise ValueError('Thin-lens focal length must be nonzero.')
                if e['model']=='doublet':
                    for k in ('t1_mm','t2_mm'): num(e,k,.01,100)
                    for k in ('n1','n2'): num(e,k,1.01,3)
                    for k in ('glass1','glass2'):
                        if e.get(k) not in ('N-LAK22','N-SF6','constant'): raise ValueError('Unknown lens glass.')
                    for k in ('r1_mm','r2_mm','r3_mm'):
                        num(e,k,-1e6,1e6)
                        if abs(e[k])<=e['diameter_mm']/2: raise ValueError('Each spherical radius must exceed the blank radius in magnitude.')
                    # Verify the surfaces do not cross anywhere in the circular blank.
                    rho=np.linspace(0,e['diameter_mm']/2,101)
                    verts=np.array([0,e['t1_mm'],e['t1_mm']+e['t2_mm']])
                    sag=[r-np.sign(r)*np.sqrt(r*r-rho*rho) for r in [e['r1_mm'],e['r2_mm'],e['r3_mm']]]
                    if np.any(verts[1]+sag[1]<=verts[0]+sag[0]) or np.any(verts[2]+sag[2]<=verts[1]+sag[1]):
                        raise ValueError('Lens surfaces cross within the blank; adjust radii, thickness or diameter.')
    if sources>8 or samples>100000: raise ValueError('Use at most 8 lasers and 100000 sampled rays in total.')
    return c


def inside(point,bench):
    return all(-1e-8<=p<=bench[k]+1e-8 for p,k in zip(point,('width_mm','depth_mm','height_mm')))


def boundary(point,direction,bench):
    distances=[]
    for i,k in enumerate(('width_mm','depth_mm','height_mm')):
        if abs(direction[i])>1e-12:
            wall=bench[k] if direction[i]>0 else 0
            distances.append(max(0.,float((wall-point[i])/direction[i])))
    t=min(distances)
    return point+t*direction,t


class WorkSurface(Surface):
    def __init__(self,e):
        n,u,v=pose_frame(e); t=e['type']
        super().__init__(e['id'],[e['x_mm'],e['y_mm'],e['z_mm']],n,
                         radius=e.get('clear_diameter_mm',16)/2,
                         kind='lens' if t=='lens' else 'grating' if t=='grating' else t if t in ('polarizer','waveplate') else 'mirror',
                         half=(e['clear_width_mm']/2,e['clear_height_mm']/2) if t=='grating' else None,
                         upper=e['upper_edge_mm'] if t=='mirror_c' else None)
        self.e=e; self.u=u; self.v=v
        self.blank_radius=e.get('diameter_mm',16)/2
        self.body_half=(e['width_mm']/2,e['height_mm']/2) if t=='grating' else None
        self.axis=n*(-1 if e.get('flipped',False) else 1)
        if t=='lens' and e['model']=='doublet':
            total=e['t1_mm']+e['t2_mm']
            self.vertices=[self.centre+self.axis*z for z in [-total/2,e['t1_mm']-total/2,total/2]]
            self.radii=[e['r1_mm'],e['r2_mm'],e['r3_mm']]
        elif t=='lens' and e['model']=='prescription':
            rows=e['surfaces']; axial=np.r_[0.,np.cumsum([r['thickness_mm'] for r in rows[:-1]])]
            self.vertices=[self.centre+self.axis*z for z in axial-axial[-1]/2]
            self.radii=[r['radius_mm'] for r in rows]

    def surface_hit(self,point,direction,i):
        radius=self.radii[i]
        if radius: return spherical_hit(point,direction,self.vertices[i],self.axis,radius)
        den=float(np.dot(direction,self.axis))
        if abs(den)<1e-12: return None
        distance=float(np.dot(self.vertices[i]-point,self.axis)/den)
        return (point+distance*direction,distance) if distance>1e-8 else None

    def intersect(self,point,direction):
        if self.kind=='lens' and self.e['model']!='thin':
            i=0 if np.dot(direction,self.axis)>0 else len(self.radii)-1
            return self.surface_hit(point,direction,i)
        return super().intersect(point,direction)

    def body_margin(self,hit):
        x,y=self.local(hit)
        if self.half: return min(self.body_half[0]-abs(x),self.body_half[1]-abs(y))
        m=self.blank_radius-np.hypot(x,y)
        if self.upper is not None: m=min(m,self.upper-y)
        return m

    def outline(self,blank=False):
        s=copy.copy(self)
        if blank: s.radius=self.blank_radius; s.half=self.body_half
        return s.polygon()

    def advance_lens(self,point,direction,wavelength,apertures=True):
        if self.e['model']=='thin':
            return point,lens_direction(direction,point,self,self.e['focal_length_mm']),[],None
        e=self.e
        if e['model']=='prescription':
            indices=[1.]+[float(material_index(row['material_after'],wavelength)) for row in e['surfaces']]
        else: indices=[1.]+[e['n'+str(i)] if e['glass'+str(i)]=='constant' else float(glass_index(e['glass'+str(i)],wavelength)) for i in (1,2)]+[1.]
        if not all(math.isfinite(n) and n>0 for n in indices): return point,direction,[],'Invalid refractive index'
        forward=np.dot(direction,self.axis)>0
        sequence=range(len(self.radii)) if forward else range(len(self.radii)-1,-1,-1)
        q=point.copy(); d=direction.copy(); hits=[]
        for visit,i in enumerate(sequence):
            found=(q,0.) if visit==0 else self.surface_hit(q,d,i)
            if found is None: return q,d,hits,'Missed lens interface'
            q=found[0]; margin=self.margin(q)
            if e['model']=='prescription':
                uv=self.local(q); margin=min(margin,e['surfaces'][i]['clear_diameter_mm']/2-np.hypot(*uv))
            before,after=(indices[i],indices[i+1]) if forward else (indices[i+1],indices[i])
            normal=(q-(self.vertices[i]+self.radii[i]*self.axis))/abs(self.radii[i]) if self.radii[i] else self.axis.copy()
            out=refract(d,normal,before,after)
            hits.append(dict(point=q.tolist(),surface=i+1,n_before=before,n_after=after,margin_mm=margin,normal=normal.tolist(),incoming_direction=d.tolist(),outgoing_direction=out.tolist() if out is not None else None,distance_mm=float(found[1])))
            if apertures and margin<0: return q,d,hits,'Clipped inside lens'
            if out is None: return q,d,hits,'Total internal reflection'
            d=out
        return q,d,hits,None


def grating_angles(surface,incoming,outgoing):
    g=surface.v
    a=incoming-g*np.dot(incoming,g); b=outgoing-g*np.dot(outgoing,g)
    deviation=None
    if np.linalg.norm(a)>1e-10 and np.linalg.norm(b)>1e-10:
        a=-unit(a); b=unit(b)
        deviation=float(np.rad2deg(np.arctan2(np.dot(g,np.cross(a,b)),np.dot(a,b))))
    return dict(incidence_deg=float(np.rad2deg(np.arccos(np.clip(abs(np.dot(incoming,surface.normal)),0,1)))),
                diffraction_deg=float(np.rad2deg(np.arccos(np.clip(abs(np.dot(outgoing,surface.normal)),0,1)))),
                deviation_deg=deviation,groove_direction_component=float(np.dot(incoming,g)))


def trace(point,direction,wavelength,surfaces,c,polarization=None,reference_wavelength_nm=None,ignore_apertures=False,source_phase_rad=0.):
    q=np.array(point,float); d=unit(direction); points=[q.tolist()]; events=[]
    throughput=1.; length=0.; opl=0.; groove_phase=float(source_phase_rad); coating_phase=0.; visits={}
    field=np.array(polarization,complex) if polarization is not None else frame(d)[0].astype(complex)
    field-=d*np.dot(field,d)
    if np.linalg.norm(field)>1e-20: field/=np.linalg.norm(field)
    k=2*np.pi/(wavelength*1e-6)
    omega0=2*np.pi*.000299792458/((reference_wavelength_nm or wavelength)*1e-6)
    delta=2*np.pi*.000299792458/(wavelength*1e-6)-omega0
    if not inside(q,c['bench']):
        return dict(points=points,events=events,status='Source sample outside working volume',throughput=0.,length_mm=0.,optical_path_mm=0.)
    status='Interaction limit reached'
    for _ in range(c['max_interactions']):
        end,wall_distance=boundary(q,d,c['bench']); nearest=None
        for surface in surfaces:
            found=surface.intersect(q,d)
            if found and found[1]<wall_distance-1e-7 and surface.body_margin(found[0])>=-1e-8:
                if nearest is None or found[1]<nearest[2]: nearest=(surface,*found)
        if nearest is None:
            length+=wall_distance; opl+=wall_distance; points.append(end.tolist()); status='Reached bench boundary'; break
        surface,hit,distance=nearest; margin=surface.margin(hit); incoming=d.copy()
        length+=distance; opl+=distance; points.append(hit.tolist())
        visits[surface.name]=visits.get(surface.name,0)+1
        event=dict(id=surface.name,name=surface.e['name'],kind=surface.kind,visit=visits[surface.name],
                   point=hit.tolist(),margin_mm=margin,uv=list(surface.local(hit)),wavelength_nm=wavelength,
                   incoming_direction=d.tolist(),outgoing_direction=None,lens_surfaces=[],
                   power_before=throughput,power_after=0.,optical_path_mm=opl,
                   phase_before_rad=float(k*opl+groove_phase+coating_phase),
                   jones_before=pack(field),stokes_before=stokes(field,d))
        events.append(event)
        if margin < -1e-8 and not ignore_apertures: throughput=0.; status='Blocked by optic blank'; break
        if surface.kind=='mirror':
            d=reflection(d,surface.normal); q=hit; coefficient=surface.e['reflectance']
            next_field=element_transfer(surface.e,incoming,d,surface.normal,field,wavelength,surface.u,surface.v)
        elif surface.kind=='grating':
            out=grating(d,surface.normal,surface.v,wavelength*1e-6,surface.e['lines_per_mm'],surface.e['order'])
            if out is None: throughput=0.; status='No propagating grating order'; break
            d=out; q=hit; coefficient=surface.e['efficiency']
            groove_phase+=2*np.pi*surface.e['order']*surface.e['lines_per_mm']*surface.local(hit)[0]
            event['grating_angles']=grating_angles(surface,incoming,d)
            next_field=element_transfer(surface.e,incoming,d,surface.normal,field,wavelength,surface.u,surface.v)
        elif surface.kind in ('polarizer','waveplate'):
            q=hit; coefficient=surface.e['transmission']
            next_field=element_transfer(surface.e,incoming,d,surface.normal,field,wavelength,surface.u,surface.v)
        else:
            q,d,hits,failure=surface.advance_lens(hit,d,wavelength,not ignore_apertures)
            if surface.e['model']=='thin':
                local=surface.local(hit); groove_phase-=k*(local[0]**2+local[1]**2)/(2*surface.e['focal_length_mm'])
            event['lens_surfaces']=hits; next_field=field.copy(); coefficient=surface.e['transmission']
            for i,h in enumerate(hits):
                h['power_before']=float(throughput*np.vdot(next_field,next_field).real); h['jones_before']=pack(next_field)
                h['phase_before_rad']=float(k*opl+groove_phase+coating_phase)
                if i:
                    p=np.array(h['point']); previous=np.array(points[-1]); segment=unit(p-previous)
                    if not inside(p,c['bench']):
                        stop,t=boundary(previous,segment,c['bench']); length+=t; opl+=t*h['n_before']; points.append(stop.tolist())
                        event['lens_surfaces']=hits[:i]
                        event['incomplete']='Bench boundary inside lens'
                        d=np.array(h['incoming_direction'])
                        fraction=float(np.vdot(next_field,next_field).real)
                        throughput*=fraction
                        field=next_field/np.sqrt(fraction) if fraction>1e-25 else np.zeros(3,complex)
                        status='Reached bench boundary'; break
                    distance=float(np.linalg.norm(p-previous)); length+=distance; opl+=distance*h['n_before']; points.append(p.tolist())
                    h['phase_before_rad']=float(k*opl+groove_phase+coating_phase)
                if h['outgoing_direction'] is not None:
                    before=np.array(h['incoming_direction']); after=np.array(h['outgoing_direction']); normal=np.array(h['normal'])
                    if surface.e.get('bare_fresnel',False):
                        next_field=fresnel_transmit(next_field,before,after,normal,h['n_before'],h['n_after'])
                    else: next_field=transported(next_field,before,after)
                h['power_after']=float(event['power_before']*np.vdot(next_field,next_field).real) if h['outgoing_direction'] is not None else 0.
                h['jones_after']=pack(next_field)
            if status=='Reached bench boundary': break
            if failure and not (ignore_apertures and failure.startswith('Clipped')):
                throughput=0.; status=failure; break
            if not hits: next_field=transported(field,incoming,d)
            next_field=element_transfer(surface.e,d,d,surface.normal,next_field,wavelength,surface.u,surface.v)
        fraction=float(np.vdot(next_field,next_field).real)
        throughput*=coefficient*fraction
        field=next_field/np.sqrt(fraction) if fraction>1e-25 else np.zeros(3,complex)
        coating_phase+=surface.e.get('coating_gdd_fs2',0)*delta**2/2+surface.e.get('coating_tod_fs3',0)*delta**3/6
        event.update(outgoing_direction=d.tolist(),exit_point=q.tolist(),power_after=throughput,
                     phase_after_rad=float(k*opl+groove_phase+coating_phase),jones_after=pack(field),
                     stokes_after=stokes(field,d),optical_path_after_mm=opl)
        if event['lens_surfaces']:
            # Common per-pass transmission and supplied Jones action are applied
            # at the final interface; preceding interfaces carry only Fresnel loss.
            event['lens_surfaces'][-1].update(power_after=throughput,jones_after=pack(field))
    return dict(points=points,events=events,status=status,throughput=throughput,length_mm=float(length),
                optical_path_mm=float(opl),phase_rad=float(k*opl+groove_phase+coating_phase),jones=pack(field),stokes=stokes(field,d))


def simulate(config,retain_rays=False):
    c=checked(config); surfaces=[WorkSurface(e) for e in c['elements'] if e['enabled'] and e['type']!='laser']
    scene=[]; warnings=[]
    for s in surfaces:
        scene.append(dict(id=s.name,centre=s.centre.tolist(),normal=s.normal.tolist(),u=s.u.tolist(),v=s.v.tolist(),
                          outline=s.outline(),blank=s.outline(True)))
        if not inside(s.centre,c['bench']): warnings.append(s.e['name']+' centre is outside the work volume.')
    rays=[]; chiefs=[]; spectral_chiefs=[]; spectra=[]; power_in=0.; power_out=0.; escaped=0; total=0
    for source in [e for e in c['elements'] if e['enabled'] and e['type']=='laser']:
        d,u,v=pose_frame(source); centre=np.array([source['x_mm'],source['y_mm'],source['z_mm']]); wl=source['wavelength_nm']
        polar=source_jones(source,u,v)
        chief=trace(centre,d,wl,surfaces,c,polar,wl); chief.update(source_id=source['id'],wavelength_nm=wl); chiefs.append(chief)
        count=source['rays']; rng=np.random.default_rng(20261013)
        offsets=rng.normal(0,source['beam_radius_mm']/2,(count,2))
        angles=np.random.default_rng(20261014).normal(0,source['divergence_mrad']*.001/2,(count,2))
        if count==1: offsets[:]=0; angles[:]=0
        n=source['wavelength_samples'] if source['bandwidth_nm'] else 1
        samples,weights=np.polynomial.hermite.hermgauss(n)
        samples*=np.sqrt(2); weights/=np.sqrt(np.pi)
        if source.get('pulse_profile')=='sech2':
            weights*=1/np.cosh(samples*(2*np.arccosh(np.sqrt(2))/2.355))**2/np.exp(-samples*samples/2)
            weights/=weights.sum()
        spectrum=[]
        power_in+=source['power_mw']
        for sample,weight in zip(samples,weights):
            wavelength=wl+sample*source['bandwidth_nm']/2.355
            spectral=trace(centre,d,float(wavelength),surfaces,c,polar,wl)
            spectral.update(source_id=source['id'],wavelength_nm=float(wavelength),spectral_weight=float(weight))
            spectral_chiefs.append(spectral)
            spectrum.append(dict(wavelength_nm=float(wavelength),weight=float(weight)))
            for offset,angle in zip(offsets,angles):
                q=centre+offset[0]*u+offset[1]*v
                curvature=source.get('wavefront_radius_mm',0)
                slope=offset/curvature if curvature else np.zeros(2)
                launch_phase=np.pi*float(np.dot(offset,offset))/(wavelength*1e-6*curvature) if curvature else 0.
                ray=trace(q,unit(d+(angle[0]+slope[0])*u+(angle[1]+slope[1])*v),float(wavelength),surfaces,c,polar,wl,source_phase_rad=launch_phase)
                ray.update(source_id=source['id'],wavelength_nm=float(wavelength),weight=float(weight/count))
                rays.append(ray); total+=1
                if ray['status']=='Reached bench boundary':
                    power_out+=source['power_mw']*ray['weight']*ray['throughput']; escaped+=1
        spectra.append(dict(source_id=source['id'],name=source['name'],samples=spectrum))
        if chief['status']!='Reached bench boundary': warnings.append(source['name']+': '+chief['status']+'.')
    if not chiefs: warnings.append('Add or enable a laser source to trace a beam.')
    if any(r['status']=='Interaction limit reached' for r in rays): warnings.append('Some rays reached the interaction limit; check for a closed optical loop.')
    from diagnostics import footprints
    profiles=footprints(c,surfaces,rays)
    display=rays if retain_rays or len(rays)<=800 else rays[::int(np.ceil(len(rays)/800))]
    return dict(config=c,scene=scene,chiefs=chiefs,spectral_chiefs=spectral_chiefs,spectra=spectra,rays=display,footprints=profiles,warnings=warnings,
                metrics=dict(input_power_mw=power_in,boundary_power_mw=power_out,
                             transmission=power_out/power_in if power_in else 0.,sampled_rays=total,
                             escaped_rays=escaped,displayed_rays=len(display),chief_length_mm=sum(r['length_mm'] for r in chiefs)))
