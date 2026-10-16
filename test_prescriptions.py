"""Independent lens/material/focus checks, including persistence and search bounds."""
import copy
import json
import tempfile
import unittest
from pathlib import Path
import numpy as np
from model import element, checked, default_config, WorkSurface, unit, simulate
from materials import builtins, material_index, validate_material, save_material, list_materials
from prescriptions import doublet_surfaces
from products import builtins as products, save_product, list_products
from waveoptics import lens_abcd, compute_field
from pulses import pulse_analysis
from focus import focus_analysis

MATS={m['id']:m for m in builtins()}


def singlet():
    return element('lens','l',x_mm=100,y_mm=75,model='prescription',surfaces=[
        dict(radius_mm=50.,thickness_mm=5.,clear_diameter_mm=24.,material_after=copy.deepcopy(MATS['constant-150'])),
        dict(radius_mm=-50.,thickness_mm=0.,clear_diameter_mm=24.,material_after=copy.deepcopy(MATS['air']))])


def bench(lens=None):
    c=default_config(); c['elements']=[element('laser','s',x_mm=20,y_mm=75,wavelength_nm=780,bandwidth_nm=10,wavelength_samples=5,rays=65,beam_radius_mm=.5),lens or singlet()]
    return c


class PrescriptionTests(unittest.TestCase):
    def test_material_formula_table_range_and_rejected_poles(self):
        from doublet import glass_index
        for glass in ('N-LAK22','N-SF6'):
            wl=np.array([760.,780.,880.]); np.testing.assert_allclose(material_index(MATS[glass],wl),glass_index(glass,wl),rtol=1e-14)
        table=validate_material(dict(name='Measured',model='table',min_nm=700,max_nm=900,table=[[700,1.52],[800,1.51],[900,1.50]]))
        self.assertAlmostEqual(float(material_index(table,750)),1.515)
        with self.assertRaisesRegex(ValueError,'extrapolation'): material_index(table,901)
        for patch in [dict(table=[[800,1.5],[700,1.4]]),dict(max_nm=1000)]:
            with self.assertRaises(ValueError): validate_material({**table,**patch})
        pole={**MATS['N-LAK22'],'C':[.6,2,100]}
        with self.assertRaisesRegex(ValueError,'pole'): validate_material(pole)

    def test_material_persistence_updates_and_portable_snapshots(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'materials.json'; draft=copy.deepcopy(MATS['N-LAK22']); draft['id']=None; draft['name']='My glass'
            saved=save_material(draft,path)['material']; lens=singlet(); lens['surfaces'][0]['material_after']=copy.deepcopy(saved)
            before=material_index(lens['surfaces'][0]['material_after'],780)
            saved['B'][0]+=.1; save_material(saved,path)
            self.assertNotEqual(float(material_index(list_materials(path)[-1],780)),float(before))
            self.assertEqual(float(material_index(lens['surfaces'][0]['material_after'],780)),float(before))
            with self.assertRaises(ValueError): save_material(MATS['N-LAK22'],path)
            path.write_text('{bad',encoding='utf-8')
            with self.assertRaises(ValueError): list_materials(path)
            self.assertEqual(path.read_text(),'{bad')

    def test_prescription_matches_legacy_doublet_and_reverse_snell(self):
        old=element('lens','l'); new=copy.deepcopy(old); new.update(model='prescription',surfaces=doublet_surfaces(old))
        for flipped in (False,True):
            old['flipped']=new['flipped']=flipped
            for wl in (760,780,880):
                outputs=[]
                for lens in (old,new):
                    s=WorkSurface(lens); d=unit([1,.02,.01]); p=s.centre+np.array([-30,1,1]); hit=s.intersect(p,d)
                    q,out,hits,error=s.advance_lens(hit[0],d,wl); self.assertIsNone(error); outputs.append((q,out))
                    for h in hits:
                        n=np.array(h['normal']); a=np.array(h['incoming_direction']); b=np.array(h['outgoing_direction'])
                        np.testing.assert_allclose(h['n_before']*(a-n*(a@n)),h['n_after']*(b-n*(b@n)),atol=1e-12)
                    reverse=s.intersect(q+30*out,-out); back,bd,_,error=s.advance_lens(reverse[0],-out,wl)
                    self.assertIsNone(error); np.testing.assert_allclose(bd,-d,atol=1e-10)
                    np.testing.assert_allclose(back,hit[0],atol=1e-8)
                np.testing.assert_allclose(outputs[0],outputs[1],atol=1e-12)

    def test_planar_plate_oblique_snell_and_optical_path(self):
        lens=singlet()
        for row in lens['surfaces']: row['radius_mm']=0
        s=WorkSurface(lens); d=unit([1,.2,.07]); hit=s.intersect(np.array([20,75,20.]),d)
        # Use an on-aperture entry with nonzero incidence.
        point=s.vertices[0].copy(); q,out,hits,error=s.advance_lens(point,d,780)
        self.assertIsNone(error); np.testing.assert_allclose(out,d,atol=1e-12)
        inside=np.array(hits[0]['outgoing_direction']); self.assertAlmostEqual(float(inside[1]),float(d[1]/1.5),12)
        self.assertAlmostEqual(np.linalg.norm(q-point),5/inside[0],10)
        m=lens_abcd(singlet(),780)
        # Thick lensmaker formula for n=1.5, R1=50, R2=-50, t=5.
        power=.5*(1/50-1/-50+.5*5/(1.5*50*-50))
        self.assertAlmostEqual(m['focal_length_mm'],1/power,delta=1e-5)

    def test_air_spaced_assembly_four_surfaces_and_aperture(self):
        lens=singlet(); a,b=copy.deepcopy(lens['surfaces']); b['thickness_mm']=10
        lens['surfaces']=[a,b,copy.deepcopy(a),copy.deepcopy(lens['surfaces'][-1])]
        c=bench(lens); checked(c); r=simulate(c); hits=r['chiefs'][0]['events'][0]['lens_surfaces']
        self.assertEqual(len(hits),4); self.assertEqual([h['n_before'] for h in hits],[1,1.5,1,1.5])
        self.assertEqual([h['n_after'] for h in hits],[1.5,1,1.5,1])
        lens=singlet(); lens['surfaces'][1]['clear_diameter_mm']=.1
        s=WorkSurface(lens); p=s.vertices[0]+np.array([0,1,0]); _,_,hits,error=s.advance_lens(p,np.array([1.,0,0]),780)
        self.assertEqual(error,'Clipped inside lens'); self.assertLess(hits[-1]['margin_mm'],0)

    def test_invalid_prescriptions_and_product_roundtrip(self):
        c=bench()
        for mutate in (lambda e:e.update(surfaces=[]),lambda e:e['surfaces'][0].update(radius_mm=2),
                       lambda e:e['surfaces'][0].update(thickness_mm=0),lambda e:e['surfaces'][-1].update(thickness_mm=5),
                       lambda e:e['surfaces'][-1].update(material_after=MATS['constant-150'])):
            bad=copy.deepcopy(c); mutate(bad['elements'][1])
            with self.assertRaises(ValueError): checked(bad)
        crossing=copy.deepcopy(c); crossing['elements'][1]['surfaces'][0].update(radius_mm=15,thickness_mm=.1)
        with self.assertRaisesRegex(ValueError,'cross'): checked(crossing)
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'products.json'; draft=copy.deepcopy(next(p for p in products() if p['id']=='template-prescription-lens')); draft['id']=None
            save_product(draft,path); restored=list_products(path)[-1]
            self.assertEqual(restored['properties']['surfaces'],draft['properties']['surfaces'])

    def test_general_prescription_field_and_material_gdd(self):
        from test_analysis import straight
        c=straight(180); e=element('lens','l',x_mm=100,y_mm=75); e.update(model='prescription',surfaces=doublet_surfaces(e)); c['elements'].insert(1,e)
        c['analysis'].update(field_grid=64,field_span_mm=4)
        r=compute_field(c,'s','t'); self.assertGreater(r['power_mw'],0)
        pulse=pulse_analysis(c,'s','t'); self.assertGreater(pulse['optical_gdd_fs2'],0)
        json.dumps(pulse,allow_nan=False)


class FocusTests(unittest.TestCase):
    def test_thin_lens_focus_and_all_samples_retained(self):
        c=bench(element('lens','l',x_mm=100,y_mm=75,model='thin',focal_length_mm=50))
        c['elements'][0].update(rays=257,wavelength_samples=5)
        r=focus_analysis(c,'s','l'); self.assertEqual(r['combined']['ray_count'],1285)
        self.assertAlmostEqual(r['combined']['distance_mm'],50,delta=.0001)
        self.assertLess(r['combined']['rms_radius_mm'],1e-7); self.assertFalse(r['combined']['boundary_limited'])
        self.assertAlmostEqual(r['chromatic_focal_shift_mm'],0,delta=1e-9)

    def test_spherical_focus_chromatic_shift_and_combined_curve(self):
        c=bench(); c['elements'][1]['surfaces'][0]['material_after']=copy.deepcopy(MATS['N-SF6'])
        r=focus_analysis(c,'s','l'); self.assertGreater(r['chromatic_focal_shift_mm'],.01)
        # Combined spot cannot be smaller than the power-weighted per-colour minimum variances.
        floor=sum(row['power_mw']*row['rms_radius_mm']**2 for row in r['wavelengths'])/r['surviving_power_mw']
        self.assertGreaterEqual(r['combined']['rms_radius_mm']**2+1e-14,floor)
        self.assertFalse(r['combined']['boundary_limited']); json.dumps(r,allow_nan=False)

    def test_focus_bounds_next_optic_and_divergence(self):
        c=bench(element('lens','l',x_mm=100,y_mm=75,model='thin',focal_length_mm=80))
        c['elements'].append(element('mirror_e','m',x_mm=120,y_mm=75))
        r=focus_analysis(c,'s','l'); self.assertLessEqual(r['search_interval_mm'][1],20)
        self.assertTrue(r['combined']['boundary_limited']); self.assertTrue(r['warnings'])
        c['elements']=c['elements'][:2]; c['elements'][1]['focal_length_mm']=-80
        r=focus_analysis(c,'s','l'); self.assertTrue(r['combined']['boundary_limited']); self.assertAlmostEqual(r['combined']['distance_mm'],r['search_interval_mm'][0])
        c['elements'][0]['rays']=1
        r=focus_analysis(c,'s','l'); self.assertFalse(r['combined']['resolved'])


if __name__=='__main__': unittest.main()
