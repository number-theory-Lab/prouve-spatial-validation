from __future__ import annotations
import random
import sys
import unittest
from pathlib import Path
import numpy as np
import shapely

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'engine'))
from test_geometry_stress import build_stress_cases
from geometry_engine_v02 import compute_usable_area
from optimization_engine_v04 import (_basis,_make_specs,_project_bbox_coefficients,
                                      _candidate_indices,_candidate_indices_for_basis,
                                      enumerate_layout)


class ScanlineCandidateTests(unittest.TestCase):
    def test_scanline_count_matches_conservative_bbox_enumeration(self):
        rng=random.Random(20261125)
        cases=build_stress_cases()
        for name in ('concave_L','concave_U','large_projected_coords','tiny_scale'):
            case=cases[name]
            geo=compute_usable_area(case)
            usable=geo['geometries']['usable']
            field=geo['geometries']['field']
            spec=_make_specs(case['crop']['row_spacing_m'],case['crop']['in_row_spacing_m'])['rectangular_crop']
            for theta in (0.0,23.5,45.0,90.0,137.25):
                a,b=_basis(spec,theta)
                coeff=_project_bbox_coefficients(field.bounds,a,b)
                js0,ii0=_candidate_indices(coeff,0.0,0.0)
                js1,ii1=_candidate_indices_for_basis(usable,a,b)
                # Every *accepted point* from the conservative bbox enumeration
                # must have its lattice index represented by the scanline set.
                new_pairs=set(zip(js1.tolist(),ii1.tolist()))
                for _ in range(3):
                    pa,pb=rng.random(),rng.random()
                    ca=pa+js0.astype(float);cb=pb+ii0.astype(float)
                    xs=ca*a[0]+cb*b[0];ys=ca*a[1]+cb*b[1]
                    mask=np.asarray(shapely.covers(usable,shapely.points(xs,ys)),dtype=bool)
                    old_count=int(np.count_nonzero(mask))
                    accepted_pairs=set(zip(js0[mask].tolist(),ii0[mask].tolist()))
                    self.assertTrue(accepted_pairs.issubset(new_pairs),
                                    f'{name} theta={theta}: scanline omitted an accepted lattice index')
                    new_count=enumerate_layout(usable,field.bounds,spec,theta,pa,pb)['count']
                    self.assertEqual(new_count,old_count,f'{name} theta={theta} phases=({pa},{pb})')

    def test_thin_rotated_sliver_does_not_form_huge_cartesian_bbox(self):
        case=build_stress_cases()['near_degenerate_sliver']
        geo=compute_usable_area(case)
        usable=geo['geometries']['usable'];field=geo['geometries']['field']
        spec=_make_specs(case['crop']['row_spacing_m'],case['crop']['in_row_spacing_m'])['rectangular_crop']
        a,b=_basis(spec,45.0)
        js,ii=_candidate_indices_for_basis(usable,a,b)
        self.assertLess(len(js),1_000_000)
        self.assertEqual(len(js),len(ii))
        self.assertGreater(len(js),100_000)

    def test_scanline_span_guard_rejects_excessive_row_iterations(self):
        from shapely.geometry import box
        from optimization_engine_v04 import OptimizationInputError
        poly = box(0.0, 0.0, 0.01, 1_000_010.0)
        spec = _make_specs(1.0, 1.0)['rectangular_crop']
        a, b = _basis(spec, 0.0)
        with self.assertRaisesRegex(OptimizationInputError, 'scanline spans'):
            _candidate_indices_for_basis(poly, a, b)


if __name__=='__main__':
    unittest.main(verbosity=2)
