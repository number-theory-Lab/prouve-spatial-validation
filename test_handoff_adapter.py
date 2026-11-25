import unittest
from handoff_adapter import adapt_project, HandoffError


def app_doc(status="USER_CONFIRMED", crs="EPSG:32647"):
    vertices = [[500000, 1000000], [500020, 1000000], [500020, 1000020], [500000, 1000020]]
    doc = {
        "schema": "prouve-spatial-boundary-v0.5",
        "project": {"name": "Synthetic FTS test", "id": "SYNTH-01"},
        "boundary": {"status": status, "inputระบบพิกัด": crs, "workingระบบพิกัด": crs,
                     "units": "เมตร", "sourceVertices": vertices, "workingVertices": vertices,
                     "validation": {"valid": True}},
        "optimizerHandoff": {"acceptedForGeometryProcessing": True, "readyForFieldUse": status in ["USER_CONFIRMED", "SURVEY_VERIFIED"]},
        "surveyReference": None,
    }
    if status == "SURVEY_VERIFIED":
        doc["surveyReference"] = {"vertices": vertices, "crs": crs, "metadata": {"recordId": "SYN-SURVEY-01", "method": "Synthetic test", "date": "2026-11-25"}, "comparison": {"passed": True}}
    return doc


def profile(reviewed=False):
    review = {"status": "APPROVED", "reviewer": "Synthetic reviewer", "date": "2026-11-25"} if reviewed else {"status": "PENDING"}
    return {
        "profile_schema": "prouve-spatial-site-profile-v0.1", "profile_id": "SYN-PROFILE-01",
        "site": {"site_id": "SYNTH-01", "name": "synthetic fixture"},
        "settings": {"boundary_setback_m": 1.0, "obstacle_buffer_m": 1.0, "quad_segs": 64, "geometry_tolerance_m": 1e-7},
        "obstacles": [],
        "crop": {"profile_id": "SYN-CROP-01", "crop_name": "Synthetic crop", "row_spacing_m": 3.0,
                 "in_row_spacing_m": 2.0, "plants_per_hole_after_thinning": 1},
        "reviews": {"boundary": review, "obstacles": review, "settings": review, "crop": review, "uncertainty": review},
        "uncertainty": {"status": "APPROVED" if reviewed else "NOT_CALIBRATED"},
        "sources": ({"boundary": "synthetic survey source", "obstacles": "synthetic obstacle inspection", "settings": "synthetic reviewed settings", "crop": "synthetic agronomy profile"} if reviewed else {}),
    }


class HandoffTests(unittest.TestCase):
    def test_user_confirmed_is_exploratory_only(self):
        case, audit = adapt_project(app_doc(), profile(), mode="exploratory")
        self.assertEqual(audit["gate_status"], "EXPLORATORY_ONLY")
        self.assertFalse(audit["field_deployment_authorized"])
        self.assertEqual(case["crop"]["row_spacing_m"], 3.0)

    def test_draft_boundary_is_blocked(self):
        with self.assertRaises(HandoffError):
            adapt_project(app_doc("DRAFT"), profile(), mode="exploratory")

    def test_local_metric_not_allowed_as_real_site(self):
        with self.assertRaises(HandoffError):
            adapt_project(app_doc("USER_CONFIRMED", "LOCAL:METRE"), profile(), mode="exploratory")

    def test_missing_explicit_settings_is_blocked(self):
        p = profile(); del p["settings"]["obstacle_buffer_m"]
        with self.assertRaises(HandoffError):
            adapt_project(app_doc(), p, mode="exploratory")

    def test_empty_obstacles_must_be_explicit(self):
        p = profile(); del p["obstacles"]
        with self.assertRaises(HandoffError):
            adapt_project(app_doc(), p, mode="exploratory")

    def test_zero_or_negative_crop_spacing_is_blocked(self):
        p = profile(); p["crop"]["row_spacing_m"] = 0
        with self.assertRaises(HandoffError):
            adapt_project(app_doc(), p, mode="exploratory")

    def test_field_candidate_requires_survey_verified_and_reviews(self):
        with self.assertRaises(HandoffError):
            adapt_project(app_doc(), profile(reviewed=True), mode="field_candidate")
        with self.assertRaises(HandoffError):
            adapt_project(app_doc("SURVEY_VERIFIED"), profile(reviewed=False), mode="field_candidate")

    def test_reviewed_survey_verified_only_passes_input_gate(self):
        _, audit = adapt_project(app_doc("SURVEY_VERIFIED"), profile(reviewed=True), mode="field_candidate")
        self.assertEqual(audit["gate_status"], "INPUT_GATE_PASSED_NOT_FIELD_VALIDATED")
        self.assertTrue(audit["eligible_for_engine_run"])
        self.assertFalse(audit["field_deployment_authorized"])

    def test_field_candidate_needs_uncertainty_status_not_only_review_flag(self):
        p = profile(reviewed=True); p["uncertainty"]["status"] = "NOT_CALIBRATED"
        with self.assertRaises(HandoffError):
            adapt_project(app_doc("SURVEY_VERIFIED"), p, mode="field_candidate")

    def test_invalid_crs_is_blocked(self):
        with self.assertRaises(HandoffError):
            adapt_project(app_doc("USER_CONFIRMED", "EPSG:3857"), profile(), mode="exploratory")

    def test_field_candidate_requires_settings_reviewer(self):
        p = profile(reviewed=True); p["reviews"].pop("settings")
        with self.assertRaises(HandoffError):
            adapt_project(app_doc("SURVEY_VERIFIED"), p, mode="field_candidate")

    def test_nan_coordinate_is_blocked(self):
        doc = app_doc(); doc["boundary"]["workingVertices"][0][0] = float("nan")
        with self.assertRaises(HandoffError):
            adapt_project(doc, profile(), mode="exploratory")

    def test_invalid_source_coordinate_is_blocked(self):
        doc = app_doc(); doc["boundary"]["sourceVertices"][0][1] = float("inf")
        with self.assertRaises(HandoffError):
            adapt_project(doc, profile(), mode="exploratory")


if __name__ == "__main__":
    unittest.main(verbosity=2)
