#!/usr/bin/env python3
"""Reproduce fixed-angle phase-arrangement vs 20x20 phase-grid micro-benchmark."""
import json, statistics, time
from pathlib import Path
from shapely.geometry import Polygon
from exact_phase_arrangement import optimize_phase_fixed_orientation
from continuous_lattice_bnb import _candidate_index_ranges, _count_layout, optimize_rectangular_lattice

polygons = [
    Polygon([(0,0),(10,0),(10,7),(0,7)]),
    Polygon([(0,0),(12,0),(12,8),(8,8),(8,5),(4,5),(4,8),(0,8)]),
    Polygon([(0,0),(9,0),(9,3),(5,3),(5,8),(0,8)]),
    Polygon([(0,0),(8,0),(10,4),(6,9),(1,7)]),
    Polygon([(0,0),(10,0),(9,5),(6,4),(4,7),(1,6)]),
]
spacings = [(2.0,2.5),(1.8,3.0),(2.2,1.7),(1.5,2.6),(2.4,3.1)]
angles = [0,15,37,82]
rows=[]
for shape_id,(poly,(spacing_a,spacing_b)) in enumerate(zip(polygons,spacings), start=1):
    index_ranges,center = _candidate_index_ranges(poly,spacing_a,spacing_b)
    for theta in angles:
        t0=time.perf_counter()
        arr=optimize_phase_fixed_orientation(poly,spacing_a,spacing_b,theta)
        arr_time=time.perf_counter()-t0
        t0=time.perf_counter(); grid_best=0; grid_phase=None
        for ia in range(20):
            for ib in range(20):
                count=_count_layout(poly,theta,ia/20,ib/20,spacing_a,spacing_b,center,index_ranges)
                if count>grid_best:
                    grid_best=count;grid_phase=(ia/20,ib/20)
        grid_time=time.perf_counter()-t0
        rows.append({"shape_id":shape_id,"theta_deg":theta,
                     "arrangement_count":arr["max_count"],
                     "arrangement_phase":[arr["best_phase_a"],arr["best_phase_b"]],
                     "grid20_count":grid_best,"grid20_phase":grid_phase,
                     "arrangement_points_tested":arr["tested_phase_points"],
                     "arrangement_pieces":arr["phase_pieces"],
                     "arrangement_seconds":arr_time,"grid20_seconds":grid_time,
                     "count_delta":arr["max_count"]-grid_best,
                     "runtime_ratio":arr_time/grid_time if grid_time else None})

# Explicitly record the deliberately weak initial B&B prototype on the U-shaped case.
u_shape=polygons[1]
bnb=optimize_rectangular_lattice(u_shape,2.0,2.5,max_nodes=300,
                                 seed_grid_angle_step=30,seed_phase_divisions=3)

arr_times=[x["arrangement_seconds"] for x in rows]
grid_times=[x["grid20_seconds"] for x in rows]
summary={
    "benchmark_name":"fixed_orientation_phase_arrangement_vs_20x20_uniform_phase_grid",
    "shape_count":len(polygons),"orientation_cases_per_shape":len(angles),
    "total_cases":len(rows),
    "arrangement_ge_grid_cases":sum(x["count_delta"]>=0 for x in rows),
    "arrangement_strictly_better_cases":sum(x["count_delta"]>0 for x in rows),
    "max_count_improvement":max(x["count_delta"] for x in rows),
    "median_arrangement_seconds":statistics.median(arr_times),
    "median_grid20_seconds":statistics.median(grid_times),
    "median_runtime_ratio_arrangement_over_grid20":statistics.median(arr_times)/statistics.median(grid_times),
    "bnb_exploratory_result":{k:bnb[k] for k in ["status","best_found_count","upper_bound_count","absolute_gap","processed_nodes","elapsed_seconds"]},
    "scope":"Synthetic small polygons only; fixed orientation; Shapely/GEOS numerical topology; not farm validation; not proof of novelty; not proof of a formal mathematical certificate.",
    "cases":rows,
}
out=Path(__file__).with_name("prototype_benchmark_results.json")
out.write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in summary.items() if k!="cases"},ensure_ascii=False,indent=2))
