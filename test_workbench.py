"""Physics, arbitrary-route and boundary regression checks for the new app."""
import copy
import math
import unittest
import numpy as np
from model import default_config, folded_config, element, checked, simulate, trace, WorkSurface, unit
from doublet import trace_doublet


def simple(*optics):
    c=default_config()
    c['elements']=[element('laser','s',x_mm=20,y_mm=60,z_mm=20,rays=1),*optics]
    return c


class WorkbenchTests(unittest.TestCase):
    def test_default_route_and_loss(self):
        r=simulate(folded_config()); chief=r['chiefs'][0]
        self.assertEqual([e['id'] for e in chief['events']],['mirror-b-1','mirror-c-1','lens-1','mirror-e-1'])
        self.assertEqual(chief['status'],'Reached bench boundary')
        self.assertAlmostEqual(r['metrics']['transmission'],.99**3*.995,12)
        self.assertAlmostEqual(chief['length_mm'],405.,8)

    def test_default_bench_is_always_empty(self):
        config=default_config(); self.assertEqual(config['elements'],[])
        self.assertEqual(config['bench']['width_mm'],300)
        self.assertEqual(config['bench']['depth_mm'],150)
        config['elements'].append(element('laser','a'))
        self.assertEqual(default_config()['elements'],[])

    def test_free_space_exact_wall(self):
        chief=simulate(simple())['chiefs'][0]
        self.assertEqual(chief['events'],[])
        np.testing.assert_allclose(chief['points'][-1],[300,60,20],atol=1e-10)

    def test_nearest_hit_independent_of_list_order(self):
        near=element('mirror_b','near',x_mm=80,y_mm=60,z_mm=20,azimuth_deg=-45)
        far=element('mirror_e','far',x_mm=150,y_mm=60,z_mm=20)
        c=simple(far,near); first=simulate(c)['chiefs'][0]
        c['elements'].reverse(); second=simulate(c)['chiefs'][0]
        self.assertEqual([e['id'] for e in first['events']],['near'])
        np.testing.assert_allclose(first['points'],second['points'])
        np.testing.assert_allclose(first['points'][-1],[80,150,20],atol=1e-9)

    def test_moving_a_mirror_does_not_reconnect_beam(self):
        c=simple(element('mirror_b','m',x_mm=80,y_mm=60))
        self.assertEqual(len(simulate(c)['chiefs'][0]['events']),1)
        c['elements'][1]['y_mm']+=30
        self.assertEqual(len(simulate(c)['chiefs'][0]['events']),0)

    def test_3d_reflection_and_top_boundary(self):
        c=simple(element('mirror_b','m',x_mm=80,y_mm=60,elevation_deg=-45))
        chief=simulate(c)['chiefs'][0]
        np.testing.assert_allclose(chief['events'][0]['outgoing_direction'],[0,0,1],atol=1e-10)
        np.testing.assert_allclose(chief['points'][-1],[80,60,100],atol=1e-9)

    def test_aperture_blank_stops_beam(self):
        c=simple(element('mirror_b','m',x_mm=80,y_mm=65,diameter_mm=16,clear_diameter_mm=4))
        chief=simulate(c)['chiefs'][0]
        self.assertEqual(chief['status'],'Blocked by optic blank')
        self.assertEqual(chief['throughput'],0)

    def test_cut_edge_miss_and_roll(self):
        e=element('mirror_c','c',x_mm=80,y_mm=60,z_mm=17,upper_edge_mm=1.8)
        c=simple(e)
        self.assertEqual(len(simulate(c)['chiefs'][0]['events']),0)
        e['roll_deg']=180
        self.assertEqual(len(simulate(c)['chiefs'][0]['events']),1)

    def test_grating_equation_and_invalid_order(self):
        e=element('grating','g',x_mm=100,y_mm=60,lines_per_mm=500,order=1)
        chief=simulate(simple(e))['chiefs'][0]
        d=chief['events'][0]['outgoing_direction']
        self.assertAlmostEqual(d[1],.4,12)
        self.assertLess(d[0],0)
        e['lines_per_mm']=1400
        chief=simulate(simple(e))['chiefs'][0]
        self.assertEqual(chief['status'],'No propagating grating order')
        self.assertEqual(chief['throughput'],0)

    def test_thin_lens_focus(self):
        e=element('lens','l',x_mm=100,y_mm=60,model='thin',focal_length_mm=75)
        s=WorkSurface(e); c=simple(e)
        r=trace([20,61,20],[1,0,0],800,[s],c)
        out=np.array(r['events'][0]['outgoing_direction']); hit=np.array(r['events'][0]['point'])
        np.testing.assert_allclose(hit+out*(75/out[0]),[175,60,20],atol=1e-10)

    def test_thin_lens_custom_aperture_ignores_doublet_radii(self):
        c=simple(element('lens','l',x_mm=100,y_mm=60,model='thin',diameter_mm=200,clear_diameter_mm=180))
        self.assertEqual(simulate(c)['chiefs'][0]['status'],'Reached bench boundary')

    def test_doublet_matches_established_solver(self):
        e=element('lens','l',x_mm=100,y_mm=60,z_mm=20,azimuth_deg=14,elevation_deg=8,roll_deg=31)
        s=WorkSurface(e); q=s.centre-30*s.normal+.8*s.u; d=s.normal
        found=s.intersect(q,d); q2,d2,hits,failure=s.advance_lens(found[0],d,880)
        old=trace_doublet(q,d,880,s)
        self.assertIsNone(failure); self.assertEqual(len(hits),3)
        np.testing.assert_allclose(q2,old['point'],atol=1e-9)
        np.testing.assert_allclose(d2,old['direction'],atol=1e-10)
        # Reverse direction through the same physical surfaces.
        start=q2+20*d2; found=s.intersect(start,-d2)
        back,back_d,_,failure=s.advance_lens(found[0],-d2,880)
        self.assertIsNone(failure); np.testing.assert_allclose(back_d,-d,atol=1e-9)
        np.testing.assert_allclose(back,old['surfaces'][0]['point'],atol=1e-8)

    def test_custom_prescription_changes_refraction(self):
        a=element('lens','l',x_mm=100,y_mm=60); b=copy.deepcopy(a)
        b.update(glass1='constant',glass2='constant',n1=1.4,n2=1.5,r1_mm=60)
        directions=[]
        for e in (a,b):
            c=simple(e); checked(c); s=WorkSurface(e); q=np.array([20,61,20]); d=np.array([1.,0,0])
            found=s.intersect(q,d); _,out,_,failure=s.advance_lens(found[0],d,800)
            self.assertIsNone(failure); directions.append(out)
        self.assertGreater(np.linalg.norm(directions[0]-directions[1]),.001)

    def test_lens_boundary_is_not_overshot(self):
        e=element('lens','l',x_mm=300,y_mm=60)
        chief=simulate(simple(e))['chiefs'][0]
        self.assertEqual(chief['status'],'Reached bench boundary')
        self.assertAlmostEqual(chief['points'][-1][0],300)
        self.assertTrue(all(p[0]<=300+1e-8 for p in chief['points']))
        self.assertTrue(all(h['point'][0]<=300+1e-8 for h in chief['events'][0]['lens_surfaces']))
        self.assertEqual(len(chief['events'][0]['lens_surfaces']),1)

    def test_loop_terminates(self):
        c=simple(element('mirror_b','a',x_mm=100,y_mm=60),element('mirror_b','b',x_mm=10,y_mm=60))
        c['max_interactions']=8
        chief=simulate(c)['chiefs'][0]
        self.assertEqual(chief['status'],'Interaction limit reached')
        self.assertEqual(len(chief['events']),8)

    def test_spectral_power_is_normalized(self):
        c=simple(); c['elements'][0].update(bandwidth_nm=20,rays=9,wavelength_samples=5,divergence_mrad=1)
        r=simulate(c)
        self.assertEqual(r['metrics']['sampled_rays'],45)
        self.assertAlmostEqual(r['metrics']['boundary_power_mw'],10,10)
        wavelengths={ray['wavelength_nm'] for ray in r['rays']}
        self.assertEqual(len(wavelengths),5)
        mean=sum(ray['weight']*ray['wavelength_nm'] for ray in r['rays'])
        variance=sum(ray['weight']*(ray['wavelength_nm']-mean)**2 for ray in r['rays'])
        self.assertAlmostEqual(mean,800,10)
        self.assertAlmostEqual(variance,(20/2.355)**2,8)

    def test_invalid_configuration_rejected(self):
        cases=[]
        c=simple(); c['bench']['width_mm']=0; cases.append(c)
        c=simple(); c['elements'][0]['azimuth_deg']=float('nan'); cases.append(c)
        c=simple(); c['elements'][0]['x_mm']=-1; cases.append(c)
        c=simple(); c['elements'][0]['rays']=1.5; cases.append(c)
        c=simple(element('lens','l')); c['elements'][1]['clear_diameter_mm']=30; cases.append(c)
        c=simple(element('lens','l')); c['elements'][1]['t1_mm']=.01; cases.append(c)
        c=simple(); c['elements'].append(copy.deepcopy(c['elements'][0])); cases.append(c)
        for c in cases:
            with self.subTest(config=c),self.assertRaises(ValueError): checked(c)


if __name__=='__main__': unittest.main()
