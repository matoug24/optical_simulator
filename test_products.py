import copy
import json
import tempfile
import unittest
from pathlib import Path
from products import builtins, list_products, save_product, validate_product


class ProductTests(unittest.TestCase):
    def setUp(self):
        self.directory=tempfile.TemporaryDirectory(); self.addCleanup(self.directory.cleanup)
        self.path=Path(self.directory.name)/'products.json'

    def draft(self,ident='template-lens'):
        p=next(p for p in builtins() if p['id']==ident); p['id']=None
        return p

    def test_all_defaults_are_valid_and_lenses_include_generic(self):
        for p in builtins(): validate_product(p)
        lenses=[p for p in list_products(self.path) if p['category']=='lens']
        self.assertEqual(len(lenses),4)
        self.assertEqual(next(p for p in lenses if p['id']=='template-lens')['properties']['glass1'],'constant')

    def test_calmar_reference_is_explicitly_assumed_and_savable(self):
        p=next(p for p in builtins() if p['id']=='calmar-mendocino-780-assumed')
        self.assertIn('assumed',p['name']); self.assertIn('estimates',p['assumption_note'])
        self.assertEqual(p['properties']['wavelength_nm'],780)
        self.assertEqual(p['properties']['bandwidth_nm'],5)
        self.assertEqual(p['properties']['wavelength_samples'],7)
        p['id']=None; saved=save_product(p,self.path)['product']
        self.assertEqual(saved['properties'],p['properties'])

    def test_three_lens_variants_persist_independently(self):
        for index in range(3):
            draft=self.draft(); draft['name']=f'Custom lens {index+1}'
            draft['properties']['n1']=1.4+index*.1
            save_product(draft,self.path)
        listed=list_products(self.path); custom=[p for p in listed if not p['builtin']]
        self.assertEqual(len(custom),3); self.assertEqual(len({p['id'] for p in custom}),3)
        for p,n in zip(custom,[1.4,1.5,1.6]): self.assertAlmostEqual(p['properties']['n1'],n)
        self.assertEqual(json.loads(self.path.read_text())['format'],'optics-products-v1')

    def test_laser_wavelength_and_saved_update(self):
        draft=self.draft('default-laser'); draft['name']='532 nm laser'; draft['properties']['wavelength_nm']=532
        item=save_product(draft,self.path)['product']; item['properties']['power_mw']=25
        save_product(item,self.path)
        saved=[p for p in list_products(self.path) if not p['builtin']]
        self.assertEqual(len(saved),1); self.assertEqual(saved[0]['properties']['power_mw'],25)
        self.assertEqual(saved[0]['properties']['wavelength_nm'],532)

    def test_default_cannot_be_overwritten(self):
        original=builtins()
        with self.assertRaises(ValueError): save_product(original[0],self.path)
        self.assertEqual(original,builtins()); self.assertFalse(self.path.exists())

    def test_invalid_prescription_and_position_do_not_write(self):
        draft=self.draft(); save_product(draft,self.path); before=self.path.read_bytes()
        for key,value in [('n1',.8),('diameter_mm',0),('x_mm',100)]:
            candidate=copy.deepcopy(draft); candidate['properties'][key]=value
            with self.subTest(key=key),self.assertRaises(ValueError): save_product(candidate,self.path)
        self.assertEqual(before,self.path.read_bytes())

    def test_corrupt_library_is_preserved(self):
        self.path.write_text('invalid library',encoding='utf-8')
        with self.assertRaises(ValueError): save_product(self.draft(),self.path)
        self.assertEqual(self.path.read_text(),'invalid library')

    def test_inactive_properties_cannot_store_nan(self):
        draft=self.draft('template-thin-lens'); draft['properties']['r1_mm']=float('nan')
        with self.assertRaises(ValueError): save_product(draft,self.path)
        self.assertFalse(self.path.exists())


if __name__=='__main__': unittest.main()
