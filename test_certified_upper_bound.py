from __future__ import annotations
import json
import random
import sys
import unittest
from pathlib import Path

from shapely.geometry import Polygon, box
from shapely.ops import unary_union

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'engine'))
from geometry_engine_v02 import compute_usable_area
from optimization_engine_v04 import _make_specs, lattice_upper_bound, enumerate_layout
from certified_upper_bound import certified_lattice_upper_bound


class CertifiedUpperBoundTests(unittest.TestCase):
    def test_baseline_fixture_certified_bound_dominates_grid_search(self):
        case = json.loads((ROOT/'reports/full_pipeline_output/engine_case.json').read_text())
        geo = compute_usable_area(case)
        spec = _make_specs(case['crop']['row_spacing_m'], case['crop']['in_row_spacing_m'])['rectangular_crop']
        cert = lattice_upper_bound(geo['geometries']['usable'], spec)
        self.assertTrue(cert['upper_bound_certified'])
        self.assertEqual(cert['upper_bound_count'], 77)
        self.assertLessEqual(63, cert['upper_bound_count'])
        self.assertEqual(cert['upper_bound_status'], 'CERTIFIED_RATIONAL_STEINER_ENCLOSURE')
        self.assertIn('/', cert['exact_quotient_fraction'])

    def test_random_translations_and_orientations_below_certified_bound(self):
        case = json.loads((ROOT/'reports/full_pipeline_output/engine_case.json').read_text())
        geo = compute_usable_area(case)
        usable = geo['geometries']['usable']
        spec = _make_specs(3.0, 2.0)['rectangular_crop']
        ub = certified_lattice_upper_bound(usable, spec)['upper_bound_count']
        rng = random.Random(22062026)
        for _ in range(350):
            theta = rng.random()*180.0
            pa, pb = rng.random(), rng.random()
            count = enumerate_layout(usable, geo['geometries']['field'].bounds,
                                     spec, theta, pa, pb)['count']
            self.assertLessEqual(count, ub)

    def test_triangular_and_square_family_certified(self):
        usable = box(0, 0, 15, 11).difference(box(6, 3, 9, 7))
        specs = _make_specs(3.0, 2.0)
        for key in ('square_equal_density', 'triangular_equal_density'):
            cert = certified_lattice_upper_bound(usable, specs[key])
            self.assertTrue(cert['certified'])
            self.assertGreaterEqual(cert['upper_bound_count'], 0)

    def test_multipolygon_and_hole_geometry_certified(self):
        usable = unary_union([box(0,0,4,4), box(8,0,12,4)]).difference(box(1,1,2,2))
        spec = _make_specs(1.5, 1.0)['rectangular_crop']
        cert = certified_lattice_upper_bound(usable, spec)
        self.assertTrue(cert['certified'])
        self.assertGreaterEqual(cert['upper_bound_count'], 0)

    def test_empty_geometry_has_certified_zero(self):
        from shapely.geometry import Polygon as EmptyPolygon
        cert = certified_lattice_upper_bound(EmptyPolygon(), _make_specs(2.0, 3.0)['rectangular_crop'])
        self.assertTrue(cert['certified'])
        self.assertEqual(cert['upper_bound_count'], 0)
        self.assertEqual(cert['status'], 'CERTIFIED_EMPTY_SET_ZERO')
        self.assertEqual(cert['exact_cell_area_lower_fraction'], 'not_required_empty_set')

    def test_large_coordinate_offset_keeps_integer_indices_safe(self):
        from optimization_engine_v04 import search_lattice
        poly = box(1e12, 1e12, 1e12+60, 1e12+45)
        spec = _make_specs(3.0, 2.0)['rectangular_crop']
        result = search_lattice(poly, poly.bounds, spec, angle_step_deg=45,
                                phase_divisions=3, refine=False)
        self.assertGreater(result['best_count'], 0)
        self.assertGreater(max(abs(result['best']['accepted_i']).max(), abs(result['best']['accepted_j']).max()), 2**31)

    def test_bound_rejects_invalid_or_unsupported_geometry(self):
        spec = _make_specs(2.0, 3.0)['rectangular_crop']
        with self.assertRaises(Exception):
            certified_lattice_upper_bound(Polygon([(0,0),(1,1),(2,2)]), spec)


if __name__ == '__main__':
    unittest.main(verbosity=2)
