import math
import random
import unittest

from shapely.geometry import Polygon, box

from continuous_lattice_bnb import (
    _candidate_index_ranges, _node_upper_bound, _count_layout,
    optimize_rectangular_lattice, SearchInputError,
)


class ContinuousLatticeBnbTests(unittest.TestCase):
    def setUp(self):
        self.poly = Polygon([(0,0),(12,0),(12,8),(8,8),(8,5),(4,5),(4,8),(0,8)])
        self.spacing_a = 2.0
        self.spacing_b = 2.5
        self.ranges, self.center = _candidate_index_ranges(self.poly, self.spacing_a, self.spacing_b)

    def test_seed_result_is_feasible_and_bound_dominates(self):
        out = optimize_rectangular_lattice(self.poly, self.spacing_a, self.spacing_b,
                                           max_nodes=150, seed_grid_angle_step=30,
                                           seed_phase_divisions=3)
        self.assertGreaterEqual(out['best_found_count'], 0)
        self.assertGreaterEqual(out['upper_bound_count'], out['best_found_count'])
        self.assertGreaterEqual(out['absolute_gap'], 0)
        self.assertGreater(out['evaluated_layouts'], 0)

    def test_root_upper_bound_dominates_random_parameter_samples(self):
        root_ub = _node_upper_bound(self.poly, (0,180), (0,1), (0,1),
                                    self.spacing_a, self.spacing_b,
                                    self.center, self.ranges)
        rng = random.Random(20261125)
        for _ in range(250):
            theta = rng.random()*180
            pa, pb = rng.random(), rng.random()
            count = _count_layout(self.poly, theta, pa, pb, self.spacing_a,
                                  self.spacing_b, self.center, self.ranges)
            self.assertLessEqual(count, root_ub)

    def test_upper_bound_dominates_dense_small_grid(self):
        root_ub = _node_upper_bound(self.poly, (0,180), (0,1), (0,1),
                                    self.spacing_a, self.spacing_b,
                                    self.center, self.ranges)
        for ti in range(0, 180, 10):
            for ai in range(0, 10):
                for bi in range(0, 10):
                    n = _count_layout(self.poly, ti, ai/10, bi/10,
                                      self.spacing_a, self.spacing_b,
                                      self.center, self.ranges)
                    self.assertLessEqual(n, root_ub)

    def test_invalid_spacing_rejected(self):
        with self.assertRaises(SearchInputError):
            optimize_rectangular_lattice(self.poly, 0, 2)

    def test_empty_geometry_rejected(self):
        with self.assertRaises(SearchInputError):
            optimize_rectangular_lattice(Polygon(), 2, 3)

    def test_rectangle_edge_boundary_is_included(self):
        p = box(0,0,4,4)
        count = _count_layout(p, 0, 0, 0, 2, 2, (2,2), (-3,3,-3,3))
        self.assertGreaterEqual(count, 9)

    def test_returned_phase_is_converted_to_global_engine_frame(self):
        import sys
        from pathlib import Path
        root = Path(__file__).resolve().parents[1]
        sys.path.insert(0, str(root/'engine'))
        from optimization_engine_v04 import _make_specs, enumerate_layout
        out = optimize_rectangular_lattice(self.poly, self.spacing_a, self.spacing_b,
                                           max_nodes=4, seed_grid_angle_step=60,
                                           seed_phase_divisions=2)
        spec = _make_specs(self.spacing_b, self.spacing_a)['rectangular_crop']
        layout = enumerate_layout(self.poly, self.poly.bounds, spec,
                                  out['best_theta_deg'], out['best_phase_a'],
                                  out['best_phase_b'], include_points=True)
        self.assertEqual(layout['count'], out['best_found_count'])
        self.assertEqual(out['phase_coordinate_frame'], 'global_local_xy_origin; centered phases retained in *_centered fields')

    def test_time_budget_stops_search_without_false_tree_closure(self):
        poly = box(0, 0, 20, 20)
        out = optimize_rectangular_lattice(
            poly, 2.0, 3.0, max_nodes=1000, seed_grid_angle_step=60,
            seed_phase_divisions=4, max_candidate_indices=50000,
            time_budget_seconds=1e-9
        )
        self.assertEqual(out['status'], 'TIME_LIMIT_BEST_FOUND_WITH_GAP')
        self.assertGreaterEqual(out['best_found_count'], 0)
        self.assertIsNotNone(out['time_budget_seconds'])
        self.assertEqual(out['evaluated_layouts'], 1)
        self.assertIsNone(out['upper_bound_count'])
        self.assertIsNone(out['absolute_gap'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
