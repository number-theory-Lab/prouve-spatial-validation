import json
import tempfile
import unittest
from pathlib import Path
from shapely.geometry import Polygon, box

from adaptive_solver import run_adaptive_solver
from pipeline_runner_v03 import run_pipeline_v03
from formal_feasibility_certificate import CertificateInputError, verify_candidate_set
from geometry_engine_v03 import GeometryInputError, compute_usable_area
from lattice_relation_certificate import (
    build_rational_lattice_plan,
    verify_rational_lattice_relation,
)


def polygon_2d():
    return {"type": "Polygon", "coordinates": [[[0, 0], [20, 0], [20, 20], [0, 20], [0, 0]]]}


class AdversarialHardeningV031Tests(unittest.TestCase):
    def test_exact_certificate_rejects_3d_coordinate(self):
        field = {"type": "Polygon", "coordinates": [[[0, 0, 5], [10, 0, 5], [10, 10, 5], [0, 10, 5], [0, 0, 5]]]}
        with self.assertRaises(CertificateInputError):
            verify_candidate_set(field, [], [{"x_m": 1, "y_m": 1}])

    def test_geometry_engine_rejects_3d_geojson(self):
        case = {
            "field": {"type": "Polygon", "coordinates": [[[0, 0, 1], [10, 0, 1], [10, 10, 1], [0, 10, 1], [0, 0, 1]]]},
            "obstacles": [],
            "settings": {"boundary_setback_m": 0, "obstacle_buffer_m": 0, "quad_segs": 8, "geometry_tolerance_m": 1e-7},
        }
        with self.assertRaises(GeometryInputError):
            compute_usable_area(case)

    def test_geometry_engine_rejects_boolean_geojson_coordinate(self):
        case = {
            "field": {"type": "Polygon", "coordinates": [[[False, 0], [10, 0], [10, 10], [0, 10], [False, 0]]]},
            "obstacles": [],
            "settings": {"boundary_setback_m": 0, "obstacle_buffer_m": 0, "quad_segs": 8, "geometry_tolerance_m": 1e-7},
        }
        with self.assertRaises(GeometryInputError):
            compute_usable_area(case)

    def _valid_plan(self):
        layout = {
            "phase_a": 0.25,
            "phase_b": 0.5,
            "accepted_i": [0, 1, -2],
            "accepted_j": [0, -1, 3],
        }
        points, metadata = build_rational_lattice_plan(layout, 2, 3, 30.0, 2)
        return points, metadata

    def test_valid_exact_rational_lattice_passes(self):
        points, metadata = self._valid_plan()
        result = verify_rational_lattice_relation(points, metadata)
        self.assertEqual(result["status"], "CERTIFIED_RATIONAL_LATTICE")
        self.assertTrue(result["pairwise_spacing_property_certified"])
        self.assertEqual(result["minimum_pairwise_spacing_lower_bound_m"], "2/1")

    def test_lattice_builder_rejects_fractional_index_instead_of_truncating(self):
        layout = {"phase_a": 0.1, "phase_b": 0.2, "accepted_i": [0.7], "accepted_j": [0]}
        with self.assertRaises(CertificateInputError):
            build_rational_lattice_plan(layout, 2, 3, 20.0, 1)

    def test_lattice_builder_rejects_boolean_index(self):
        layout = {"phase_a": 0.1, "phase_b": 0.2, "accepted_i": [True], "accepted_j": [0]}
        with self.assertRaises(CertificateInputError):
            build_rational_lattice_plan(layout, 2, 3, 20.0, 1)

    def test_lattice_builder_rejects_non_integer_plants_per_hole(self):
        layout = {"phase_a": 0.1, "phase_b": 0.2, "accepted_i": [0], "accepted_j": [0]}
        with self.assertRaises(CertificateInputError):
            build_rational_lattice_plan(layout, 2, 3, 20.0, 1.5)

    def test_lattice_verifier_rejects_fractional_index_instead_of_truncating(self):
        points, metadata = self._valid_plan()
        points[0]["lattice_i"] = 0.9
        result = verify_rational_lattice_relation(points, metadata)
        self.assertEqual(result["status"], "HOLD_LATTICE_RELATION_FAILED")
        self.assertFalse(result["certified"])

    def test_lattice_verifier_rejects_non_positive_spacing(self):
        points, metadata = self._valid_plan()
        metadata["spacing_a_m"] = "-2/1"
        result = verify_rational_lattice_relation(points, metadata)
        self.assertEqual(result["status"], "HOLD_LATTICE_RELATION_FAILED")
        self.assertFalse(result["certified"])
        self.assertIsNone(result["minimum_pairwise_spacing_lower_bound_m"])

    def test_lattice_verifier_rejects_phase_outside_unit_interval(self):
        points, metadata = self._valid_plan()
        metadata["phase_a"] = "3/2"
        result = verify_rational_lattice_relation(points, metadata)
        self.assertEqual(result["status"], "HOLD_LATTICE_RELATION_FAILED")
        self.assertFalse(result["certified"])

    def test_lattice_verifier_rejects_inconsistent_rotation_metadata(self):
        points, metadata = self._valid_plan()
        metadata["rotation_cos"] = "0/1"
        result = verify_rational_lattice_relation(points, metadata)
        self.assertEqual(result["status"], "HOLD_LATTICE_RELATION_FAILED")
        self.assertFalse(result["certified"])

    def test_empty_usable_geometry_returns_hold_instead_of_crashing(self):
        case = {"field": {"vertices": [[0, 0], [1, 0], [1, 1], [0, 1]]},
                "crop": {"row_spacing_m": 3.0, "in_row_spacing_m": 2.0,
                         "plants_per_hole_after_thinning": 1},
                "settings": {}, "obstacles": []}
        result = run_adaptive_solver(case, Polygon(), (0.0, 0.0, 1.0, 1.0),
                                     max_wall_time_seconds=1.0,
                                     max_grid_evaluations=16,
                                     allow_phase_arrangement=False,
                                     allow_orientation_bnb=False)
        self.assertEqual(result["status"], "HOLD_NO_FEASIBLE_CANDIDATE_FOUND")
        self.assertEqual(result["no_candidate_reason"], "USABLE_GEOMETRY_EMPTY")
        self.assertEqual(result["best_found_count"], 0)
        self.assertEqual(result["planting_positions"], [])
        self.assertFalse(result["optimality"]["proven"])
        self.assertFalse(result["field_deployment_authorized"])

    def test_nonempty_but_missed_search_returns_nonproof_hold(self):
        case = {"field": {"vertices": [[0, 0], [10, 0], [10, 10], [0, 10]]},
                "crop": {"row_spacing_m": 3.0, "in_row_spacing_m": 2.0,
                         "plants_per_hole_after_thinning": 1},
                "settings": {"boundary_setback_m": 0, "obstacle_buffer_m": 0},
                "obstacles": []}
        result = run_adaptive_solver(case, box(0.1, 0.1, 0.11, 0.11), (0.0, 0.0, 10.0, 10.0),
                                     max_wall_time_seconds=1.0, max_grid_evaluations=16,
                                     phase_divisions_cap=2, allow_phase_arrangement=False,
                                     allow_orientation_bnb=False)
        self.assertEqual(result["status"], "HOLD_NO_FEASIBLE_CANDIDATE_FOUND")
        self.assertEqual(result["no_candidate_reason"], "SEARCH_DID_NOT_FIND_A_FEASIBLE_SITE")
        self.assertEqual(result["best_found_count"], 0)
        self.assertEqual(result["certified_upper_bound"]["upper_bound_count"], 1)
        self.assertFalse(result["optimality"]["proven"])

    def test_empty_usable_geometry_pipeline_is_reported_as_hold(self):
        root = Path(__file__).resolve().parents[1]
        app = json.loads((root / "adapter" / "sample_app_project.json").read_text(encoding="utf-8"))
        profile = json.loads((root / "adapter" / "sample_site_profile.json").read_text(encoding="utf-8"))
        tiny = [[0, 0], [0.1, 0], [0.1, 0.1], [0, 0.1]]
        app["boundary"]["sourceVertices"] = tiny
        app["boundary"]["workingVertices"] = tiny
        profile["settings"]["boundary_setback_m"] = 1.0
        profile["settings"]["obstacle_buffer_m"] = 0.0
        with tempfile.TemporaryDirectory() as tmp:
            app_path = Path(tmp) / "app.json"
            profile_path = Path(tmp) / "profile.json"
            app_path.write_text(json.dumps(app), encoding="utf-8")
            profile_path.write_text(json.dumps(profile), encoding="utf-8")
            report = run_pipeline_v03(app_path, profile_path, Path(tmp) / "out",
                                      mode="exploratory", max_wall_time_seconds=1.0,
                                      max_grid_evaluations=16, allow_phase_arrangement=False,
                                      allow_orientation_bnb=False)
        self.assertEqual(report["pipeline_status"], "HOLD_EMPTY_USABLE_GEOMETRY")
        self.assertFalse(report["verification"]["all_formal_checks_passed"])
        self.assertEqual(report["optimization"]["best_found_count"], 0)
        self.assertFalse(report["field_deployment_authorized"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
