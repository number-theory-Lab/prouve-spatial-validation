from __future__ import annotations
import math
import random
import sys
import unittest
from pathlib import Path

from shapely.geometry import Polygon

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'engine'))
sys.path.insert(0, str(ROOT/'adapter'))
from geometry_engine_v02 import compute_usable_area, GeometryInputError
from optimization_engine_v04 import run_benchmarks, OptimizationInputError
from reference_verifier import verify_plan_reference
from shapely_verifier import verify_plan_shapely


def case_from(vertices, obstacles=None, setback=0.25, clearance=0.25,
              row=3.0, along=2.0, tol=1e-7):
    return {
        'field': {'vertices': vertices},
        'obstacles': obstacles or [],
        'settings': {'boundary_setback_m': setback, 'obstacle_buffer_m': clearance,
                     'quad_segs': 32, 'geometry_tolerance_m': tol},
        'crop': {'row_spacing_m': row, 'in_row_spacing_m': along,
                 'plants_per_hole_after_thinning': 1},
    }


def square(x0, y0, side):
    return [[x0,y0],[x0+side,y0],[x0+side,y0+side],[x0,y0+side]]


def build_stress_cases():
    cases = {}
    cases['concave_L'] = case_from(
        [[0,0],[40,0],[40,12],[18,12],[18,34],[0,34]],
        [{'name':'pond_A','vertices':square(5,5,3)},
         {'name':'shed_B','vertices':square(25,4,4)}], 0.5, 0.75)
    cases['concave_U'] = case_from(
        [[0,0],[40,0],[40,30],[28,30],[28,10],[12,10],[12,30],[0,30]],
        [{'name':'obstacle_left','vertices':square(3,3,2)},
         {'name':'obstacle_right','vertices':square(33,3,2)}], 0.4, 0.5)
    cases['radial_concave_24'] = case_from(
        [(50+(40 if k%2==0 else 28)*math.cos(2*math.pi*k/24),
          50+(40 if k%2==0 else 28)*math.sin(2*math.pi*k/24)) for k in range(24)],
        [{'name':'central_pool','vertices':square(47,47,6)}], 0.4, 1.0)
    many = []
    for r in range(5):
        for c in range(5):
            many.append({'name':f'obstacle_{r}_{c}', 'vertices':square(8+c*16, 8+r*16, 2.5)})
    cases['many_obstacles_25'] = case_from(square(0,0,100), many, 1.0, 1.0)
    dense = []
    for r in range(6):
        for c in range(6):
            dense.append({'name':f'dense_{r}_{c}', 'vertices':square(5+c*7,5+r*7,2.2)})
    cases['obstacle_dense_36'] = case_from(square(0,0,50), dense, 0.5, 0.6)
    cases['narrow_corridor'] = case_from(
        [[0,0],[100,0],[100,1.0],[0,1.0]], [], 0.1, 0.05, row=0.3, along=0.2, tol=1e-9)
    cases['near_degenerate_sliver'] = case_from(
        [[0,0],[100,0],[100,0.01],[0,0.01]], [], 0.001, 0.001,
        row=0.002, along=0.003, tol=1e-10)
    cases['large_projected_coords'] = case_from(
        square(500000.0, 1000000.0, 100.0),
        [{'name':'largecoord_obstacle','vertices':square(500040,1000040,5)}],
        0.5, 1.0)
    cases['very_large_offset'] = case_from(
        square(1e12, 1e12, 60.0),
        [{'name':'far_obstacle','vertices':square(1e12+20,1e12+20,5)}],
        0.5, 1.0)
    cases['tiny_scale'] = case_from(
        [[0,0],[0.02,0],[0.02,0.015],[0,0.015]], [],
        0.0002, 0.0002, row=0.002, along=0.0015, tol=1e-10)
    cases['near_touching_obstacles'] = case_from(
        square(0,0,30),
        [{'name':'near_a','vertices':square(10,10,2)},
         {'name':'near_b','vertices':square(12.0001,10,2)}],
        0.5, 0.001)
    cases['setback_erases_area'] = case_from(square(0,0,1), [], 0.6, 0.1, row=0.5, along=0.5)
    return cases


class GeometryStressTests(unittest.TestCase):
    def test_stress_cases_geometry_validity_and_safety(self):
        results = {}
        cases = build_stress_cases()
        for name, case in cases.items():
            with self.subTest(case=name):
                if name == 'very_large_offset':
                    with self.assertRaises(GeometryInputError):
                        compute_usable_area(case)
                    continue
                geom = compute_usable_area(case)
                usable = geom['geometries']['usable']
                self.assertTrue(geom['result']['geometry']['usable_geometry_valid'])
                self.assertTrue(geom['result']['status']['boundary_clearance_verified'])
                self.assertTrue(geom['result']['status']['obstacle_clearance_verified'])
                self.assertGreaterEqual(geom['result']['areas_m2']['usable_planting_area'], 0)
                results[name] = (case, geom)
        self.assertEqual(len(results), len(cases)-1)

    def test_multiple_complex_cases_end_to_end_verifier_agreement(self):
        cases = build_stress_cases()
        selected = ['concave_L','concave_U','many_obstacles_25','large_projected_coords']
        for name in selected:
            with self.subTest(case=name):
                case = cases[name]
                out = run_benchmarks(case, angle_step_deg=45, phase_divisions=3,
                                     refine=False, run_comparison_lattices=False)['result']
                if not out['planting_positions']:
                    continue
                a = verify_plan_reference(case, out)
                b = verify_plan_shapely(case, out)
                self.assertTrue(a['all_checks_passed'], a)
                self.assertTrue(b['all_checks_passed'], b)
                self.assertEqual(a['verified_point_count'], b['verified_point_count'])

    def test_extreme_absolute_offset_rejected_with_local_xy_guidance(self):
        case = build_stress_cases()['very_large_offset']
        with self.assertRaisesRegex(GeometryInputError, 'local XY'):
            compute_usable_area(case)

    def test_self_intersection_is_rejected_safely(self):
        case = case_from([[0,0],[5,5],[0,5],[5,0]], [], 0, 0)
        with self.assertRaises(GeometryInputError):
            compute_usable_area(case)

    def test_boolean_nan_and_infinity_rejected(self):
        invalid_cases = []
        c = case_from(square(0,0,10)); c['field']['vertices'][0][0] = True; invalid_cases.append(c)
        c = case_from(square(0,0,10)); c['settings']['boundary_setback_m'] = float('nan'); invalid_cases.append(c)
        c = case_from(square(0,0,10)); c['settings']['obstacle_buffer_m'] = float('inf'); invalid_cases.append(c)
        for c in invalid_cases:
            with self.assertRaises(GeometryInputError):
                compute_usable_area(c)

    def test_large_index_uses_int64_not_int32(self):
        from shapely.geometry import box
        from optimization_engine_v04 import _make_specs, search_lattice
        poly = box(1e12, 1e12, 1e12+60, 1e12+45)
        spec = _make_specs(3.0, 2.0)['rectangular_crop']
        out = search_lattice(poly, poly.bounds, spec, angle_step_deg=60,
                             phase_divisions=2, refine=False)
        self.assertGreater(out['best_count'], 0)
        self.assertGreater(max(abs(int(v)) for v in out['best']['accepted_i']), 2**31)


if __name__ == '__main__':
    unittest.main(verbosity=2)
