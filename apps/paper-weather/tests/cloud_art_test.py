"""Cloud morphology/compatibility invariants; visual quality is reviewed separately."""
import importlib.util
from pathlib import Path
import sys
import unittest
import json
from dataclasses import replace

TOOLS=Path(__file__).resolve().parents[1]/'tools'
sys.path.insert(0,str(TOOLS))
import cloud_art as art

class CloudArtTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.presets=art.presets()

    def test_complete_named_taxonomy_and_all_common_genus_species_forms(self):
        t=art.TAXONOMY
        self.assertEqual(len(t['genera']),10)
        self.assertEqual(len(set(s for g in t['genera'].values()for s in g['species'])),15)
        self.assertEqual(len(t['varieties']),9)
        self.assertEqual(len(t['features']),11)
        self.assertEqual(len(t['accessories']),4)
        self.assertEqual(len(self.presets['species']),31) # includes As/Ns with no species
        self.assertEqual({c.upper for c in self.presets['upper']},set(t['upper']))

    def test_all_presets_build_closed_native_documents_within_real_wire_budget(self):
        for category,specs in self.presets.items():
            for spec in specs:
                with self.subTest(category=category,cloud=spec.label):
                    art.validate(spec)
                    document,report=art.document(spec)
                    self.assertLessEqual(len(json.dumps(document,separators=(',',':')).encode()),1048576)
                    self.assertGreater(report['pieces'],0)
                    self.assertLessEqual(report['pieces'],180)
                    for item in document['nodes'][1]['children']:
                        self.assertEqual(item['path'][0][0],'M')
                        self.assertEqual(item['path'][-1][0],'Z')
                        self.assertTrue(30<=item['z']<=30.5)

    def test_invalid_classification_and_explicit_grammar_limits_are_rejected(self):
        invalid=[art.Cloud('cumulus','capillatus'),art.Cloud('cirrus','lenticularis'),
                 art.Cloud('altostratus','humilis'),art.Cloud('cumulonimbus','calvus',varieties=('radiatus',)),
                 art.Cloud('cumulus','humilis',features=('incus',)),
                 art.Cloud('cirrus','fibratus',accessories=('pileus',)),
                 art.Cloud('cumulonimbus','capillatus',features=('cauda',)),
                 art.Cloud('altostratus',varieties=('opacus','translucidus')),
                 art.Cloud('altocumulus','stratiformis',features=('cavum','asperitas')),
                 art.Cloud('altostratus',halo=True),art.Cloud('upper',upper='noctilucent',species='fibratus')]
        for spec in invalid:
            with self.subTest(spec=spec),self.assertRaises(ValueError):art.validate(spec)

    def test_relative_cloudlet_scale_and_high_cloud_shading_signature(self):
        widths=[]
        for genus in ('cirrocumulus','altocumulus','stratocumulus'):
            builder=art.Builder(art.Cloud(genus,'stratiformis'));builder.build()
            widths.append(sum(builder.metrics['cloudlet_widths'])/len(builder.metrics['cloudlet_widths']))
            if genus=='cirrocumulus':
                self.assertFalse(builder.metrics['intrinsic_shading'])
                self.assertFalse(any(n['material'] in ('under','shade','dark','storm')for n in builder.nodes))
        self.assertLess(widths[0],widths[1]*.6)
        self.assertLess(widths[1],widths[2]*.65)

    def test_convective_growth_and_ice_crown_are_structural_changes(self):
        heights=[]
        for species in ('humilis','mediocris','congestus'):
            builder=art.Builder(art.Cloud('cumulus',species));nodes=builder.build()
            ys=[c[i]for n in nodes for c in n['path']for i in range(2,len(c),2)]
            heights.append(max(ys)-min(ys))
        self.assertLess(heights[0],heights[1]);self.assertLess(heights[1],heights[2])
        calvus=art.Builder(art.Cloud('cumulonimbus','calvus'));calvus.build()
        capillatus=art.Builder(art.Cloud('cumulonimbus','capillatus'));capillatus.build()
        self.assertFalse(any('filament' in n['id']for n in calvus.nodes))
        self.assertTrue(any('filament' in n['id']for n in capillatus.nodes))
        self.assertTrue(any('continuous-updraft' in n['id']for n in capillatus.nodes))

    def test_seed_replay_and_variation_exist_for_every_genus_and_upper_case(self):
        for specs in (self.presets['genera'],self.presets['upper']):
            for spec in specs:
                with self.subTest(spec=spec.label):
                    a=art.Builder(spec).build()
                    self.assertEqual(a,art.Builder(spec).build())
                    self.assertNotEqual(a,art.Builder(replace(spec,seed=spec.seed+1)).build())

    def test_apertures_are_real_subpaths_and_features_compose_in_either_order(self):
        a=art.Builder(art.Cloud('altocumulus','stratiformis',features=('virga','cavum'))).build()
        b=art.Builder(art.Cloud('altocumulus','stratiformis',features=('cavum','virga'))).build()
        self.assertEqual(a,b)
        holes=[n for n in a if 'perforated' in n['id']]
        self.assertEqual(len(holes),1)
        self.assertEqual(sum(c[0]=='M'for c in holes[0]['path']),2)
        self.assertTrue(any('evaporating-fallstreak' in n['id']for n in a))
        layer=art.Builder(art.Cloud('cirrocumulus','stratiformis',varieties=('lacunosus',))).build()
        self.assertGreater(sum(c[0]=='M'for n in layer for c in n['path']),10)

    def test_typed_data_specs_and_independent_layer_operators(self):
        spec=art.from_mapping({'genus':'altocumulus','species':'stratiformis',
                               'features':['cavum','virga'],'varieties':['duplicatus'],'seed':42})
        nodes=art.Builder(spec).build()
        self.assertTrue(any('second-layer' in n['id']for n in nodes))
        self.assertTrue(any('evaporating-fallstreak' in n['id']for n in nodes))
        for bad in [{'genus':'cirrus','image':'photo.png'}, {'genus':'cirrus','seed':True},
                    {'genus':'cirrus','features':'mamma'}, {'genus':'cirrostratus','halo':1}]:
            with self.subTest(bad=bad),self.assertRaises(ValueError):art.from_mapping(bad)
        for spec in [art.Cloud('cirrus','fibratus',varieties=('intortus','vertebratus')),
                     art.Cloud('altocumulus','stratiformis',varieties=('radiatus',),features=('cavum',))]:
            with self.assertRaises(ValueError):art.validate(spec)

    def test_complete_geometry_and_control_hulls_fit_the_study_frame(self):
        for specs in self.presets.values():
            for spec in specs:
                with self.subTest(spec=spec.label):
                    nodes=art.Builder(spec).build()
                    for n in nodes:
                        for c in n['path']:
                            for i in range(1,len(c),2):
                                self.assertGreaterEqual(c[i],-1e-6);self.assertLessEqual(c[i],1000+1e-6)
                                self.assertGreaterEqual(c[i+1],5-1e-6);self.assertLessEqual(c[i+1],455+1e-6)

if __name__=='__main__':unittest.main()
