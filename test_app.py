"""Local HTTP, serialization and layout-import checks."""
import json
import re
import threading
import unittest
import tempfile
from pathlib import Path
from unittest.mock import patch
from http.server import ThreadingHTTPServer
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from app import Handler, TOKEN, ROOT
from model import default_config, folded_config, checked


class AppTests(unittest.TestCase):
    def setUp(self):
        directory=tempfile.TemporaryDirectory(); self.addCleanup(directory.cleanup)
        self.product_path=Path(directory.name)/'products.json'
        replacement=patch('products.PRODUCT_FILE',self.product_path); replacement.start(); self.addCleanup(replacement.stop)
        replacement=patch('materials.MATERIAL_FILE',Path(directory.name)/'materials.json'); replacement.start(); self.addCleanup(replacement.stop)

    @classmethod
    def setUpClass(cls):
        cls.server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
        cls.url=f'http://127.0.0.1:{cls.server.server_address[1]}'
        cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown(); cls.server.server_close(); cls.thread.join(3)

    def request(self,path,config=None,token=TOKEN):
        req=Request(self.url+path,data=json.dumps({'config':config}).encode() if config is not None else None,
                    headers={'Content-Type':'application/json','X-Optics-Token':token})
        with urlopen(req,timeout=10) as response: return response.status,response.read().decode()

    def test_page_and_assets(self):
        status,html=self.request('/')
        self.assertEqual(status,200); self.assertIn('window.BOOT=',html); self.assertNotIn('/*BOOTSTRAP*/',html)
        assets=re.findall(r'(?:src|href)="(/[^"?]+\.(?:js|css))"',html)
        self.assertIn('/analyses.js',assets)
        for asset in assets:
            with self.subTest(asset=asset):
                ROOT.joinpath(asset.lstrip('/')).read_text(encoding='utf-8')
                self.assertEqual(self.request(asset)[0],200)
        for path in ['/lens_geometry.js','/lens_visuals.js','/pointer_tools.js','/workspace.css','/learning_examples.js','/layout_geometry.js','/layout_tools.js','/workbench.js','/products.js','/lens_editor.js','/focusviz.js','/spectral.js','/pulseviz.js','/analyses.js','/style.css','/product-style.css','/analysis-style.css','/api/health','/api/materials']:
            self.assertEqual(self.request(path)[0],200)

    def test_simulation_response_serializes_paths(self):
        status,payload=self.request('/api/simulate',folded_config())
        data=json.loads(payload)
        self.assertEqual(status,200)
        self.assertEqual(data['chiefs'][0]['status'],'Reached bench boundary')
        self.assertAlmostEqual(data['metrics']['boundary_power_mw'],9.65447505,10)
        self.assertEqual(len(data['chiefs'][0]['events']),4)

    def test_saved_examples_validate_and_recompute(self):
        for path in (ROOT/'examples').glob('*.json'):
            with self.subTest(example=path.name):
                original=json.loads(path.read_text(encoding='utf-8'))
                validated=json.loads(self.request('/api/validate',original)[1])['config']
                self.assertEqual(checked(original),validated)
                for before,after in zip(original['elements'],validated['elements']):
                    for key,value in before.items(): self.assertEqual(value,after[key])
                self.assertEqual(self.request('/api/simulate',validated)[0],200)

    def test_component_locks_survive_layout_import_and_simulation(self):
        config=folded_config(); config['elements'][0]['locked']=True
        validated=json.loads(self.request('/api/validate',config)[1])['config']
        self.assertTrue(validated['elements'][0]['locked'])
        self.assertFalse(validated['elements'][1]['locked'])
        data=json.loads(self.request('/api/simulate',validated)[1])
        self.assertAlmostEqual(data['metrics']['boundary_power_mw'],9.65447505,10)
        config['elements'][0]['locked']='false'
        with self.assertRaises(HTTPError) as err:self.request('/api/validate',config)
        self.assertEqual(err.exception.code,400)

    def test_bad_input_and_unauthorized_calls(self):
        with self.assertRaises(HTTPError) as err: self.request('/api/simulate',default_config(),token='incorrect')
        self.assertEqual(err.exception.code,403)
        with self.assertRaises(HTTPError) as err: self.request('/api/validate',{'format':'old-gvd-format'})
        self.assertEqual(err.exception.code,400)

    def test_product_api_save_and_read(self):
        initial=json.loads(self.request('/api/products')[1])['products']
        generic=next(p for p in initial if p['id']=='template-lens')
        generic['id']=None; generic['name']='My custom n=1.45 lens'; generic['properties']['n1']=1.45
        req=Request(self.url+'/api/products/save',data=json.dumps({'product':generic}).encode(),
                    headers={'Content-Type':'application/json','X-Optics-Token':TOKEN})
        with urlopen(req,timeout=10) as response: saved=json.loads(response.read())['product']
        self.assertFalse(saved['builtin']); self.assertTrue(self.product_path.exists())
        listed=json.loads(self.request('/api/products')[1])['products']
        self.assertEqual(next(p for p in listed if p['id']==saved['id'])['properties']['n1'],1.45)

    def test_analysis_endpoints_and_finite_json(self):
        from test_analysis import straight
        c=straight(20); c['analysis']['field_grid']=64
        for endpoint in ('sensitivity','field','pulse','focus','field-convergence','pulse-convergence'):
            with self.subTest(endpoint=endpoint):
                body=dict(config=c,source_id='s',target_id='t',visit=1,element_id='s')
                req=Request(self.url+'/api/'+endpoint,data=json.dumps(body).encode(),headers={'Content-Type':'application/json','X-Optics-Token':TOKEN})
                with urlopen(req,timeout=30) as response:
                    r=json.loads(response.read()); self.assertEqual(response.status,200)
                    json.dumps(r,allow_nan=False)
        bad=dict(config=c,source_id='s',target_id='t',visit=1.5)
        req=Request(self.url+'/api/field',data=json.dumps(bad).encode(),headers={'Content-Type':'application/json','X-Optics-Token':TOKEN})
        with self.assertRaises(HTTPError) as err: urlopen(req)
        self.assertEqual(err.exception.code,400)

    def test_material_api_saves_custom_dispersion(self):
        material=dict(name='Measured test glass',model='table',min_nm=700,max_nm=900,table=[[700,1.52],[800,1.51],[900,1.50]])
        req=Request(self.url+'/api/materials/save',data=json.dumps({'material':material}).encode(),headers={'Content-Type':'application/json','X-Optics-Token':TOKEN})
        with urlopen(req,timeout=10) as response: saved=json.loads(response.read())['material']
        items=json.loads(self.request('/api/materials')[1])['materials']
        self.assertEqual(next(m for m in items if m['id']==saved['id'])['table'],material['table'])
        material['table']=[[800,1.5],[700,1.4]]
        req=Request(self.url+'/api/materials/save',data=json.dumps({'material':material}).encode(),headers={'Content-Type':'application/json','X-Optics-Token':TOKEN})
        with self.assertRaises(HTTPError) as err: urlopen(req)
        self.assertEqual(err.exception.code,400)

    def test_learning_example_loader(self):
        for key in ('complex_dispersion','complex_telescope','complex_3d_alignment'):
            status,payload=self.request('/api/examples/'+key)
            c=json.loads(payload)['config']
            self.assertEqual(status,200);self.assertEqual(c,checked(c));self.assertIn('learning_notes',c)
        with self.assertRaises(HTTPError) as err:self.request('/api/examples/unknown')
        self.assertEqual(err.exception.code,404)


if __name__=='__main__': unittest.main()
