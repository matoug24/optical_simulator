"""Stored teaching layouts must have working routes and meaningful diagnostics."""
import json
from pathlib import Path
import unittest
import numpy as np
from model import checked, simulate
from focus import focus_analysis
from pulses import pulse_analysis


class LearningExampleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.configs={key:checked(json.loads((Path(__file__).parent/'examples'/(key+'.json')).read_text(encoding='utf-8'))) for key in
                     ('complex_dispersion','complex_telescope','complex_3d_alignment')}
        cls.results={key:simulate(c) for key,c in cls.configs.items()}

    def test_all_intended_routes_and_surviving_power(self):
        for key,c in self.configs.items():
            with self.subTest(example=key):
                r=self.results[key];chief=r['chiefs'][0]
                self.assertGreaterEqual(len(c['elements']),8)
                self.assertEqual([e['id'] for e in chief['events']],[e['id'] for e in c['elements'] if e['type']!='laser'])
                self.assertEqual(chief['status'],'Reached bench boundary')
                self.assertGreater(r['metrics']['boundary_power_mw'],35)
                self.assertEqual(len(r['spectral_chiefs']),7)
                self.assertGreaterEqual(len(c['learning_notes']['experiments']),4)
                json.dumps(r,allow_nan=False)

    def test_telescope_expands_actual_finite_ray_bundle(self):
        rays=[r for r in self.results['complex_telescope']['rays'] if abs(r['wavelength_nm']-780)<1e-8]
        before=np.array([r['points'][0][1:] for r in rays])
        after=np.array([next(e for e in r['events'] if e['id']=='telescope-2')['exit_point'][1:] for r in rays])
        ratio=np.sqrt(np.var(after,axis=0).sum()/np.var(before,axis=0).sum())
        self.assertAlmostEqual(ratio,2,delta=.01)
        event=next(e for e in self.results['complex_telescope']['chiefs'][0]['events'] if e['id']=='focusing-assembly')
        self.assertEqual(len(event['lens_surfaces']),4)
        self.assertEqual(event['lens_surfaces'][2]['n_before'],1.)

    def test_3d_path_reaches_three_distinct_heights(self):
        events=self.results['complex_3d_alignment']['chiefs'][0]['events'];heights={e['id']:e['point'][2] for e in events}
        self.assertAlmostEqual(heights['rise-fold'],25,places=8)
        self.assertAlmostEqual(heights['high-fold'],90,places=8)
        self.assertAlmostEqual(heights['descent-fold'],90,places=8)
        self.assertAlmostEqual(heights['low-fold'],35,places=8)
        self.assertAlmostEqual(heights['exit-fold'],35,places=8)

    def test_examples_have_interior_focus_and_a_finite_pulse(self):
        targets={'complex_dispersion':'final-lens','complex_telescope':'focusing-assembly','complex_3d_alignment':'return-lens'}
        for key,target in targets.items():
            with self.subTest(example=key):
                r=focus_analysis(self.configs[key],'source',target)
                self.assertFalse(r['combined']['boundary_limited']);self.assertTrue(r['combined']['resolved'])
                self.assertGreater(r['combined']['distance_mm'],1)
        r=pulse_analysis(self.configs['complex_dispersion'],'source','glass-plate')
        self.assertGreater(r['input_fwhm_fs'],0);self.assertGreater(r['output_fwhm_fs'],0)
        self.assertGreater(abs(r['optical_gdd_fs2']),100)
        json.dumps(r,allow_nan=False)


if __name__=='__main__':unittest.main()
