from __future__ import annotations
from dataclasses import replace
from fractions import Fraction
import random
import unittest

from shapely.geometry import box

from optimization_engine_v04 import _make_specs, enumerate_layout
from certified_upper_bound_v03 import (
    certified_lattice_upper_bound,
    CertifiedBoundError,
)


class CertifiedUpperBoundV031Tests(unittest.TestCase):
    def test_rectangular_family_dominates_random_translations_and_orientations(self):
        usable = box(0, 0, 24, 18).difference(box(8, 5, 13, 12))
        spec = _make_specs(3.0, 2.0)["rectangular_crop"]
        result = certified_lattice_upper_bound(usable, spec)
        self.assertTrue(result["certified"])
        self.assertEqual(result["status"], "CERTIFIED_RATIONAL_STEINER_ENCLOSURE")
        ub = result["upper_bound_count"]
        rng = random.Random(20261125)
        for _ in range(350):
            theta = rng.random() * spec.angle_period_deg
            pa, pb = rng.random(), rng.random()
            count = enumerate_layout(usable, usable.bounds, spec, theta, pa, pb)["count"]
            self.assertLessEqual(count, ub)

    def test_triangular_family_dominates_random_translations_and_orientations(self):
        usable = box(0, 0, 24, 18).difference(box(8, 5, 13, 12))
        spec = _make_specs(3.0, 2.0)["triangular_equal_density"]
        result = certified_lattice_upper_bound(usable, spec)
        self.assertTrue(result["certified"])
        ub = result["upper_bound_count"]
        rng = random.Random(20261126)
        for _ in range(350):
            theta = rng.random() * spec.angle_period_deg
            pa, pb = rng.random(), rng.random()
            count = enumerate_layout(usable, usable.bounds, spec, theta, pa, pb)["count"]
            self.assertLessEqual(count, ub)

    def test_multicomponent_with_holes_has_conservative_bound(self):
        left = box(0, 0, 8, 8).difference(box(2, 2, 3, 3))
        right = box(12, 0, 20, 8)
        from shapely.geometry import MultiPolygon
        usable = MultiPolygon([left, right])
        spec = _make_specs(2.0, 2.0)["rectangular_crop"]
        result = certified_lattice_upper_bound(usable, spec)
        self.assertTrue(result["certified"])
        self.assertGreaterEqual(result["upper_bound_count"], 0)
        self.assertGreaterEqual(result["hull_area_m2"], usable.area)

    def test_exact_fraction_outputs_are_consistent(self):
        usable = box(0, 0, 10, 10)
        spec = _make_specs(2.0, 3.0)["rectangular_crop"]
        result = certified_lattice_upper_bound(usable, spec)
        q = Fraction(result["exact_quotient_fraction"])
        cell = Fraction(result["exact_cell_area_lower_fraction"])
        area = Fraction(result["exact_area_upper_fraction"])
        self.assertEqual(q, area / cell)
        self.assertEqual(result["upper_bound_count"], q.numerator // q.denominator)
        self.assertGreaterEqual(float(area), usable.area)

    def test_empty_geometry_returns_certified_zero(self):
        from shapely.geometry import Polygon as EmptyPolygon
        spec = _make_specs(2.0, 3.0)["rectangular_crop"]
        result = certified_lattice_upper_bound(EmptyPolygon(), spec)
        self.assertTrue(result["certified"])
        self.assertEqual(result["upper_bound_count"], 0)
        self.assertEqual(result["status"], "CERTIFIED_EMPTY_SET_ZERO")

    def test_unsupported_lattice_angle_is_rejected(self):
        spec = _make_specs(2.0, 3.0)["rectangular_crop"]
        with self.assertRaises(CertifiedBoundError):
            certified_lattice_upper_bound(box(0, 0, 10, 10), replace(spec, gamma_deg=75.0))


if __name__ == "__main__":
    unittest.main(verbosity=2)
