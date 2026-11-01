"""Semantic tests for the procedural tree definition and placement rules."""
import copy
import importlib.util
from pathlib import Path
import sys
import unittest

FILE=Path(__file__).resolve().parents[1]/'tools/tree_art.py'
spec=importlib.util.spec_from_file_location('tree_art',FILE)
art=importlib.util.module_from_spec(spec)
sys.modules[spec.name]=art
spec.loader.exec_module(art)

class TreeArtTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.definition=art.load_definition(art.DEFAULT_DEFINITION)

    def test_repeatable_identity_and_independent_material_edits(self):
        a=art.construct(self.definition,42)
        self.assertEqual(a,art.construct(self.definition,42))
        recolored=copy.deepcopy(self.definition)
        recolored['paper']['stocks'][0]['face']='aabbcc'
        self.assertEqual(a,art.construct(recolored,42))
        # Even adding a trait sampling stream must not change existing streams.
        reordered=copy.deepcopy(self.definition)
        reordered['variation']=dict(reversed(list(reordered['variation'].items())))
        self.assertEqual(a.traits,art.sample_traits(reordered,42))

    def test_age_changes_related_dimensions_together(self):
        young=dict(age=.15,vigour=.65,exposure=.2,gesture=0)
        old=dict(young,age=.9)
        a=art.construct(self.definition,1,young)
        b=art.construct(self.definition,1,old)
        self.assertGreater(b.height,a.height)
        self.assertLess(b.width_ratio,a.width_ratio)
        self.assertGreater(b.trunk_ratio,a.trunk_ratio)
        self.assertGreater(len(b.tiers),len(a.tiers))
        self.assertGreater(b.clearance,a.clearance)

    def test_selected_individuals_obey_constraints_and_have_distinct_forms(self):
        trees=art.select_variations(self.definition)
        self.assertTrue(all(not t.violations for t in trees))
        self.assertEqual(len({t.seed for t in trees}),6)
        self.assertGreater(max(t.height for t in trees)-min(t.height for t in trees),40)
        self.assertGreater(max(t.width_ratio for t in trees)-min(t.width_ratio for t in trees),.06)
        self.assertGreater(len({len(t.tiers) for t in trees}),1)

    def test_placement_preserves_opening_spacing_and_replay(self):
        a,report=art.place_grove(self.definition)
        b,_=art.place_grove(self.definition)
        self.assertEqual(a,b)
        self.assertEqual(len(a),self.definition['placement']['count'])
        for i,candidate in enumerate(a):
            self.assertEqual(art.placement_violations(self.definition['placement'],candidate,a[:i]),[])
        self.assertGreater(max(p.scale for p in a)-min(p.scale for p in a),.5)
        self.assertIn('protected_opening',report['rejected'])

    def test_aesthetic_weights_change_selection_without_changing_construction(self):
        alternative=copy.deepcopy(self.definition)
        alternative['placement']['preferences']['near_tangency']=30
        before,_=art.place_grove(self.definition)
        after,_=art.place_grove(alternative)
        self.assertNotEqual([(p.x,p.y)for p in before],[(p.x,p.y)for p in after])
        self.assertEqual(art.construct(self.definition,42),art.construct(alternative,42))
        for i,candidate in enumerate(after):
            self.assertEqual(art.placement_violations(alternative['placement'],candidate,after[:i]),[])

    def test_complete_foreground_trees_occlude_background_assemblies(self):
        placements,_=art.place_grove(self.definition)
        scene=art.grove_scene(self.definition,placements)
        groups=[n for n in scene['nodes']if 'children'in n]
        intervals=[(min(p['z']for p in n['children']),max(p['z']for p in n['children']))for n in groups]
        for back,front in zip(intervals,intervals[1:]):
            self.assertLess(back[1],front[0])
        self.assertLess(intervals[-1][1],48)

if __name__=='__main__':unittest.main()
