import tempfile
import unittest
from pathlib import Path
from engine.pipeline_runner_v03 import run_pipeline_v03

ROOT=Path(__file__).resolve().parents[1]

class PipelineRunnerV03Tests(unittest.TestCase):
    def test_sample_pipeline_emits_feasibility_and_bound_evidence(self):
        with tempfile.TemporaryDirectory() as td:
            r=run_pipeline_v03(ROOT/'adapter'/'sample_app_project.json',ROOT/'adapter'/'sample_site_profile.json',
                               Path(td),mode='exploratory',max_wall_time_seconds=3,max_grid_evaluations=144,
                               allow_phase_arrangement=True,allow_orientation_bnb=False)
            self.assertEqual(r['pipeline_status'],'SYNTHETIC_PIPELINE_PASS_FEASIBILITY_CERTIFIED_EXPLORATORY_ONLY')
            self.assertFalse(r['field_deployment_authorized'])
            self.assertEqual(r['verification']['all_formal_checks_passed'],True)
            self.assertEqual(r['optimization']['best_found_count'],70)
            self.assertEqual(r['optimization']['upper_bound_count'],77)
            self.assertTrue((Path(td)/'evidence_report.json').exists())

    def test_multipolygon_hole_pipeline(self):
        with tempfile.TemporaryDirectory() as td:
            r=run_pipeline_v03(ROOT/'fixtures'/'multipolygon_hole_app_project.json',
                               ROOT/'fixtures'/'multipolygon_hole_site_profile.json',Path(td),
                               mode='exploratory',max_wall_time_seconds=3,max_grid_evaluations=64,
                               allow_phase_arrangement=True,allow_orientation_bnb=False)
            self.assertEqual(r['pipeline_status'],'SYNTHETIC_PIPELINE_PASS_FEASIBILITY_CERTIFIED_EXPLORATORY_ONLY')
            self.assertTrue(r['verification']['all_formal_checks_passed'])
            self.assertEqual(r['geometry']['source_field_geometry']['type'],'MultiPolygon')

if __name__=='__main__': unittest.main(verbosity=2)
