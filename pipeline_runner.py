#!/usr/bin/env python3
"""Reproducible Adapter -> Geometry -> Optimization -> two Verifiers -> Evidence pipeline.

The runner is intentionally marked exploratory: it never authorizes field use.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
import platform
import sys
from pathlib import Path
from typing import Any

import numpy
import shapely

from handoff_adapter import adapt_project
from geometry_engine_v02 import compute_usable_area
from optimization_engine_v04 import run_benchmarks
from reference_verifier import verify_plan_reference
from shapely_verifier import verify_plan_shapely
from engine_safety import compare_verifier_results, classify_optimality


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def _sha256_obj(obj: Any) -> str:
    raw = json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()
    return hashlib.sha256(raw).hexdigest()


def _write_json(path: Path, obj: Any) -> None:
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')


def run_pipeline(app_path: Path, profile_path: Path, out_dir: Path, *, mode: str = 'exploratory',
                 angle_step_deg: float = 30.0, phase_divisions: int = 3,
                 refine: bool = False, comparison_lattices: bool = True) -> dict:
    app_doc = json.loads(app_path.read_text(encoding='utf-8'))
    profile = json.loads(profile_path.read_text(encoding='utf-8'))
    case, audit = adapt_project(app_doc, profile, mode=mode)
    geom = compute_usable_area(case)
    optimized = run_benchmarks(case, angle_step_deg=angle_step_deg,
                               phase_divisions=phase_divisions, refine=refine,
                               run_comparison_lattices=comparison_lattices)
    result = optimized['result']

    ref_result = verify_plan_reference(case, result)
    geos_result = verify_plan_shapely(case, result)
    agreement = compare_verifier_results(ref_result, geos_result)

    rect_search = result['search']['rectangular_crop_row']
    best_found = int(rect_search['best_count'])
    upper_bound = int(rect_search['upper_bound_count'])
    ub_certified = bool(rect_search.get('upper_bound_certified', False))
    has_points = bool(result.get('planting_positions'))
    both_verifiers_pass = (ref_result.get('all_checks_passed') is True and
                           geos_result.get('all_checks_passed') is True and
                           agreement.get('status') == 'AGREE')
    optimality_status = classify_optimality(
        best_found, upper_bound, has_points, ub_certified, both_verifiers_pass,
        feasibility_formally_certified=False
    )

    geom_status = geom['result']['status']
    geom_ok = (geom_status.get('usable_area_calculated') is True and
               geom_status.get('boundary_clearance_verified') is True and
               geom_status.get('obstacle_clearance_verified') is True and
               geom['result']['geometry']['usable_geometry_valid'] is True)
    if agreement.get('status') != 'AGREE':
        pipeline_status = 'HOLD_VERIFIER_DISAGREEMENT'
    elif not both_verifiers_pass:
        pipeline_status = 'HOLD_FEASIBILITY_VERIFICATION_FAILED'
    elif not geom_ok:
        pipeline_status = 'HOLD_GEOMETRY_CHECK_FAILED'
    else:
        pipeline_status = 'SYNTHETIC_PIPELINE_PASS_EXPLORATORY_ONLY'

    source_files = [
        Path(__file__), Path(__file__).with_name('geometry_engine_v02.py'),
        Path(__file__).with_name('optimization_engine_v04.py'),
        Path(__file__).with_name('reference_verifier.py'),
        Path(__file__).with_name('shapely_verifier.py'),
        Path(__file__).with_name('engine_safety.py'),
        Path(__file__).with_name('certified_upper_bound.py'),
        Path(__file__).resolve().parents[1] / 'adapter' / 'handoff_adapter.py',
    ]
    source_hashes = {str(p.relative_to(Path(__file__).resolve().parents[1])): _sha256_file(p) for p in source_files}
    run_id = _sha256_obj({'app': audit['input_hashes']['app_project_sha256'],
                          'profile': audit['input_hashes']['site_profile_sha256'],
                          'engine_sources': source_hashes,
                          'search': {'angle_step_deg': angle_step_deg,
                                     'phase_divisions': phase_divisions,
                                     'refine': refine,
                                     'comparison_lattices': comparison_lattices}})[:16]

    report = {
        'project': 'PROUVÉ Spatial',
        'engine_branch': 'Engine Branch V0.2',
        'run_id': run_id,
        'pipeline_status': pipeline_status,
        'mode': mode,
        'gate_status': audit['gate_status'],
        'field_deployment_authorized': False,
        'scope_notice': 'Synthetic/exploratory integration evidence only. Not a field validation, agronomic recommendation, exact-geometry certificate, or continuous/global optimum proof.',
        'environment': {'python': sys.version.split()[0], 'platform': platform.platform(),
                        'numpy': numpy.__version__, 'shapely': shapely.__version__},
        'source_hashes': source_hashes,
        'input_hashes': audit['input_hashes'],
        'engine_case_sha256': audit['engine_case_sha256'],
        'geometry': {
            'areas_m2': geom['result']['areas_m2'],
            'geometry_status': geom['result']['status'],
            'geometry_checks': geom['result']['geometry'],
            'usable_area_valid': geom['result']['geometry']['usable_geometry_valid'],
        },
        'optimization': {
            'best_found_count': best_found,
            'upper_bound_count': upper_bound,
            'upper_bound_count_estimate': result['optimality_evidence']['legacy_geos_estimate'].get('legacy_estimate_count'),
            'upper_bound_certified': ub_certified,
            'upper_bound_status': result['optimality_evidence'].get('upper_bound_status'),
            'upper_bound_method': result['optimality_evidence'].get('upper_bound_method'),
            'optimality_status_after_checks': optimality_status,
            'best_over_finite_declared_search_grid': True,
            'continuous_lattice_optimum_proven': False,
            'evaluated_layouts': rect_search['evaluated_layouts'],
            'angle_step_deg': angle_step_deg,
            'phase_divisions': phase_divisions,
            'relative_gap_to_certified_upper_bound': rect_search.get('relative_gap_to_upper_bound'),
            'elapsed_seconds': rect_search['elapsed_seconds'],
        },
        'verification': {'reference_no_shapely': ref_result,
                         'shapely_geos': geos_result,
                         'agreement': agreement,
                         'both_passed': both_verifiers_pass},
        'input_gate_warnings': audit.get('warnings', []),
        'notices': [
            'APP boundary USER_CONFIRMED is exploratory and is not survey-certified.',
            'Certified upper bound applies to the represented polygon and ideal lattice family; candidate feasibility remains numerical, so no optimum certificate is issued.',
            'Reference verifier supports simple hole-free polygon rings and rectangular lattice only.',
            'Shapely verifier shares GEOS with Geometry Engine; it complements but does not replace the no-Shapely reference verifier.',
            'Field validation, GNSS calibration, agronomist approval and farmer usability study remain pending.',
        ],
    }

    out_dir.mkdir(parents=True, exist_ok=True)
    _write_json(out_dir / 'engine_case.json', case)
    _write_json(out_dir / 'handoff_audit.json', audit)
    _write_json(out_dir / 'optimization_output.json', result)
    _write_json(out_dir / 'geometry_output.json', geom['result'])
    _write_json(out_dir / 'reference_verification.json', ref_result)
    _write_json(out_dir / 'shapely_verification.json', geos_result)
    _write_json(out_dir / 'verifier_agreement.json', agreement)
    _write_json(out_dir / 'evidence_report.json', report)
    with (out_dir / 'planting_positions.csv').open('w', newline='', encoding='utf-8-sig') as f:
        fields = ['plant_id', 'lattice_i', 'lattice_j', 'x_m', 'y_m', 'plants_in_hole']
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(result['planting_positions'])
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description='Run PROUVE Spatial Engine Branch V0.1 integration pipeline')
    parser.add_argument('app_project', type=Path)
    parser.add_argument('site_profile', type=Path)
    parser.add_argument('--out-dir', type=Path, default=Path('pipeline_output'))
    parser.add_argument('--mode', choices=('demo', 'exploratory', 'field_candidate'), default='exploratory')
    parser.add_argument('--angle-step', type=float, default=30.0)
    parser.add_argument('--phase-divisions', type=int, default=3)
    parser.add_argument('--refine', action='store_true')
    parser.add_argument('--no-comparison-lattices', action='store_true')
    args = parser.parse_args()
    report = run_pipeline(args.app_project, args.site_profile, args.out_dir, mode=args.mode,
                          angle_step_deg=args.angle_step, phase_divisions=args.phase_divisions,
                          refine=args.refine, comparison_lattices=not args.no_comparison_lattices)
    print(json.dumps({'run_id': report['run_id'], 'pipeline_status': report['pipeline_status'],
                      'best_found_count': report['optimization']['best_found_count'],
                      'upper_bound_count': report['optimization']['upper_bound_count'],
                      'upper_bound_count_estimate': report['optimization']['upper_bound_count_estimate'],
                      'optimality_status': report['optimization']['optimality_status_after_checks'],
                      'verification_agreement': report['verification']['agreement']['status'],
                      'field_deployment_authorized': report['field_deployment_authorized']}, ensure_ascii=False, indent=2))
    return 0 if report['pipeline_status'] == 'SYNTHETIC_PIPELINE_PASS_EXPLORATORY_ONLY' else 2


if __name__ == '__main__':
    raise SystemExit(main())
