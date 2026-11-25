#!/usr/bin/env python3
"""PROUVE Spatial V0.3 adapter-to-evidence pipeline with formal certificates."""
from __future__ import annotations
import argparse, csv, hashlib, json, platform, sys
from pathlib import Path
from typing import Any

import numpy
import shapely
from shapely.geometry import mapping

from handoff_adapter_v03 import adapt_project
from geometry_engine_v03 import compute_usable_area
from adaptive_solver import run_adaptive_solver


def _sha_file(p: Path) -> str:
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):
            h.update(b)
    return h.hexdigest()


def _sha_obj(obj: Any) -> str:
    raw=json.dumps(obj,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()
    return hashlib.sha256(raw).hexdigest()


def _write_json(p: Path, obj: Any) -> None:
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(obj,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8')


def run_pipeline_v03(app_path: Path, profile_path: Path, out_dir: Path, *, mode='exploratory',
                     max_wall_time_seconds=8.0, max_grid_evaluations=512,
                     allow_phase_arrangement=True, allow_orientation_bnb=True,
                     boundary_uncertainty_m=0, obstacle_uncertainty_m=0) -> dict:
    app_doc=json.loads(app_path.read_text(encoding='utf-8'))
    profile=json.loads(profile_path.read_text(encoding='utf-8'))
    case,audit=adapt_project(app_doc,profile,mode=mode)
    geom=compute_usable_area(case)
    adaptive=run_adaptive_solver(
        case,geom['geometries']['usable'],geom['geometries']['field'].bounds,
        max_wall_time_seconds=max_wall_time_seconds,
        max_grid_evaluations=max_grid_evaluations,
        allow_phase_arrangement=allow_phase_arrangement,
        allow_orientation_bnb=allow_orientation_bnb,
        boundary_uncertainty_m=boundary_uncertainty_m,
        obstacle_uncertainty_m=obstacle_uncertainty_m,
    )
    feasibility_ok=(adaptive['source_constraint_feasibility_certificate'].get('status')=='CERTIFIED_FEASIBLE' and
                    adaptive['represented_usable_geometry_feasibility_certificate'].get('status')=='CERTIFIED_FEASIBLE' and
                    adaptive['lattice_relation_verification'].get('status')=='CERTIFIED_RATIONAL_LATTICE')
    geometry_ok=(geom['result']['geometry']['usable_geometry_valid'] is True and
                 geom['result']['status']['boundary_clearance_verified'] is True and
                 geom['result']['status']['obstacle_clearance_verified'] is True)
    if not geometry_ok:
        status='HOLD_GEOMETRY_CHECK_FAILED'
    elif adaptive.get('status') == 'HOLD_NO_FEASIBLE_CANDIDATE_FOUND':
        if adaptive.get('no_candidate_reason') == 'USABLE_GEOMETRY_EMPTY':
            status='HOLD_EMPTY_USABLE_GEOMETRY'
        else:
            status='HOLD_NO_CANDIDATE_FOUND_WITHIN_SEARCH'
    elif not feasibility_ok:
        status='HOLD_FORMAL_FEASIBILITY_CERTIFICATE_FAILED'
    else:
        status='SYNTHETIC_PIPELINE_PASS_FEASIBILITY_CERTIFIED_EXPLORATORY_ONLY'
    source_files=[Path(__file__),Path(__file__).with_name('geometry_engine_v03.py'),
                  Path(__file__).with_name('adaptive_solver.py'),Path(__file__).with_name('formal_feasibility_certificate.py'),
                  Path(__file__).with_name('lattice_relation_certificate.py'),
                  Path(__file__).with_name('certified_upper_bound_v03.py'),
                  Path(__file__).parents[1]/'prototype'/'continuous_lattice_bnb.py',
                  Path(__file__).parents[1]/'prototype'/'exact_phase_arrangement.py',
                  Path(__file__).parents[1]/'adapter'/'handoff_adapter_v03.py']
    source_hashes={str(p.relative_to(Path(__file__).parents[1])):_sha_file(p) for p in source_files}
    field_geom = case.get('field',{})
    if isinstance(field_geom,dict) and 'geometry' in field_geom:
        source_geometry=field_geom['geometry']
    elif isinstance(field_geom,dict) and field_geom.get('type') in ('Polygon','MultiPolygon'):
        source_geometry=field_geom
    else:
        ring=list(field_geom.get('vertices',[]))
        if ring and ring[0]!=ring[-1]: ring.append(ring[0])
        source_geometry={'type':'Polygon','coordinates':[ring]}
    obstacle_geoms=[]
    for o in case.get('obstacles',[]):
        if 'geometry' in o: obstacle_geoms.append(o['geometry'])
        elif o.get('type') in ('Polygon','MultiPolygon'): obstacle_geoms.append({k:v for k,v in o.items() if k in ('type','coordinates')})
        else:
            ring=list(o.get('vertices',[]))
            if ring and ring[0]!=ring[-1]: ring.append(ring[0])
            obstacle_geoms.append({'type':'Polygon','coordinates':[ring]})
    usable_geojson=mapping(geom['geometries']['usable'])
    input_hashes={'app_project_sha256':_sha_file(app_path),'site_profile_sha256':_sha_file(profile_path),
                  'engine_case_sha256':_sha_obj(case)}
    run_id=_sha_obj({'input_hashes':input_hashes,'source_hashes':source_hashes,
                     'search_config':{'max_wall_time_seconds':max_wall_time_seconds,
                                      'max_grid_evaluations':max_grid_evaluations,
                                      'allow_phase_arrangement':allow_phase_arrangement,
                                      'allow_orientation_bnb':allow_orientation_bnb},
                     'selected_method':adaptive['selected_method'],
                     'candidate_set_sha256':adaptive['source_constraint_feasibility_certificate'].get('candidate_set_sha256')})[:16]
    ub=adaptive['certified_upper_bound']
    report={
        'project':'PROUVÉ Spatial', 'engine_branch':'Engine Branch V0.3.1', 'schema':'prouve-app-evidence-v0.3.1',
        'run_id':run_id,'pipeline_status':status,'mode':mode,
        'field_deployment_authorized':False,
        'scope_notice':'Synthetic/exploratory test only. Formal feasibility certifies the submitted finite rational lattice points relative to canonical decimal geometry and declared margins; it does not certify survey accuracy or agronomic suitability.',
        'environment':{'python':sys.version.split()[0],'platform':platform.platform(),'numpy':numpy.__version__,'shapely':shapely.__version__},
        'source_hashes':source_hashes,'input_hashes':input_hashes,
        'gate_status':audit.get('gate_status'),'input_gate_warnings':audit.get('warnings',[]),
        'geometry':{'areas_m2':geom['result']['areas_m2'],'geometry_checks':geom['result']['geometry'],
                    'geometry_status':geom['result']['status'],'source_field_geometry':source_geometry,
                    'source_obstacle_geometries':obstacle_geoms,'represented_usable_geometry':usable_geojson},
        'optimization':{'selected_method':adaptive['selected_method'],'best_found_count':adaptive['best_found_count'],
                        'theta_source_deg_display_only':adaptive['best_theta_deg'],
                        'evaluated_grid_layouts':adaptive['evaluated_grid_layouts'],
                        'compute_budget':adaptive['compute_budget'],'complexity':adaptive['complexity'],
                        'upper_bound_count':ub.get('upper_bound_count'),'upper_bound_certified':ub.get('certified') is True,
                        'upper_bound_status':ub.get('status'),'upper_bound_method':'Rational Steiner enclosure over decimalized represented usable geometry',
                        'relative_gap_to_certified_upper_bound':adaptive['optimality'].get('relative_gap_to_certified_upper_bound'),
                        'optimality_status':adaptive['optimality']['status'],'optimality_proven':adaptive['optimality']['proven'],
                        'optimality_scope':adaptive['optimality']['scope'],'method_attempts':adaptive['method_attempts']},
        'verification':{'rational_lattice_relation':adaptive['lattice_relation_verification'],
                        'source_constraint_feasibility':adaptive['source_constraint_feasibility_certificate'],
                        'represented_usable_geometry_feasibility':adaptive['represented_usable_geometry_feasibility_certificate'],
                        'all_formal_checks_passed':feasibility_ok},
        'rational_lattice':adaptive['rational_lattice_certificate'],
        'notices':adaptive['notices']+[
            'The finite search result is a lower bound. The certified upper bound applies to the declared rectangular lattice family over the decimalized represented usable polygon.',
            'An exact-feasibility certificate for a finite lattice candidate does not prove the candidate set is complete; equality with the certified upper bound is required for an optimum claim.',
            'Field deployment remains unauthorized pending survey/CRS/uncertainty QA and agronomist approval.'
        ],
    }
    out_dir.mkdir(parents=True,exist_ok=True)
    _write_json(out_dir/'engine_case.json',case)
    _write_json(out_dir/'geometry_output.json',geom['result'])
    _write_json(out_dir/'adaptive_result.json',adaptive)
    _write_json(out_dir/'evidence_report.json',report)
    _write_json(out_dir/'source_geometries.json',{'field':source_geometry,'obstacles':obstacle_geoms,'usable':usable_geojson})
    _write_json(out_dir/'feasibility_certificate_source.json',adaptive['source_constraint_feasibility_certificate'])
    _write_json(out_dir/'feasibility_certificate_usable.json',adaptive['represented_usable_geometry_feasibility_certificate'])
    _write_json(out_dir/'lattice_relation_certificate.json',adaptive['lattice_relation_verification'])
    _write_json(out_dir/'certified_upper_bound.json',ub)
    with (out_dir/'planting_positions.csv').open('w',newline='',encoding='utf-8-sig') as f:
        fields=['plant_id','lattice_i','lattice_j','x_m_display','y_m_display','x_m_exact_fraction','y_m_exact_fraction','plants_in_hole']
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
        for pt in adaptive['planting_positions']:
            w.writerow({'plant_id':pt['plant_id'],'lattice_i':pt['lattice_i'],'lattice_j':pt['lattice_j'],
                        'x_m_display':pt['x_m_display'],'y_m_display':pt['y_m_display'],
                        'x_m_exact_fraction':pt['x_m'],'y_m_exact_fraction':pt['y_m'],
                        'plants_in_hole':pt['plants_in_hole']})
    return report


def main():
    p=argparse.ArgumentParser(description='PROUVE Spatial Engine Branch V0.3 pipeline')
    p.add_argument('app_project',type=Path);p.add_argument('site_profile',type=Path)
    p.add_argument('--out-dir',type=Path,default=Path('reports/v0_3_pipeline'))
    p.add_argument('--mode',choices=('demo','exploratory','field_candidate'),default='exploratory')
    p.add_argument('--max-wall-time',type=float,default=8.0)
    p.add_argument('--max-grid-evaluations',type=int,default=512)
    p.add_argument('--no-arrangement',action='store_true');p.add_argument('--no-bnb',action='store_true')
    args=p.parse_args()
    r=run_pipeline_v03(args.app_project,args.site_profile,args.out_dir,mode=args.mode,
                       max_wall_time_seconds=args.max_wall_time,max_grid_evaluations=args.max_grid_evaluations,
                       allow_phase_arrangement=not args.no_arrangement,allow_orientation_bnb=not args.no_bnb)
    print(json.dumps({'run_id':r['run_id'],'pipeline_status':r['pipeline_status'],
                      'best_found_count':r['optimization']['best_found_count'],
                      'upper_bound_count':r['optimization']['upper_bound_count'],
                      'optimality_status':r['optimization']['optimality_status'],
                      'formal_checks_passed':r['verification']['all_formal_checks_passed'],
                      'field_deployment_authorized':r['field_deployment_authorized']},ensure_ascii=False,indent=2))
    return 0 if r['pipeline_status']=='SYNTHETIC_PIPELINE_PASS_FEASIBILITY_CERTIFIED_EXPLORATORY_ONLY' else 2

if __name__=='__main__': raise SystemExit(main())
