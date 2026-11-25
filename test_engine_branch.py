from __future__ import annotations
import json
import math
import tempfile
import unittest
from pathlib import Path

from geometry_engine_v02 import compute_usable_area, GeometryInputError
from optimization_engine_v04 import run_benchmarks, _make_specs, search_lattice, lattice_upper_bound, OptimizationInputError
from engine_safety import classify_optimality, conservative_integer_upper_bound, compare_verifier_results
from reference_verifier import verify_plan_reference, ReferenceVerificationError
from shapely_verifier import verify_plan_shapely
from pipeline_runner import run_pipeline

ROOT = Path(__file__).resolve().parents[1]


def square_case():
    return {
        'field': {'vertices': [[0,0],[20,0],[20,20],[0,20]]},
        'obstacles': [],
        'settings': {'boundary_setback_m': 1.0, 'obstacle_buffer_m': 1.0, 'quad_segs': 32, 'geometry_tolerance_m': 1e-7},
        'crop': {'row_spacing_m': 3.0, 'in_row_spacing_m': 2.0, 'plants_per_hole_after_thinning': 1},
    }


class EngineBranchPatchTests(unittest.TestCase):
    def test_patch01_best_found_below_estimate_not_optimal(self):
        self.assertEqual(classify_optimality(63, 78, True, False, True), 'BEST_FOUND_NOT_PROVEN_OPTIMAL')

    def test_patch02_equality_needs_certified_bound_and_verifiers(self):
        self.assertEqual(classify_optimality(5, 5, True, False, True), 'EQUALITY_WITHOUT_CERTIFIED_UB_OR_VERIFICATION')
        self.assertEqual(classify_optimality(5, 5, True, True, True), 'BOUND_MATCH_NUMERIC_FEASIBILITY_ONLY')
        self.assertEqual(classify_optimality(5, 5, True, True, True, feasibility_formally_certified=True), 'OPTIMAL_WITHIN_DECLARED_LATTICE_FAMILY')

    def test_patch03_best_above_bound_is_conflict(self):
        self.assertEqual(classify_optimality(10, 9, True, True, True), 'BOUND_CONFLICT')

    def test_patch04_zero_empty_is_not_optimal(self):
        self.assertEqual(classify_optimality(0, 0, False, False, False), 'NO_FEASIBLE_POINTS_IN_ENUMERATED_SEARCH')
        self.assertEqual(classify_optimality(0, 0, True, True, True), 'NO_POSITIVE_SOLUTION')

    def test_patch05_empty_plan_rejected_by_both_verifiers(self):
        case = square_case()
        result = {'search': {'rectangular_crop_row': {'best_count': 0, 'best_theta_deg': 0, 'best_phase_a_fraction': 0, 'best_phase_b_fraction': 0}}, 'planting_positions': []}
        self.assertEqual(verify_plan_reference(case, result)['status'], 'NO_FEASIBLE_POINTS')
        self.assertEqual(verify_plan_shapely(case, result)['status'], 'NO_FEASIBLE_POINTS')

    def test_patch06_geometry_rejects_boolean_coordinate_and_setting(self):
        c = square_case(); c['field']['vertices'][0][0] = True
        with self.assertRaises(GeometryInputError):
            compute_usable_area(c)
        c = square_case(); c['settings']['boundary_setback_m'] = True
        with self.assertRaises(GeometryInputError):
            compute_usable_area(c)

    def test_patch06_optimizer_rejects_nan_spacing_and_bad_angle(self):
        with self.assertRaises(OptimizationInputError):
            _make_specs(float('nan'), 1.0)
        geom = compute_usable_area(square_case())
        spec = _make_specs(3.0, 2.0)['rectangular_crop']
        with self.assertRaises(OptimizationInputError):
            search_lattice(geom['geometries']['usable'], geom['geometries']['field'].bounds, spec, angle_step_deg=float('nan'))

    def test_patch06_optimizer_rejects_boolean_spacing_and_noninteger_plants_per_hole(self):
        c = square_case(); c['crop']['row_spacing_m'] = True
        with self.assertRaises(OptimizationInputError):
            run_benchmarks(c, angle_step_deg=30, phase_divisions=3, refine=False, run_comparison_lattices=False)
        c = square_case(); c['crop']['plants_per_hole_after_thinning'] = 1.5
        with self.assertRaises(OptimizationInputError):
            run_benchmarks(c, angle_step_deg=30, phase_divisions=3, refine=False, run_comparison_lattices=False)

    def test_patch07_no_epsilon_subtraction_and_estimate_not_certified(self):
        converted = conservative_integer_upper_bound(10.0000000000005, source_bound_certified=False)
        self.assertEqual(converted['upper_bound_count'], 11)
        self.assertFalse(converted['certified'])
        geom = compute_usable_area(square_case())
        spec = _make_specs(3.0, 2.0)['rectangular_crop']
        ub = lattice_upper_bound(geom['geometries']['usable'], spec)
        self.assertTrue(ub['upper_bound_certified'])
        self.assertEqual(ub['upper_bound_status'], 'CERTIFIED_RATIONAL_STEINER_ENCLOSURE')
        self.assertEqual(ub['legacy_geos_estimate']['legacy_rounding_rule'], 'ceil(q); no epsilon subtraction')

    def test_patch08_concave_field_and_obstacle_clearance(self):
        case = {'field': {'vertices': [[0,0],[12,0],[12,8],[8,8],[8,5],[4,5],[4,8],[0,8]]},
                'obstacles': [{'name':'pond','vertices': [[5,1],[7,1],[7,3],[5,3]]}],
                'settings': {'boundary_setback_m':0.5,'obstacle_buffer_m':0.5},
                'crop': {'row_spacing_m':2,'in_row_spacing_m':1}}
        res = {'search': {'rectangular_crop_row': {'best_count':1,'best_theta_deg':0,'best_phase_a_fraction':0,'best_phase_b_fraction':0}},
               'planting_positions': [{'x_m':2,'y_m':2,'lattice_i':1,'lattice_j':2}]}
        v = verify_plan_reference(case, res)
        self.assertTrue(v['all_checks_passed'])
        bad = dict(res); bad['planting_positions'] = [{'x_m':5.5,'y_m':2,'lattice_i':1,'lattice_j':5}]
        self.assertFalse(verify_plan_reference(case, bad)['all_checks_passed'])

    def test_patch08_self_intersection_rejected(self):
        case = square_case(); case['field']['vertices'] = [[0,0],[4,4],[0,4],[4,0]]
        res = {'search': {'rectangular_crop_row': {'best_count':1,'best_theta_deg':0,'best_phase_a_fraction':0,'best_phase_b_fraction':0}},
               'planting_positions': [{'x_m':1,'y_m':1,'lattice_i':0,'lattice_j':0}]}
        with self.assertRaises(ReferenceVerificationError):
            verify_plan_reference(case, res)

    def test_patch09_zero_setback_boundary_inclusive(self):
        case = {'field': {'vertices': [[0,0],[4,0],[4,4],[0,4]]}, 'obstacles': [],
                'settings': {'boundary_setback_m':0,'obstacle_buffer_m':0},
                'crop': {'row_spacing_m':2,'in_row_spacing_m':2}}
        res = {'search': {'rectangular_crop_row': {'best_count':1,'best_theta_deg':0,'best_phase_a_fraction':0,'best_phase_b_fraction':0}},
               'planting_positions': [{'x_m':0,'y_m':0,'lattice_i':0,'lattice_j':0}]}
        self.assertTrue(verify_plan_reference(case, res)['all_checks_passed'])

    def test_patch09_zero_obstacle_clearance_allows_boundary_not_interior(self):
        case = {'field': {'vertices': [[0,0],[10,0],[10,10],[0,10]]},
                'obstacles': [{'name':'pond','vertices': [[4,4],[6,4],[6,6],[4,6]]}],
                'settings': {'boundary_setback_m':0,'obstacle_buffer_m':0},
                'crop': {'row_spacing_m':2,'in_row_spacing_m':2}}
        res = {'search': {'rectangular_crop_row': {'best_count':1,'best_theta_deg':0,'best_phase_a_fraction':0,'best_phase_b_fraction':0}},
               'planting_positions': [{'x_m':4,'y_m':4,'lattice_i':2,'lattice_j':2}]}
        self.assertTrue(verify_plan_reference(case, res)['all_checks_passed'])
        res['search']['rectangular_crop_row']['best_phase_a_fraction'] = 0.5
        res['search']['rectangular_crop_row']['best_phase_b_fraction'] = 0.5
        res['planting_positions'] = [{'x_m':5,'y_m':5,'lattice_i':2,'lattice_j':2}]
        self.assertFalse(verify_plan_reference(case, res)['all_checks_passed'])

    def test_patch10_disagreement_holds(self):
        a = {'all_checks_passed':True, 'verified_point_count':4, 'status':'VERIFIED_FEASIBLE'}
        b = {'all_checks_passed':False, 'verified_point_count':4, 'status':'VERIFICATION_FAILED'}
        self.assertEqual(compare_verifier_results(a,b)['status'], 'HOLD')

    def test_reference_rejects_fractional_lattice_index(self):
        case = square_case()
        res = {'search': {'rectangular_crop_row': {'best_count':1,'best_theta_deg':0,'best_phase_a_fraction':0,'best_phase_b_fraction':0}},
               'planting_positions': [{'x_m':0,'y_m':0,'lattice_i':0.5,'lattice_j':0}]}
        v = verify_plan_reference(case, res)
        self.assertFalse(v['all_checks_passed'])
        self.assertEqual(v['checks']['coordinate_reconstruction'], 1)

    def test_pipeline_end_to_end_synthetic(self):
        with tempfile.TemporaryDirectory() as td:
            report = run_pipeline(ROOT/'adapter/sample_app_project.json', ROOT/'adapter/sample_site_profile.json', Path(td),
                                  mode='exploratory', angle_step_deg=30, phase_divisions=3,
                                  refine=False, comparison_lattices=False)
            self.assertEqual(report['pipeline_status'], 'SYNTHETIC_PIPELINE_PASS_EXPLORATORY_ONLY')
            self.assertEqual(report['verification']['agreement']['status'], 'AGREE')
            self.assertEqual(report['optimization']['best_found_count'], 63)
            self.assertTrue(report['optimization']['upper_bound_certified'])
            self.assertEqual(report['optimization']['optimality_status_after_checks'], 'BEST_FOUND_NOT_PROVEN_OPTIMAL')
            self.assertFalse(report['field_deployment_authorized'])
            self.assertTrue((Path(td)/'evidence_report.json').exists())


if __name__ == '__main__':
    unittest.main(verbosity=2)
