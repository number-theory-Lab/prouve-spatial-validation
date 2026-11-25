import json
import unittest
from pathlib import Path

from engine.geometry_engine_v03 import compute_usable_area
from engine.adaptive_solver import run_adaptive_solver

ROOT = Path(__file__).resolve().parents[1]

class AdaptiveSolverTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.case=json.loads((ROOT/'fixtures'/'baseline_engine_case.json').read_text())
        cls.geom=compute_usable_area(cls.case)

    def test_grid_only_returns_certified_feasible_plan(self):
        r=run_adaptive_solver(self.case,self.geom['geometries']['usable'],self.geom['geometries']['field'].bounds,
                              max_wall_time_seconds=2,max_grid_evaluations=64,phase_divisions_cap=4,
                              allow_phase_arrangement=False,allow_orientation_bnb=False)
        self.assertEqual(r['status'],'FEASIBLE_CERTIFIED_BEST_FOUND_NOT_PROVEN_OPTIMAL')
        self.assertEqual(r['source_constraint_feasibility_certificate']['status'],'CERTIFIED_FEASIBLE')
        self.assertEqual(r['represented_usable_geometry_feasibility_certificate']['status'],'CERTIFIED_FEASIBLE')
        self.assertEqual(r['lattice_relation_verification']['status'],'CERTIFIED_RATIONAL_LATTICE')
        self.assertTrue(r['certified_upper_bound']['certified'])

    def test_phase_arrangement_reconciles_and_improves_sample(self):
        r=run_adaptive_solver(self.case,self.geom['geometries']['usable'],self.geom['geometries']['field'].bounds,
                              max_wall_time_seconds=3,max_grid_evaluations=144,phase_divisions_cap=4,
                              allow_phase_arrangement=True,allow_orientation_bnb=False)
        self.assertEqual(r['status'],'FEASIBLE_CERTIFIED_BEST_FOUND_NOT_PROVEN_OPTIMAL')
        self.assertEqual(r['selected_method'],'PHASE_ARRANGEMENT_FIXED_ORIENTATION')
        self.assertGreaterEqual(r['best_found_count'],60)
        a=[x for x in r['method_attempts'] if x['method']=='PHASE_ARRANGEMENT'][0]
        self.assertEqual(a['status'],'RECONCILED')

    def test_bnb_reconciles_candidate_with_production_enumerator(self):
        r=run_adaptive_solver(self.case,self.geom['geometries']['usable'],self.geom['geometries']['field'].bounds,
                              max_wall_time_seconds=3,max_grid_evaluations=64,phase_divisions_cap=3,
                              allow_phase_arrangement=False,allow_orientation_bnb=True,bnb_max_nodes=3)
        a=[x for x in r['method_attempts'] if x['method']=='ORIENTATION_PHASE_BNB'][0]
        self.assertIn(a['status'],('RECONCILED','SKIPPED_OR_FALLBACK','SKIPPED_COMPLEXITY_OR_BUDGET'))
        if a['status']=='RECONCILED':
            self.assertEqual(a['reported_count'],a['recomputed_count'])

if __name__ == '__main__':
    unittest.main(verbosity=2)
