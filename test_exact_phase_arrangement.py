import unittest
from shapely.geometry import Polygon
from exact_phase_arrangement import optimize_phase_fixed_orientation, PhaseArrangementError
from continuous_lattice_bnb import _candidate_index_ranges, _count_layout


class ExactPhaseArrangementTests(unittest.TestCase):
    def setUp(self):
        self.poly = Polygon([(0,0),(12,0),(12,8),(8,8),(8,5),(4,5),(4,8),(0,8)])

    def test_fixed_orientation_phase_max_dominates_dense_grid(self):
        spacing_a, spacing_b, theta = 2.0, 2.5, 0.0
        r = optimize_phase_fixed_orientation(self.poly, spacing_a, spacing_b, theta)
        ranges, center = _candidate_index_ranges(self.poly, spacing_a, spacing_b)
        dense = 0
        for ai in range(40):
            for bi in range(40):
                dense = max(dense, _count_layout(self.poly, theta, ai/40, bi/40,
                                                 spacing_a, spacing_b, center, ranges))
        self.assertGreaterEqual(r['max_count'], dense)
        self.assertGreater(r['phase_pieces'], 0)
        self.assertGreater(r['tested_phase_points'], 0)

    def test_rotated_fixed_orientation_runs(self):
        r = optimize_phase_fixed_orientation(self.poly, 1.0, 2.0, 37.5)
        self.assertGreaterEqual(r['max_count'], 0)
        self.assertIn('PHASE_ARRANGEMENT_COMPLETE', r['status'])


    def test_polygon_with_obstacle_hole(self):
        from shapely.geometry import box
        usable = box(0, 0, 10, 8).difference(box(4, 3, 6, 5))
        r = optimize_phase_fixed_orientation(usable, 1.5, 2.0, 23.0)
        ranges, center = _candidate_index_ranges(usable, 1.5, 2.0)
        dense = 0
        for ai in range(20):
            for bi in range(20):
                dense = max(dense, _count_layout(usable, 23.0, ai/20, bi/20,
                                                 1.5, 2.0, center, ranges))
        self.assertGreaterEqual(r['max_count'], dense)

    def test_invalid_polygon_rejected(self):
        with self.assertRaises(PhaseArrangementError):
            optimize_phase_fixed_orientation(Polygon(), 1, 2, 0)

    def test_invalid_spacing_rejected(self):
        with self.assertRaises(PhaseArrangementError):
            optimize_phase_fixed_orientation(self.poly, 0, 2, 0)


if __name__ == '__main__':
    unittest.main(verbosity=2)
