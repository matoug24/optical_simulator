"""Lens/grating audit: independent catalog, Snell, momentum and pulse benchmarks."""
import copy
import unittest
import numpy as np
from model import checked, element, WorkSurface, grating, unit, pose_frame, simulate, spectral_focus_config
from doublet import glass_index
from waveoptics import lens_abcd, compute_field
from diagnostics import chief, encounter
from test_analysis import straight
from pulses import pulse_analysis, phase_interpolate, C_MM_FS


class OpticsReviewTests(unittest.TestCase):
    def test_schott_catalog_indices_and_edmund_focal_lengths(self):
        # Independent nominal SCHOTT nd values at the helium d line.
        self.assertAlmostEqual(float(glass_index('N-LAK22',587.6)),1.65113,delta=5e-6)
        self.assertAlmostEqual(float(glass_index('N-SF6',587.6)),1.80518,delta=7e-6)
        m=lens_abcd(element('lens','l'),880)
        self.assertAlmostEqual(m['focal_length_mm'],75,delta=.01)
        self.assertAlmostEqual(m['A']*m['focal_length_mm'],69.06,delta=.01)

    def test_snell_and_reciprocity_for_angles_wavelengths_and_flips(self):
        for flipped in (False,True):
            for wavelength in (760,780,800,880,1050):
                e=element('lens','l',azimuth_deg=25,elevation_deg=11,roll_deg=37,flipped=flipped)
                s=WorkSurface(e)
                for shift,angle in ((0.,0.),(1.5,.02),(-2.,-.04)):
                    d=unit(s.axis+angle*s.u); p=s.centre-40*s.axis+shift*s.u
                    hit=s.intersect(p,d); self.assertIsNotNone(hit)
                    q,out,hits,failure=s.advance_lens(hit[0],d,wavelength); self.assertIsNone(failure)
                    for h in hits:
                        n=np.array(h['normal']); a=np.array(h['incoming_direction']); b=np.array(h['outgoing_direction'])
                        # Tangential wavevector is conserved at each glass interface.
                        np.testing.assert_allclose(h['n_before']*(a-n*np.dot(a,n)),h['n_after']*(b-n*np.dot(b,n)),atol=2e-12)
                        self.assertAlmostEqual(float(np.linalg.norm(b)),1,12)
                    reverse_hit=s.intersect(q+20*out,-out)
                    back,back_d,_,failure=s.advance_lens(reverse_hit[0],-out,wavelength)
                    self.assertIsNone(failure); np.testing.assert_allclose(back_d,-d,atol=2e-10)
                    np.testing.assert_allclose(back,hit[0],atol=2e-8)

    def test_grating_conical_momentum_and_angular_dispersion(self):
        e=element('grating','g',azimuth_deg=-43,elevation_deg=12,roll_deg=19); s=WorkSurface(e)
        d=unit(.83*s.normal+.5*s.u+.18*s.v); wavelength=780e-6
        out=grating(d,s.normal,s.v,wavelength,1400,-1); self.assertIsNotNone(out)
        self.assertAlmostEqual(float(np.dot(out-d,s.v)),0,12)
        self.assertAlmostEqual(float(np.dot(out-d,s.u)),-wavelength*1400,12)
        self.assertLess(np.dot(d,s.normal)*np.dot(out,s.normal),0)
        step=1e-8
        plus=grating(d,s.normal,s.v,wavelength+step,1400,-1); minus=grating(d,s.normal,s.v,wavelength-step,1400,-1)
        q=np.dot(out,s.u); root=abs(np.dot(out,s.normal)); sign=np.sign(np.dot(out,s.normal))
        expected=-1400*s.u+sign*q*1400/root*s.normal
        np.testing.assert_allclose((plus-minus)/(2*step),expected,rtol=2e-8,atol=1e-5)

    def test_grazing_order_roundoff_and_real_evanescence(self):
        n=np.array([1.,0,0]); g=np.array([0.,0,1.]); d=n.copy()
        self.assertIsNotNone(grating(d,n,g,1e-3,1000*(1+2e-16),1))
        self.assertIsNone(grating(d,n,g,1e-3,1000.01,1))

    def test_dispersed_bundle_refracts_individually_and_spectral_crossing_is_in_bench(self):
        c=spectral_focus_config(); r=simulate(c)
        self.assertEqual(len(r['spectral_chiefs']),7)
        for ray in r['spectral_chiefs']:
            lens=encounter(ray,'lens-demo'); self.assertIsNotNone(lens)
            self.assertEqual(len(lens['lens_surfaces']),3)
            s=WorkSurface(c['elements'][2]); entry=np.array(lens['point']); incoming=np.array(lens['incoming_direction'])
            q,d,_,failure=s.advance_lens(entry,incoming,ray['wavelength_nm']); self.assertIsNone(failure)
            np.testing.assert_allclose(d,lens['outgoing_direction'],atol=1e-12)
        ends=[encounter(ray,'mirror-demo') for ray in (r['spectral_chiefs'][0],r['spectral_chiefs'][-1])]
        self.assertTrue(all(e is not None for e in ends))
        p1,p2=[np.array(e['exit_point']) for e in ends]; d1,d2=[np.array(e['outgoing_direction']) for e in ends]
        t=np.linalg.lstsq(np.column_stack((d1,-d2)),p2-p1,rcond=None)[0]
        cross=p1+t[0]*d1; self.assertTrue(np.all(t>0)); self.assertGreater(cross[1],100); self.assertLess(cross[1],150)
        self.assertLess(np.linalg.norm(cross-(p2+t[1]*d2)),1e-8)
        self.assertAlmostEqual(sum(s['weight'] for s in r['spectra'][0]['samples']),1,12)

    def test_curvature_launch_phase_matches_ray_launch_slopes(self):
        c=straight(40); c['elements'][0].update(rays=7,bandwidth_nm=0,wavefront_radius_mm=150)
        r=simulate(c); source=c['elements'][0]
        for ray in r['rays']:
            event=ray['events'][0]; offset=np.array(ray['points'][0])-np.array([source['x_mm'],source['y_mm'],source['z_mm']])
            k=2*np.pi/(source['wavelength_nm']*1e-6)
            self.assertAlmostEqual(event['phase_before_rad']-k*event['optical_path_mm'],k*np.dot(offset,offset)/(2*150),8)

    def test_source_chirp_is_visible_and_compensates(self):
        c=straight(); c['elements'][0]['source_gdd_fs2']=20000
        r=pulse_analysis(c,'s','t')
        self.assertGreater(r['input_fwhm_fs'],r['reference_fwhm_fs']*1.9)
        self.assertAlmostEqual(r['output_fwhm_fs'],r['input_fwhm_fs'],delta=.001)
        c['analysis']['extra_gdd_fs2']=-20000; compressed=pulse_analysis(c,'s','t')
        self.assertAlmostEqual(compressed['output_fwhm_fs'],compressed['reference_fwhm_fs'],delta=.001)
        self.assertAlmostEqual(compressed['input_fwhm_fs'],r['input_fwhm_fs'],delta=.001)

    def test_chirp_sign_matches_positive_gdd_and_carrier_period(self):
        c=straight(); c['analysis']['extra_gdd_fs2']=20000; r=pulse_analysis(c,'s','t')
        points=[(t,wl) for t,wl,i in zip(r['time_fs'],r['output_instantaneous_wavelength_nm'],r['output_intensity']) if wl is not None and i>r['relative_peak']*.25]
        slope=np.polyfit(*np.array(points).T,1)[0]; self.assertLess(slope,0)
        self.assertAlmostEqual(r['carrier_period_fs'],2.601799942545586,9)
        self.assertEqual(len(r['carrier_envelope_time_fs']),len(r['output_envelope_real']))
        self.assertTrue(all(np.isfinite(r['output_envelope_real'])))
        # Narrow spectra have coarser native temporal steps, but the carrier view
        # must still have bracketing envelope samples for its 20–200 fs window.
        c['elements'][0]['bandwidth_nm']=.1; narrow=pulse_analysis(c,'s','t')
        self.assertGreaterEqual(len(narrow['carrier_envelope_time_fs']),3)
        self.assertLess(narrow['carrier_envelope_time_fs'][0],-100)
        self.assertGreater(narrow['carrier_envelope_time_fs'][-1],100)

    def test_continuous_phase_interpolation_preserves_gdd(self):
        x=np.linspace(-2,2,17); y=4+3*x+5000*x*x; points=np.linspace(-2,2,4001)
        np.testing.assert_allclose(phase_interpolate(x,y,points),4+3*points+5000*points*points,atol=1e-10)

    def test_first_order_field_lens_matches_gaussian_q_propagation(self):
        c=straight(180); source=c['elements'][0]; source['beam_radius_mm']=.3
        lens=element('lens','l',x_mm=100,y_mm=75)
        c['elements'].insert(1,lens); c['analysis'].update(field_grid=256,field_span_mm=2)
        m=lens_abcd(lens,780); lam=780e-6
        # Source plane x=20, front vertex x=95; exit vertex x=105, target x=200.
        q=75+1j*np.pi*.3**2/lam; q=(m['A']*q+m['B'])/(m['C']*q+m['D'])+95
        expected=np.sqrt(-lam/(np.pi*np.imag(1/q)))
        r=compute_field(c,'s','t'); np.testing.assert_allclose(r['radius_mm'],expected,rtol=.003)
        self.assertAlmostEqual(r['power_mw'],10*.995,delta=.003)

    def test_doublet_material_gdd_matches_independent_phase_derivative(self):
        c=straight(180); lens=element('lens','l',x_mm=100,y_mm=75); c['elements'].insert(1,lens)
        omega0=2*np.pi*C_MM_FS/(780e-6); step=omega0*.001
        def phi(omega):
            wavelength=2*np.pi*C_MM_FS/omega*1e6
            return omega/C_MM_FS*(6*float(glass_index('N-LAK22',wavelength))+4*float(glass_index('N-SF6',wavelength)))
        expected=(-phi(omega0+2*step)+16*phi(omega0+step)-30*phi(omega0)+16*phi(omega0-step)-phi(omega0-2*step))/(12*step**2)
        r=pulse_analysis(c,'s','t'); self.assertGreater(expected,0)
        self.assertAlmostEqual(r['optical_gdd_fs2']/expected,1,delta=2e-4)


if __name__=='__main__': unittest.main()
