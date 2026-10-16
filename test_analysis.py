"""Independent analytic benchmarks for analysis physics and surface diagnostics."""
import copy
import json
import unittest
import numpy as np
from model import default_config, folded_config, element, checked, simulate, WorkSurface, pose_frame, unit
from diagnostics import chief, encounter, solve_grating, sensitivity, convergence
from polarization import source_jones, stokes, element_transfer, fresnel_transmit
from waveoptics import angular_spectrum, compute_field, lens_abcd, field_convergence
from pulses import pulse_analysis, pulse_convergence, C_MM_FS


def straight(distance=100):
    c=default_config()
    c['elements']=[element('laser','s',x_mm=20,y_mm=75,wavelength_nm=780,bandwidth_nm=5,beam_radius_mm=.2),
                   element('waveplate','t',x_mm=20+distance,y_mm=75,retardance_deg=0,transmission=1)]
    c=checked(c); c['analysis'].update(field_grid=128,field_span_mm=2,field_after=True)
    return c


class AnalysisTests(unittest.TestCase):
    def test_footprints_only_elements_and_three_lens_interfaces(self):
        r=simulate(folded_config()); ids={p['id'] for p in r['footprints']}
        self.assertEqual(ids,{'mirror-b-1','mirror-c-1','lens-1','mirror-e-1'})
        lens=[p for p in r['footprints'] if p['id']=='lens-1']
        self.assertEqual({p['interface'] for p in lens},{1,2,3})
        for p in r['footprints']:
            area=(2*p['bound_mm']/64)**2
            self.assertAlmostEqual(np.sum(p['density_mw_mm2'])*area,p['incident_power_mw'],8)
            self.assertLessEqual(p['after_power_mw'],p['incident_power_mw']+1e-8)

    def test_signed_grating_target_and_momentum(self):
        c=straight(); c['elements'][1]=element('grating','g',x_mm=120,y_mm=75,azimuth_deg=-45)
        r=solve_grating(c,'s','g',-11)
        self.assertAlmostEqual(r['angles']['deviation_deg'],-11,8)
        surface=WorkSurface(r['config']['elements'][1]); d=np.array(r['outgoing_direction'])
        self.assertAlmostEqual(np.dot(d-[1,0,0],surface.u),-780e-6*1400,10)
        self.assertLess(np.dot(d,surface.normal)*np.dot([1,0,0],surface.normal),0)
        with self.assertRaises(ValueError): solve_grating(c,'s','g',170)

    def test_reflection_alignment_derivative(self):
        c=folded_config(); r=sensitivity(c,'laser-1','mirror-c-1',element_id='mirror-b-1')
        row=next(v for v in r['rows'] if v['axis']=='tilt_v')
        # Surface U is oblique by 45 degrees, hence 2*70 mm / cos(45°).
        self.assertFalse(row['issue']); self.assertAlmostEqual(abs(row['du']),.14*np.sqrt(2),5)
        self.assertAlmostEqual(abs(row['dangle_u']),4,4)

    def test_sampling_refinements_and_conservative_status(self):
        r=convergence(straight(),'s','t',levels=3,tolerance_percent=20)
        self.assertEqual([v['rays_per_wavelength'] for v in r['rows']],[33,132,528])
        self.assertTrue(r['converged']); self.assertEqual(len(r['rows']),3)
        self.assertFalse(convergence(straight(),'s','t',levels=2,tolerance_percent=20)['converged'])

    def test_sampling_cap_does_not_fake_a_refinement(self):
        c=straight(); c['elements'][0].update(rays=4096,bandwidth_nm=0)
        r=convergence(c,'s','t',levels=3,tolerance_percent=20)
        self.assertEqual(len(r['rows']),1); self.assertFalse(r['converged'])

    def test_gaussian_free_space_field(self):
        c=straight(200); r=compute_field(c,'s','t')
        zray=np.pi*.2**2/(780e-6); expected=.2*np.sqrt(1+(200/zray)**2)
        np.testing.assert_allclose(r['radius_mm'],expected,rtol=2e-4)
        self.assertAlmostEqual(r['power_mw'],10,5)
        self.assertTrue(field_convergence(c,'s','t')['converged'])

    def test_angular_spectrum_reversibility_and_airy_diffraction(self):
        n=256; span=2.; xx=(np.arange(n)-n//2)*span/n; X,Y=np.meshgrid(xx,xx)
        field=np.array([(X*X+Y*Y<.08**2).astype(complex),np.zeros((n,n),complex)])
        out,_=angular_spectrum(field,780e-6,30,span)
        outside=X*X+Y*Y>.15**2
        self.assertGreater(np.sum(abs(out[:,outside])**2)/np.sum(abs(out)**2),.05)
        gaussian=np.array([np.exp(-(X*X+Y*Y)/.2**2),np.zeros((n,n))])
        forward,_=angular_spectrum(gaussian,780e-6,50,span); back,_=angular_spectrum(forward,780e-6,-50,span)
        np.testing.assert_allclose(back,gaussian,atol=1e-5)

    def test_two_pupils_interfere(self):
        n=256; xx=(np.arange(n)-n//2)*2/n; X,Y=np.meshgrid(xx,xx)
        left=np.exp(-((X+.08)**2+Y*Y)/.025**2); right=np.exp(-((X-.08)**2+Y*Y)/.025**2)
        a,_=angular_spectrum(np.array([left,np.zeros_like(left)]),780e-6,100,2)
        b,_=angular_spectrum(np.array([right,np.zeros_like(right)]),780e-6,100,2)
        coherent=abs(a+b)**2; incoherent=abs(a)**2+abs(b)**2
        self.assertGreater(float(np.max(abs(coherent-incoherent))),float(np.max(incoherent))*.5)

    def test_lens_abcd_invariant_and_reverse(self):
        e=element('lens','l'); m=lens_abcd(e,780)
        self.assertAlmostEqual(m['A']*m['D']-m['B']*m['C'],1,6)
        self.assertGreater(m['focal_length_mm'],70); self.assertLess(m['focal_length_mm'],80)
        e['flipped']=True; reverse=lens_abcd(e,780)
        self.assertAlmostEqual(m['A'],reverse['D'],6); self.assertAlmostEqual(m['C'],reverse['C'],6)

    def test_polarizer_malus_law_and_quarter_waveplate(self):
        c=straight(); source=c['elements'][0]; source['polarization_angle_deg']=45
        c['elements'][1]=element('polarizer','t',x_mm=120,y_mm=75,axis_deg=0,extinction_db=100,transmission=1)
        r=chief(c,'s'); e=encounter(r,'t'); self.assertAlmostEqual(e['power_after'],.5,8)
        c['elements'][1]=element('waveplate','t',x_mm=120,y_mm=75,axis_deg=0,retardance_deg=90,transmission=1)
        p=chief(c,'s')['stokes']; self.assertAlmostEqual(abs(p['V']),1,8); self.assertAlmostEqual(p['Q'],0,8)
        self.assertIsNone(p['linear_angle_deg'])

    def test_fresnel_power_and_brewster(self):
        angle=np.arctan(1.5); before=np.array([np.cos(angle),np.sin(angle),0]); after=unit([np.sqrt(1-(np.sin(angle)/1.5)**2),np.sin(angle)/1.5,0]); normal=np.array([1,0,0])
        s=np.array([0,0,1.]); p=np.cross(s,before)
        es=fresnel_transmit(s,before,after,normal,1,1.5); ep=fresnel_transmit(p,before,after,normal,1,1.5)
        self.assertLess(np.vdot(es,es).real,1); self.assertAlmostEqual(np.vdot(ep,ep).real,1,10)

    def test_scalar_and_sp_power_coefficients(self):
        c=folded_config(); r=chief(checked(c),'laser-1'); self.assertAlmostEqual(r['throughput'],.99**3*.995,10)
        m=c['elements'][1]; m.update(polarization_model='sp',s_factor=.5,p_factor=.5)
        rr=chief(checked(c),'laser-1'); self.assertAlmostEqual(rr['throughput'],r['throughput']*.5,10)

    def test_gaussian_pulse_gdd_broadening_and_energy(self):
        c=straight(); r=pulse_analysis(c,'s','t'); self.assertAlmostEqual(r['optical_gdd_fs2'],0,3)
        self.assertAlmostEqual(r['input_fwhm_fs'],r['output_fwhm_fs'],5)
        c['analysis']['extra_gdd_fs2']=20000; broadened=pulse_analysis(c,'s','t')
        tau=r['input_fwhm_fs']; expected=tau*np.sqrt(1+(4*np.log(2)*20000/tau**2)**2)
        self.assertAlmostEqual(broadened['output_fwhm_fs']/expected,1,delta=.007)
        self.assertAlmostEqual(broadened['energy_ratio'],1,8)
        self.assertTrue(pulse_convergence(c,'s','t')['converged'])

    def test_coating_source_and_fibre_dispersion_sum(self):
        c=straight(); c['elements'][0]['source_gdd_fs2']=700; c['elements'][1]['coating_gdd_fs2']=900
        c['analysis'].update(extra_gdd_fs2=-200,fibre_length_m=2,fibre_beta2_fs2_m=300)
        r=pulse_analysis(c,'s','t'); self.assertAlmostEqual(r['net_gdd_fs2'],2000,delta=.01)
        c['analysis']['pulse_after']=False; self.assertAlmostEqual(pulse_analysis(c,'s','t')['net_gdd_fs2'],1100,delta=.01)

    def test_grating_angular_dispersion_gdd(self):
        c=straight(); g=element('grating','g',x_mm=120,y_mm=75,azimuth_deg=-45)
        c['elements']=[c['elements'][0],g]; r=chief(checked(c),'s'); d=np.array(r['events'][0]['outgoing_direction'])
        distance=60; p=np.array([120,75,20])+distance*d
        t=element('waveplate','t',x_mm=float(p[0]),y_mm=float(p[1]),z_mm=20,azimuth_deg=float(np.rad2deg(np.arctan2(d[1],d[0]))),retardance_deg=0,transmission=1)
        c['elements'].append(t); pulse=pulse_analysis(c,'s','t')
        beta=np.arccos(abs(np.dot(d,WorkSurface(g).normal))); lam=780e-6
        expected=-distance*lam**3*1400**2/(2*np.pi*C_MM_FS**2*np.cos(beta)**2)
        self.assertAlmostEqual(pulse['optical_gdd_fs2']/expected,1,delta=.002)

    def test_local_field_pulse_power_and_serialization(self):
        c=straight(20); c['analysis'].update(pulse_use_field=True,field_grid=64)
        r=pulse_analysis(c,'s','t'); self.assertGreater(r['energy_ratio'],.95); self.assertLessEqual(r['energy_ratio'],1.02)
        self.assertEqual(r['field_grid_used'],64); self.assertEqual(r['field_envelope_samples'],65)
        self.assertAlmostEqual(r['output_fwhm_fs']/r['input_fwhm_fs'],1,delta=.02)
        json.dumps(r,allow_nan=False); json.dumps(compute_field(c,'s','t'),allow_nan=False)


if __name__=='__main__': unittest.main()
