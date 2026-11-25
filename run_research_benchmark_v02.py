#!/usr/bin/env python3
from __future__ import annotations
import csv
import json
import math
import statistics
import subprocess
import sys
import time
import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'engine'), str(ROOT/'prototype'), str(ROOT/'tests')]
from test_geometry_stress import build_stress_cases
from geometry_engine_v02 import compute_usable_area, GeometryInputError
from optimization_engine_v04 import _make_specs, search_lattice, lattice_upper_bound
from continuous_lattice_bnb import optimize_rectangular_lattice, _candidate_index_ranges, _count_layout, SearchInputError
from exact_phase_arrangement import optimize_phase_fixed_orientation, PhaseArrangementError
from reference_verifier import verify_plan_reference
from shapely_verifier import verify_plan_shapely

OUT = ROOT/'reports/research_benchmark_v0_2'
OUT.mkdir(parents=True, exist_ok=True)


def phase_grid(poly, theta, spacing_a, spacing_b, divisions):
    ranges, center = _candidate_index_ranges(poly, spacing_a, spacing_b)
    best = 0
    best_phase = (0.0, 0.0)
    started = time.perf_counter()
    for ai in range(divisions):
        for bi in range(divisions):
            pa, pb = ai/divisions, bi/divisions
            count = _count_layout(poly, theta, pa, pb, spacing_a, spacing_b, center, ranges)
            if (count, -pa, -pb) > (best, -best_phase[0], -best_phase[1]):
                best, best_phase = count, (pa, pb)
    return {'best_count': best, 'best_phase_a': best_phase[0], 'best_phase_b': best_phase[1],
            'evaluated_layouts': divisions*divisions, 'elapsed_seconds': time.perf_counter()-started}


def repeated_lattice_grid(usable, bounds, spec, *, angle_step=60, phase_divisions=4, repeats=3):
    runs = [search_lattice(usable, bounds, spec, angle_step_deg=angle_step,
                           phase_divisions=phase_divisions, refine=False)
            for _ in range(repeats)]
    med = statistics.median(x['elapsed_seconds'] for x in runs)
    result = dict(runs[0])
    result['elapsed_seconds'] = med
    result['elapsed_seconds_trials'] = [x['elapsed_seconds'] for x in runs]
    result['timing_repeats'] = repeats
    return result


def repeated_phase_grid(poly, theta, spacing_a, spacing_b, divisions, repeats=3):
    runs = [phase_grid(poly, theta, spacing_a, spacing_b, divisions) for _ in range(repeats)]
    med = statistics.median(x['elapsed_seconds'] for x in runs)
    result = dict(runs[0])
    result['elapsed_seconds'] = med
    result['elapsed_seconds_trials'] = [x['elapsed_seconds'] for x in runs]
    result['timing_repeats'] = repeats
    return result


def run_case(name, case):
    record = {'case': name, 'geometry_status': None, 'usable_area_m2': None,
              'component_count': None, 'certified_ub': None, 'stress_notes': []}
    try:
        geo = compute_usable_area(case)
    except GeometryInputError as exc:
        record['geometry_status'] = 'SAFE_REJECT'
        record['stress_notes'].append(str(exc))
        return record
    usable = geo['geometries']['usable']
    record['geometry_status'] = 'PASS' if geo['result']['geometry']['usable_geometry_valid'] else 'FAIL'
    record['usable_area_m2'] = geo['result']['areas_m2']['usable_planting_area']
    record['component_count'] = geo['result']['geometry']['usable_component_count']
    if usable.is_empty:
        record['geometry_status'] = 'PASS_EMPTY_USABLE_AREA'
        crop = case['crop']
        spec = _make_specs(crop['row_spacing_m'], crop['in_row_spacing_m'])['rectangular_crop']
        ub = lattice_upper_bound(usable, spec)
        record['certified_ub'] = {'count': ub['upper_bound_count'], 'certified': ub['upper_bound_certified'],
                                  'method': ub['bound_method'], 'legacy_geos_estimate': ub['legacy_geos_estimate']['legacy_estimate_count']}
        record['stress_notes'].append('Setback/clearance leaves no feasible area; no placement plan is produced. Certified upper bound is zero.')
        return record

    crop = case['crop']
    spec = _make_specs(crop['row_spacing_m'], crop['in_row_spacing_m'])['rectangular_crop']
    ub = lattice_upper_bound(usable, spec)
    record['certified_ub'] = {
        'count': ub['upper_bound_count'], 'certified': ub['upper_bound_certified'],
        'method': ub['bound_method'], 'legacy_geos_estimate': ub['legacy_geos_estimate']['legacy_estimate_count']
    }

    # First establish a stable wall-clock budget from three deterministic grid runs.
    # BnB then receives that same time budget; it may exceed it by at most one
    # uninterruptible interval-node bound evaluation, which is reported explicitly.
    bounds = (min(p[0] for p in case['field']['vertices']),
              min(p[1] for p in case['field']['vertices']),
              max(p[0] for p in case['field']['vertices']),
              max(p[1] for p in case['field']['vertices']))
    grid = repeated_lattice_grid(usable, bounds, spec, angle_step=60, phase_divisions=4, repeats=3)
    bnb_eval = None
    bnb_eval_error = None
    bnb_time = None
    bnb_time_error = None
    try:
        # Evaluation-budget comparison: 12 seed evaluations + up to 4 BnB nodes
        # (nine incumbent samples per expanded node), typically 48 layouts.
        bnb_eval = optimize_rectangular_lattice(
            usable, crop['in_row_spacing_m'], crop['row_spacing_m'],
            max_nodes=4, seed_grid_angle_step=60, seed_phase_divisions=2,
            max_candidate_indices=50000)
    except SearchInputError as exc:
        bnb_eval_error = str(exc)
    try:
        # Wall-clock comparison with the median time of three grid runs.
        bnb_time = optimize_rectangular_lattice(
            usable, crop['in_row_spacing_m'], crop['row_spacing_m'],
            max_nodes=100000, seed_grid_angle_step=60, seed_phase_divisions=2,
            max_candidate_indices=50000, time_budget_seconds=grid['elapsed_seconds'])
    except SearchInputError as exc:
        bnb_time_error = str(exc)

    record['orientation_phase_equal_budget'] = {
        'grid': {'best_count': grid['best_count'], 'evaluated_layouts': grid['coarse_layouts'],
                 'elapsed_seconds_median': grid['elapsed_seconds'],
                 'elapsed_seconds_trials': grid['elapsed_seconds_trials'],
                 'timing_repeats': grid['timing_repeats'], 'theta_deg': grid['best_theta_deg'],
                 'phase_a': grid['best_phase_a'], 'phase_b': grid['best_phase_b']},
        'bnb_equal_layout_evaluation_budget': ({
            'best_count': bnb_eval['best_found_count'], 'evaluated_layouts': bnb_eval['evaluated_layouts'],
            'processed_nodes': bnb_eval['processed_nodes'], 'upper_bound_count': bnb_eval['upper_bound_count'],
            'candidate_index_envelope_size': bnb_eval.get('candidate_index_envelope_size'),
            'status': bnb_eval['status'], 'elapsed_seconds': bnb_eval['elapsed_seconds'],
            'theta_deg': bnb_eval['best_theta_deg'], 'phase_a': bnb_eval['best_phase_a'],
            'phase_b': bnb_eval['best_phase_b'], 'numeric_note': bnb_eval['numeric_note']
        } if bnb_eval is not None else {'status': 'SKIPPED_CANDIDATE_INDEX_EXPLOSION', 'reason': bnb_eval_error}),
        'bnb_wall_clock_budget': ({
            'best_count': bnb_time['best_found_count'], 'evaluated_layouts': bnb_time['evaluated_layouts'],
            'processed_nodes': bnb_time['processed_nodes'], 'upper_bound_count': bnb_time['upper_bound_count'],
            'absolute_gap': bnb_time['absolute_gap'], 'status': bnb_time['status'],
            'elapsed_seconds': bnb_time['elapsed_seconds'], 'time_budget_seconds': bnb_time.get('time_budget_seconds'),
            'candidate_index_envelope_size': bnb_time.get('candidate_index_envelope_size'),
            'theta_deg': bnb_time['best_theta_deg'], 'phase_a': bnb_time['best_phase_a'],
            'phase_b': bnb_time['best_phase_b'], 'numeric_note': bnb_time['numeric_note']
        } if bnb_time is not None else {'status': 'SKIPPED_CANDIDATE_INDEX_EXPLOSION', 'reason': bnb_time_error}),
        'budget_note': ('Two comparisons are reported. First, BnB is limited to four nodes and its actual incumbent layout evaluations are counted against the 48-layout uniform grid; node-bound geometry work is additional and reflected in elapsed time. '
                        'Second, BnB receives the median wall-clock runtime of three grid runs; the actual runtime may exceed the target by one uninterruptible layout or node-bound operation and is reported. '
                        'BnB numeric upper bounds use platform libm trigonometric calculations and are not formal certificates.')
    }

    # Verify both BnB winners under the independent reference and GEOS checkers.
    def verify_bnb_candidate(search_result):
        from optimization_engine_v04 import enumerate_layout, _make_points
        candidate = enumerate_layout(usable, bounds, spec, search_result['best_theta_deg'],
                                     search_result['best_phase_a'], search_result['best_phase_b'], include_points=True)
        plan = {
            'search': {'rectangular_crop_row': {
                'best_count': candidate['count'], 'best_theta_deg': search_result['best_theta_deg'],
                'best_phase_a_fraction': search_result['best_phase_a'], 'best_phase_b_fraction': search_result['best_phase_b']}},
            'planting_positions': _make_points(candidate, crop['plants_per_hole_after_thinning'])
        }
        ref = verify_plan_reference(case, plan)
        geos = verify_plan_shapely(case, plan)
        return {'reference_passed': ref.get('all_checks_passed'),
                'shapely_passed': geos.get('all_checks_passed'),
                'counts_agree': ref.get('verified_point_count') == geos.get('verified_point_count') == candidate['count'],
                'regenerated_count': candidate['count'],
                'search_count_matches': candidate['count'] == search_result['best_found_count']}

    if bnb_eval is not None:
        try:
            record['orientation_phase_equal_budget']['bnb_equal_layout_candidate_verification'] = verify_bnb_candidate(bnb_eval)
        except Exception as exc:
            record['orientation_phase_equal_budget']['bnb_equal_layout_candidate_verification'] = {'error': str(exc)}
    if bnb_time is not None:
        try:
            record['orientation_phase_equal_budget']['bnb_wall_clock_candidate_verification'] = verify_bnb_candidate(bnb_time)
        except Exception as exc:
            record['orientation_phase_equal_budget']['bnb_wall_clock_candidate_verification'] = {'error': str(exc)}

    # Fixed-orientation arrangement versus uniform phase grids.
    theta = grid['best_theta_deg']
    try:
        arr_runs = [optimize_phase_fixed_orientation(usable, crop['in_row_spacing_m'],
                                                      crop['row_spacing_m'], theta,
                                                      max_boundary_fragments=600)
                    for _ in range(3)]
        arr = dict(arr_runs[0])
        arr['elapsed_seconds_trials'] = [x['elapsed_seconds'] for x in arr_runs]
        arr['elapsed_seconds'] = statistics.median(x['elapsed_seconds'] for x in arr_runs)
        arr['timing_repeats'] = 3
        m = arr['tested_phase_points']
        d = max(2, math.isqrt(m))
        equal_grid = repeated_phase_grid(usable, theta, crop['in_row_spacing_m'], crop['row_spacing_m'], d, repeats=3)
        dense_grid = phase_grid(usable, theta, crop['in_row_spacing_m'], crop['row_spacing_m'], 40)
        record['fixed_orientation_phase'] = {
            'theta_deg': theta,
            'arrangement': {'best_count': arr['max_count'], 'candidate_phases': arr['tested_phase_points'],
                            'boundary_fragments': arr['phase_pieces'], 'faces': arr['arrangement_faces'],
                            'segments': arr['arrangement_segments'], 'elapsed_seconds': arr['elapsed_seconds'],
                            'status': arr['status']},
            'uniform_grid_near_equal_budget': {'best_count': equal_grid['best_count'],
                                               'candidate_phases': equal_grid['evaluated_layouts'],
                                               'elapsed_seconds_median': equal_grid['elapsed_seconds'],
                                               'elapsed_seconds_trials': equal_grid['elapsed_seconds_trials'],
                                               'timing_repeats': equal_grid['timing_repeats'],
                                               'divisions_per_axis': d},
            'uniform_grid_40x40': {'best_count': dense_grid['best_count'],
                                   'candidate_phases': dense_grid['evaluated_layouts'],
                                   'elapsed_seconds': dense_grid['elapsed_seconds'],
                                   'timing_repeats': 1},
            'arrangement_vs_equal_budget_delta': arr['max_count'] - equal_grid['best_count'],
            'arrangement_vs_40x40_delta': arr['max_count'] - dense_grid['best_count'],
            'interpretation': 'Arrangement is an all-phase candidate method for this fixed orientation only; topology remains floating-point and is not formally exact.'
        }
    except PhaseArrangementError as exc:
        record['fixed_orientation_phase'] = {
            'status': 'SKIPPED_COMPLEXITY_CAP', 'reason': str(exc),
            'fallback': 'Use angle-phase grid or bounded adaptive search; do not force arrangement.'
        }
    return record


def _write_reports(results):
    doc = {
        'project': 'PROUVÉ Spatial', 'branch': 'Engine Branch V0.2',
        'benchmark_type': 'synthetic research comparison; not field validation',
        'environment': {'python': sys.version.split()[0]},
        'orientation_phase_budget_method': 'both equal-layout-evaluation and wall-clock-target comparisons; actual elapsed and possible one-operation overshoot recorded',
        'results': results,
        'global_limitations': [
            'All geometries and crop spacing profiles are synthetic.',
            'Grid is finite and does not prove the continuous optimum.',
            'The BnB node upper bound uses platform libm trigonometric intervals and is not a formal certificate.',
            'Phase arrangement is only for a fixed orientation, capped at 600 clipped boundary fragments, and relies on floating-point topology.',
            'Certified Steiner bound is a mathematically valid upper bound for the ideal Euclidean lattice over the represented polygonal feasible geometry; candidate feasibility is still numeric, so no optimum certificate is issued.',
            'An extreme absolute coordinate offset is deliberately rejected when its floating-point ULP exceeds the declared geometric tolerance.',
            'Each stress case is run in a fresh Python worker process to limit geometry-kernel memory/cache carry-over.'
        ]
    }
    (OUT/'research_benchmark_v0_2.json').write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding='utf-8')
    with (OUT/'research_benchmark_v0_2.csv').open('w', newline='', encoding='utf-8-sig') as f:
        fields = ['case','geometry_status','usable_area_m2','component_count','certified_ub',
                  'grid_count','grid_evaluations','grid_seconds_median','bnb_equal_count','bnb_equal_evaluations','bnb_equal_seconds',
                  'bnb_time_count','bnb_time_evaluations','bnb_time_seconds','bnb_time_budget','bnb_time_status',
                  'phase_arrangement_status','phase_arrangement_count','phase_arrangement_phases',
                  'phase_equal_grid_count','phase_equal_grid_phases','phase_40x40_count','phase_arrangement_seconds_median']
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
        for r in results:
            of=r.get('orientation_phase_equal_budget',{})
            gr=of.get('grid',{});be=of.get('bnb_equal_layout_evaluation_budget',{});bt=of.get('bnb_wall_clock_budget',{})
            ph=r.get('fixed_orientation_phase',{})
            ar=ph.get('arrangement',{});eq=ph.get('uniform_grid_near_equal_budget',{});d40=ph.get('uniform_grid_40x40',{})
            w.writerow({'case':r['case'],'geometry_status':r['geometry_status'],'usable_area_m2':r.get('usable_area_m2'),
                         'component_count':r.get('component_count'),'certified_ub':(r.get('certified_ub') or {}).get('count'),
                         'grid_count':gr.get('best_count'),'grid_evaluations':gr.get('evaluated_layouts'),'grid_seconds_median':gr.get('elapsed_seconds_median'),
                         'bnb_equal_count':be.get('best_count'),'bnb_equal_evaluations':be.get('evaluated_layouts'),'bnb_equal_seconds':be.get('elapsed_seconds'),
                         'bnb_time_count':bt.get('best_count'),'bnb_time_evaluations':bt.get('evaluated_layouts'),'bnb_time_seconds':bt.get('elapsed_seconds'),
                         'bnb_time_budget':bt.get('time_budget_seconds'),'bnb_time_status':bt.get('status'),
                         'phase_arrangement_status':ph.get('status',ar.get('status')),
                         'phase_arrangement_count':ar.get('best_count'),'phase_arrangement_phases':ar.get('candidate_phases'),
                         'phase_equal_grid_count':eq.get('best_count'),'phase_equal_grid_phases':eq.get('candidate_phases'),
                         'phase_40x40_count':d40.get('best_count'),'phase_arrangement_seconds_median':ar.get('elapsed_seconds')})


def main():
    parser=argparse.ArgumentParser(description='Run per-field synthetic research benchmark; worker isolation is used by default.')
    parser.add_argument('--worker', choices=sorted(build_stress_cases().keys()))
    parser.add_argument('--cases', nargs='*', default=None)
    args=parser.parse_args()
    cases=build_stress_cases()
    if args.worker:
        result=run_case(args.worker,cases[args.worker])
        print(json.dumps(result,ensure_ascii=False,allow_nan=False))
        return

    selected=args.cases or ['concave_L', 'concave_U', 'radial_concave_24', 'many_obstacles_25',
                            'obstacle_dense_36', 'narrow_corridor', 'near_degenerate_sliver',
                            'near_touching_obstacles', 'large_projected_coords', 'tiny_scale',
                            'setback_erases_area', 'very_large_offset']
    unknown=set(selected)-set(cases)
    if unknown:
        parser.error(f'unknown case name(s): {sorted(unknown)}')
    results=[]
    for name in selected:
        print(f'[BENCH] start {name}',flush=True)
        proc=subprocess.run([sys.executable,str(Path(__file__).resolve()),'--worker',name],
                            check=False,capture_output=True,text=True)
        if proc.returncode != 0:
            raise RuntimeError(f'benchmark worker failed for {name}: {proc.stderr[-2000:]}')
        row=json.loads(proc.stdout)
        results.append(row)
        _write_reports(results)  # incremental checkpoint after each isolated case
        print(f"[BENCH] done {name} status={row['geometry_status']} grid={row.get('orientation_phase_equal_budget',{}).get('grid',{}).get('best_count')}",flush=True)
    print(json.dumps({'out_dir':str(OUT),'case_count':len(results),
                      'geometry_pass':sum(r['geometry_status']=='PASS' for r in results),
                      'empty_usable':sum(r['geometry_status']=='PASS_EMPTY_USABLE_AREA' for r in results),
                      'safe_reject':sum(r['geometry_status']=='SAFE_REJECT' for r in results),
                      'arrangement_completed':sum('arrangement' in r.get('fixed_orientation_phase',{}) for r in results),
                      'arrangement_skipped':sum(r.get('fixed_orientation_phase',{}).get('status')=='SKIPPED_COMPLEXITY_CAP' for r in results),
                      'orientation_budget_method':'equal layout evaluation count + time-matched BnB with isolated workers'},ensure_ascii=False,indent=2))

if __name__=='__main__':
    main()
