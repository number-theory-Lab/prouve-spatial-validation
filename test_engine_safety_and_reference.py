import math
import unittest
from engine_safety import (EngineInputError, classify_optimality,
                           conservative_integer_upper_bound, compare_verifier_results)
from reference_verifier import verify_plan_reference


class Patch01To10Tests(unittest.TestCase):
    def test_patch01_bf_less_than_ub(self):
        self.assertEqual(classify_optimality(7, 9, True, True, True), "BEST_FOUND_NOT_PROVEN_OPTIMAL")

    def test_patch02_equal_positive_certified(self):
        self.assertEqual(classify_optimality(9, 9, True, True, True), "BOUND_MATCH_NUMERIC_FEASIBILITY_ONLY")

    def test_patch03_bf_greater_than_ub(self):
        self.assertEqual(classify_optimality(10, 9, True, True, True), "BOUND_CONFLICT")

    def test_patch04_zero_zero_not_usable_solution(self):
        self.assertEqual(classify_optimality(0, 0, False, True, True), "NO_FEASIBLE_POINTS_IN_ENUMERATED_SEARCH")
        self.assertEqual(classify_optimality(0, 0, True, True, True), "NO_POSITIVE_SOLUTION")

    def test_patch05_empty_plan_is_not_verified(self):
        case = {"field":{"vertices":[[0,0],[5,0],[5,5],[0,5]]}}
        result = {"search":{"rectangular_crop_row":{"best_theta_deg":0,"best_phase_a_fraction":0,"best_phase_b_fraction":0}},
                  "planting_positions":[]}
        v = verify_plan_reference(case, result)
        self.assertFalse(v["all_checks_passed"])
        self.assertEqual(v["status"], "NO_FEASIBLE_POINTS")

    def test_patch06_nan_infinity_and_bad_counts_rejected(self):
        for v in (float('nan'), float('inf'), -1, 1.5, True, "4"):
            with self.assertRaises(EngineInputError):
                classify_optimality(v, 10, True, True, True)
        with self.assertRaises(EngineInputError):
            conservative_integer_upper_bound(float('inf'), source_bound_certified=True)

    def test_patch07_quotient_just_above_integer_not_rounded_down(self):
        r = conservative_integer_upper_bound(10.0000000000005, source_bound_certified=True)
        self.assertEqual(r["upper_bound_count"], 11)
        self.assertTrue(r["certified"])
        est = conservative_integer_upper_bound(10.0000000000005, source_bound_certified=False)
        self.assertEqual(est["status"], "UB_ESTIMATE_ONLY")

    def test_patch08_concave_polygon_and_obstacle_clearance(self):
        case = {"field":{"vertices":[[0,0],[12,0],[12,8],[8,8],[8,5],[4,5],[4,8],[0,8]]},
                "obstacles":[{"name":"pond","vertices":[[5,1],[7,1],[7,3],[5,3]]}],
                "settings":{"boundary_setback_m":0.5,"obstacle_buffer_m":0.5},
                "crop":{"row_spacing_m":2,"in_row_spacing_m":1}}
        result = {"search":{"rectangular_crop_row":{"best_theta_deg":0,"best_phase_a_fraction":0,"best_phase_b_fraction":0}},
                  "planting_positions":[{"x_m":2,"y_m":2,"lattice_i":1,"lattice_j":2}]}
        v = verify_plan_reference(case, result)
        self.assertTrue(v["all_checks_passed"])
        bad = {**result,"search":{"rectangular_crop_row":{"best_theta_deg":0,"best_phase_a_fraction":0.5,"best_phase_b_fraction":0}},
               "planting_positions":[{"x_m":5.5,"y_m":2,"lattice_i":1,"lattice_j":5}]}
        vb = verify_plan_reference(case, bad)
        self.assertFalse(vb["all_checks_passed"])
        self.assertGreater(vb["checks"]["obstacle_clearance"], 0)


    def test_patch08_self_intersection_is_rejected_by_reference_verifier(self):
        case = {"field":{"vertices":[[0,0],[4,4],[0,4],[4,0]]}}
        result = {"search":{"rectangular_crop_row":{"best_theta_deg":0,"best_phase_a_fraction":0,"best_phase_b_fraction":0}},
                  "planting_positions":[{"x_m":1,"y_m":1,"lattice_i":0,"lattice_j":0}]}
        with self.assertRaises(ValueError):
            verify_plan_reference(case, result)

    def test_patch09_boundary_coverage_with_zero_setback(self):
        case = {"field":{"vertices":[[0,0],[4,0],[4,4],[0,4]]},"settings":{"boundary_setback_m":0,"obstacle_buffer_m":0},
                "crop":{"row_spacing_m":2,"in_row_spacing_m":2}}
        result = {"search":{"rectangular_crop_row":{"best_theta_deg":0,"best_phase_a_fraction":0,"best_phase_b_fraction":0}},
                  "planting_positions":[{"x_m":0,"y_m":0,"lattice_i":0,"lattice_j":0}]}
        self.assertTrue(verify_plan_reference(case, result)["all_checks_passed"])

    def test_patch10_verifier_disagreement_holds(self):
        a = {"all_checks_passed":True,"verified_point_count":5,"status":"VERIFIED_FEASIBLE"}
        b = {"all_checks_passed":False,"verified_point_count":5,"status":"VERIFICATION_FAILED"}
        self.assertEqual(compare_verifier_results(a,b)["status"], "HOLD")
        self.assertEqual(compare_verifier_results(a,a)["status"], "AGREE")


if __name__ == '__main__':
    unittest.main(verbosity=2)
