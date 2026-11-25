import unittest
from engine.formal_feasibility_certificate import (
    CertificateInputError, verify_candidate_set, verify_case_points,
)


def poly(shell, holes=None):
    return {"type": "Polygon", "coordinates": [shell] + (holes or [])}


class FormalCertificateTests(unittest.TestCase):
    def test_polygon_feasible_exact_clearance(self):
        field = poly([[0,0],[10,0],[10,10],[0,10],[0,0]])
        result = verify_candidate_set(field, [], [{"plant_id":"P1","x_m":"1","y_m":"1"}], boundary_setback_m="1")
        self.assertEqual(result["status"], "CERTIFIED_FEASIBLE")
        self.assertTrue(result["certified"])

    def test_below_clearance_fails_without_epsilon(self):
        field = poly([[0,0],[10,0],[10,10],[0,10],[0,0]])
        result = verify_candidate_set(field, [], [{"plant_id":"P1","x_m":"0.999999999999","y_m":"5"}], boundary_setback_m="1")
        self.assertEqual(result["status"], "CERTIFIED_INFEASIBLE")
        self.assertIn("BOUNDARY_CLEARANCE_BELOW_REQUIRED_MARGIN", result["points"][0]["reasons"])

    def test_polygon_hole_is_excluded(self):
        field = poly([[0,0],[20,0],[20,20],[0,20],[0,0]], [[[8,8],[12,8],[12,12],[8,12],[8,8]]])
        inside_hole = verify_candidate_set(field, [], [{"x_m":10,"y_m":10}], boundary_setback_m=0)
        outside_hole = verify_candidate_set(field, [], [{"x_m":5,"y_m":5}], boundary_setback_m=1)
        self.assertEqual(inside_hole["status"], "CERTIFIED_INFEASIBLE")
        self.assertIn("OUTSIDE_FIELD_OR_INSIDE_FIELD_HOLE", inside_hole["points"][0]["reasons"])
        self.assertEqual(outside_hole["status"], "CERTIFIED_FEASIBLE")

    def test_hole_boundary_counts_for_clearance(self):
        field = poly([[0,0],[20,0],[20,20],[0,20],[0,0]], [[[8,8],[12,8],[12,12],[8,12],[8,8]]])
        result = verify_candidate_set(field, [], [{"x_m":7,"y_m":10}], boundary_setback_m=1)
        self.assertEqual(result["status"], "CERTIFIED_FEASIBLE")

    def test_multipolygon_disjoint_components(self):
        geom = {"type":"MultiPolygon", "coordinates":[
            [[[0,0],[5,0],[5,5],[0,5],[0,0]]],
            [[[10,0],[15,0],[15,5],[10,5],[10,0]]]
        ]}
        result = verify_candidate_set(geom, [], [{"x_m":2,"y_m":2},{"x_m":12,"y_m":2}], boundary_setback_m=1)
        self.assertEqual(result["status"], "CERTIFIED_FEASIBLE")
        fail = verify_candidate_set(geom, [], [{"x_m":7,"y_m":2}], boundary_setback_m=0)
        self.assertEqual(fail["status"], "CERTIFIED_INFEASIBLE")

    def test_obstacle_clearance_and_hole(self):
        field = poly([[0,0],[20,0],[20,20],[0,20],[0,0]])
        obstacle = poly([[8,8],[12,8],[12,12],[8,12],[8,8]])
        ok = verify_candidate_set(field, [obstacle], [{"x_m":7,"y_m":10}], obstacle_clearance_m=1)
        bad = verify_candidate_set(field, [obstacle], [{"x_m":8.5,"y_m":10}], obstacle_clearance_m=1)
        self.assertEqual(ok["status"], "CERTIFIED_FEASIBLE")
        self.assertEqual(bad["status"], "CERTIFIED_INFEASIBLE")

    def test_explicit_uncertainty_is_added(self):
        field = poly([[0,0],[10,0],[10,10],[0,10],[0,0]])
        result = verify_candidate_set(field, [], [{"x_m":1,"y_m":5}], boundary_setback_m=1, boundary_uncertainty_m="0.1")
        self.assertEqual(result["status"], "CERTIFIED_INFEASIBLE")
        self.assertEqual(result["effective_boundary_clearance_m"], "11/10")

    def test_pairwise_spacing_and_duplicate_detection(self):
        field = poly([[0,0],[10,0],[10,10],[0,10],[0,0]])
        result = verify_candidate_set(field, [], [
            {"plant_id":"A","x_m":2,"y_m":2},
            {"plant_id":"B","x_m":2.5,"y_m":2},
        ], minimum_spacing_m=1)
        self.assertEqual(result["status"], "CERTIFIED_INFEASIBLE")
        self.assertEqual(len(result["pairwise_spacing_failures"]), 1)
        dup = verify_candidate_set(field, [], [{"x_m":2,"y_m":2},{"x_m":2,"y_m":2}])
        self.assertEqual(dup["failed_points"], 1)

    def test_invalid_self_intersection_is_rejected(self):
        bowtie = poly([[0,0],[10,10],[0,10],[10,0],[0,0]])
        with self.assertRaises(CertificateInputError):
            verify_candidate_set(bowtie, [], [{"x_m":2,"y_m":2}])

    def test_touching_multipolygon_is_rejected_as_unsupported(self):
        geom = {"type":"MultiPolygon", "coordinates":[
            [[[0,0],[5,0],[5,5],[0,5],[0,0]]],
            [[[5,0],[10,0],[10,5],[5,5],[5,0]]]
        ]}
        with self.assertRaises(CertificateInputError):
            verify_candidate_set(geom, [], [{"x_m":2,"y_m":2}])

    def test_empty_candidate_set_holds(self):
        field = poly([[0,0],[10,0],[10,10],[0,10],[0,0]])
        result = verify_candidate_set(field, [], [])
        self.assertEqual(result["status"], "HOLD_EMPTY_CANDIDATE_SET")
        self.assertFalse(result["certified"])

    def test_case_adapter_uses_current_case_shape(self):
        case = {"field":{"vertices":[[0,0],[10,0],[10,10],[0,10]]}, "obstacles":[], "settings":{"boundary_setback_m":1}}
        result = verify_case_points(case, [{"plant_id":"P1","x_m":1,"y_m":1}])
        self.assertEqual(result["status"], "CERTIFIED_FEASIBLE")


if __name__ == "__main__":
    unittest.main(verbosity=2)
