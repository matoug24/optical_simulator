"""Three opt-in teaching layouts. No changes to startup or saved product libraries."""
import copy
import json
from pathlib import Path
import numpy as np
from model import default_config, element, checked, simulate, analysis_config, WorkSurface, grating, unit
from materials import builtins
from waveoptics import lens_abcd

MATERIALS={m['id']:m for m in builtins()}


def pose(point,direction):
    d=unit(direction)
    return dict(x_mm=float(point[0]),y_mm=float(point[1]),z_mm=float(point[2]),
                azimuth_deg=float(np.degrees(np.arctan2(d[1],d[0]))),elevation_deg=float(np.degrees(np.arcsin(d[2]))))


def mirror(kind,ident,point,incoming,outgoing,name):
    return element(kind,ident,name=name,**pose(point,unit(incoming)-unit(outgoing)))


def source(point,name='Illustrative 780 nm source',**changes):
    values=dict(wavelength_nm=780.,bandwidth_nm=8.,wavelength_samples=7,rays=97,
                beam_radius_mm=.7,divergence_mrad=0.,power_mw=100.)
    values.update(changes)
    return element('laser','source',name=name,**pose(point,[1,0,0]),**values)


def base(name,width=450,depth=300,height=120):
    c=default_config();c.update(name=name,bench=dict(width_mm=width,depth_mm=depth,height_mm=height));return c


def prescription(ident,point,direction,rows,name):
    surfaces=[dict(radius_mm=r,thickness_mm=t,clear_diameter_mm=24.,material_after=copy.deepcopy(MATERIALS[m])) for r,t,m in rows]
    return element('lens',ident,name=name,model='prescription',surfaces=surfaces,**pose(point,direction))


def dispersion_example():
    c=base('Learning 1 · folded spectral dispersion and pulse shaping')
    laser=source([20,40,30],source_gdd_fs2=20000.)
    # Use the established signed -11 degree grating solution at 780 nm.
    reference=analysis_config()['elements'][1]
    g=element('grating','grating',name='D · spectral disperser',**pose([420,40,30],[1,0,0]))
    for key in ('azimuth_deg','elevation_deg','roll_deg'):g[key]=reference[key]
    s=WorkSurface(g);d=grating(np.array([1.,0,0]),s.normal,s.v,.000780,g['lines_per_mm'],g['order'])
    at=lambda distance:s.centre+distance*d
    lens=element('lens','spectral-lens',name='75 mm doublet · dispersed bundle',**pose(at(150),d))
    fold=mirror('mirror_e','fold',at(230),d,[0,1,0],'E · fold toward +Y')
    x,y,z=at(230)
    qwp=element('waveplate','quarter-wave',name='Quarter-wave plate · 45°',axis_deg=45.,**pose([x,y+35,z],[0,1,0]))
    pol=element('polarizer','analyzer',name='Analyzer · polarization-to-power',axis_deg=0.,**pose([x,y+65,z],[0,1,0]))
    plate=prescription('glass-plate',[x,y+95,z],[0,1,0],[(0,3,'N-LAK22'),(0,0,'air')],'3 mm N-LAK22 · material dispersion')
    final=prescription('final-lens',[x,y+145,z],[0,1,0],[(50,5,'N-LAK22'),(-50,0,'air')],'Dispersive singlet · final focus')
    c['elements']=[laser,g,lens,fold,qwp,pol,plate,final]
    c['learning_notes']=dict(goal='Connect spectral spread, per-ray lens refraction, material dispersion and pulse phase.',
        start='Trace; inspect grating angles and the spectral lens surfaces; calculate pulse at analyzer or glass-plate; find focus after final-lens.',
        experiments=['Change laser bandwidth from 8 to 2 or 16 nm.','Change plate thickness from 3 to 9 mm.','Change source GDD or supplied additional GDD in Pulse & Dispersion.','Rotate the quarter-wave plate or analyzer and watch power.'],
        limit='An illustrative folded dispersive path, not a calibrated compressor. Supplied additional GDD is a numerical phase term, not an automatically designed optic.')
    return checked(c)


def telescope_example():
    c=base('Learning 2 · achromatic telescope and air-spaced focusing assembly',500,300,120)
    laser=source([20,70,35])
    waveplate=element('waveplate','input-waveplate',name='Input quarter-wave plate',axis_deg=45.,**pose([55,70,35],[1,0,0]))
    first=element('lens','telescope-1',name='Telescope A · 75 mm doublet',**pose([110,70,35],[1,0,0]))
    second=element('lens','telescope-2',name='Telescope B · scaled 150 mm doublet',**pose([335,70,35],[1,0,0]))
    # A geometrically scaled prescription is illustrative, not another catalog product.
    for key in ('r1_mm','r2_mm','r3_mm','t1_mm','t2_mm'):second[key]*=2
    m1,m2=lens_abcd(first,780),lens_abcd(second,780)
    gap=-m1['A']/m1['C']-m2['D']/m2['C']
    second['x_mm']=first['x_mm']+5+gap+10
    one=mirror('mirror_b','fold-1',[440,70,35],[1,0,0],[0,1,0],'B · telescope output fold')
    two=mirror('mirror_e','fold-2',[440,230,35],[0,1,0],[-1,0,0],'E · return along −X')
    assembly=prescription('focusing-assembly',[300,230,35],[-1,0,0],
        [(80,5,'N-LAK22'),(-80,10,'air'),(100,5,'N-SF6'),(-100,0,'air')],
        'Two singlets · 10 mm internal air gap')
    analyzer=element('polarizer','output-analyzer',name='Output analyzer',axis_deg=0.,**pose([200,230,35],[-1,0,0]))
    c['elements']=[laser,waveplate,first,second,one,two,assembly,analyzer]
    c['learning_notes']=dict(goal='Study a roughly 2× Keplerian beam expander and a four-surface, air-spaced lens assembly.',
        start='Use Top view at Z = 35 mm. Compare surface radii at telescope-1 and telescope-2; find focus after focusing-assembly.',
        experiments=['Move telescope-2 by ±5 mm along X to change output convergence.','Change the internal air gap in focusing-assembly from 10 to 5 or 20 mm.','Swap one singlet material and compare chromatic focal shift.','Reduce an internal clear aperture to see clipping at that interface.'],
        limit='The telescope spacing makes its first-order C term vanish at 780 nm. Finite rays retain spherical/chromatic aberrations. The 150 mm doublet is an illustrative scaled prescription.')
    return checked(c)


def alignment_3d_example():
    c=base('Learning 3 · three-dimensional folded alignment',400,300,150)
    laser=source([30,50,25])
    points=[np.array(p,dtype=float) for p in [[160,50,25],[160,160,90],[320,160,90],[320,240,35],[120,240,35]]]
    directions=[unit(points[i+1]-points[i]) for i in range(4)]
    mirrors=[mirror('mirror_b','rise-fold',points[0],[1,0,0],directions[0],'B · upward fold'),
             mirror('mirror_c','high-fold',points[1],directions[0],directions[1],'C · high-level cut-edge fold'),
             mirror('mirror_e','descent-fold',points[2],directions[1],directions[2],'E · downward fold'),
             mirror('mirror_b','low-fold',points[3],directions[2],directions[3],'B · lower-level return'),
             mirror('mirror_e','exit-fold',points[4],directions[3],[0,-1,0],'E · fold toward −Y')]
    focus=element('lens','return-lens',name='75 mm doublet · lower return',**pose([230,240,35],[-1,0,0]))
    qwp=element('waveplate','output-waveplate',name='Quarter-wave plate after 3D folds',axis_deg=45.,**pose([120,180,35],[0,-1,0]))
    pol=element('polarizer','output-analyzer',name='Analyzer after 3D folds',axis_deg=0.,**pose([120,110,35],[0,-1,0]))
    final=element('lens','exit-lens',name='Ideal 50 mm lens · comparison',model='thin',focal_length_mm=50.,**pose([120,65,35],[0,-1,0]))
    c['elements']=[laser,*mirrors[:4],focus,mirrors[4],qwp,pol,final]
    c['learning_notes']=dict(goal='Understand azimuth/elevation alignment, changing beam heights, cut-edge apertures and 3D polarization transport.',
        start='Compare Front, Left and both corner views. Follow rise-fold → high-fold → descent-fold → low-fold. Find focus after return-lens.',
        experiments=['Apply a 0.1–0.5 mrad U/V tilt to rise-fold; inspect downstream surface centroids.','Move high-fold by ±0.2 mm in Z.','Change the C mirror cut edge or roll.','Use an XZ ruler plane at Y = 50 mm or XY at Z = 35 mm; tilted legs require separate projections.'],
        limit='Rulers measure within one selected coordinate plane, not a sloping 3D path. Mirror coating factors are supplied scalar values, not measured coating curves.')
    return checked(c)


BUILDERS={'complex_dispersion':dispersion_example,'complex_telescope':telescope_example,'complex_3d_alignment':alignment_3d_example}


def write_examples():
    folder=Path(__file__).resolve().parent/'examples';folder.mkdir(exist_ok=True)
    for key,builder in BUILDERS.items():
        config=builder();result=simulate(config);chief=result['chiefs'][0]
        expected=[e['id'] for e in config['elements'] if e['type']!='laser']
        actual=[e['id'] for e in chief['events']]
        if actual!=expected or chief['status']!='Reached bench boundary' or chief['throughput']<=0:
            raise ValueError(f'{key}: intended route failed: {actual}, {chief["status"]}')
        (folder/(key+'.json')).write_text(json.dumps(config,indent=2,allow_nan=False),encoding='utf-8')
        print(key,actual,'boundary power / mW:',result['metrics']['boundary_power_mw'])


if __name__=='__main__':write_examples()
