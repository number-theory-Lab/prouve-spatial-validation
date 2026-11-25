#!/usr/bin/env python3
"""Budget-aware solver selector for PROUVE Spatial Engine Branch V0.3.

The solver always establishes a deterministic finite-grid incumbent. It may
then try fixed-angle phase arrangement and continuous rectangular-lattice BnB
when geometry complexity and remaining compute budget permit. All research
candidates are re-evaluated through the production lattice enumerator. The
final finite point set is passed to the exact-rational feasibility checker.
Neither BnB nor arrangement is allowed to assert global optimality here.
"""
from __future__ import annotations

from dataclasses import asdict
import math
import time
from numbers import Integral
from typing import Any

import shapely
from shapely.geometry import mapping

from optimization_engine_v04 import (
    _make_specs, enumerate_layout, _make_points, LatticeSpec,
)
from formal_feasibility_certificate import verify_case_points, verify_candidate_set
from lattice_relation_certificate import build_rational_lattice_plan, verify_rational_lattice_relation
from certified_upper_bound_v03 import certified_lattice_upper_bound, CertifiedBoundError
from prototype.continuous_lattice_bnb import optimize_rectangular_lattice, SearchInputError
from prototype.exact_phase_arrangement import optimize_phase_fixed_orientation, PhaseArrangementError


class AdaptiveSolverError(ValueError):
    pass


def _geom_complexity(usable, obstacle_count: int, spacing_a: float, spacing_b: float) -> dict:
    def count_poly(g):
        if g.is_empty:
            return 0, 0, 0
        if g.geom_type == "Polygon":
            return 1, 1, len(g.exterior.coords) - 1 + sum(len(r.coords) - 1 for r in g.interiors)
        if hasattr(g, "geoms"):
            ps = hs = es = 0
            for child in g.geoms:
                a, b, c = count_poly(child)
                ps += a; hs += b; es += c
            return ps, hs, es
        return 0, 0, 0
    components, polygon_count, edge_count = count_poly(usable)
    holes = max(0, polygon_count - components)  # replaced below for accurate count
    if usable.geom_type == "Polygon":
        holes = len(usable.interiors)
    elif usable.geom_type == "MultiPolygon":
        holes = sum(len(p.interiors) for p in usable.geoms)
    minx, miny, maxx, maxy = usable.bounds if not usable.is_empty else (0,0,0,0)
    bbox_area = max(0.0, (maxx-minx)*(maxy-miny))
    occupancy = (float(usable.area)/bbox_area) if bbox_area > 0 else 0.0
    est_sites = int(math.ceil(bbox_area / (spacing_a * spacing_b))) if bbox_area > 0 else 0
    return {
        "component_count": components,
        "hole_count": holes,
        "boundary_edge_count": edge_count,
        "obstacle_count": obstacle_count,
        "bbox_area_m2": bbox_area,
        "usable_area_m2": float(usable.area),
        "bbox_occupancy_ratio": occupancy,
        "estimated_bbox_lattice_sites": est_sites,
        "aspect_ratio": (max(maxx-minx, maxy-miny) / max(1e-15, min(maxx-minx, maxy-miny))) if bbox_area > 0 else None,
    }


def _grid_search(usable, field_bounds, spec: LatticeSpec, *, max_evaluations: int, phase_divisions_cap: int,
                 time_budget_seconds: float | None) -> dict:
    if max_evaluations < 4:
        raise AdaptiveSolverError("max_evaluations must be at least 4")
    d = max(2, min(int(phase_divisions_cap), int(math.sqrt(max_evaluations / 4))))
    max_angles = max(1, max_evaluations // (d*d))
    angle_count = min(max_angles, int(math.ceil(spec.angle_period_deg / 1.0)))
    angle_step = spec.angle_period_deg / angle_count
    phases = [k / d for k in range(d)]
    started = time.perf_counter()
    best = None
    scored = []
    evaluated = 0
    time_exhausted = False
    for k in range(angle_count):
        theta = k * angle_step
        for pa in phases:
            for pb in phases:
                if time_budget_seconds is not None and evaluated > 0 and time.perf_counter() - started >= time_budget_seconds:
                    time_exhausted = True
                    break
                item = enumerate_layout(usable, field_bounds, spec, theta, pa, pb, False)
                evaluated += 1
                score = (item["count"], -theta, -pa, -pb)
                scored.append((item["count"], theta, pa, pb))
                if best is None or score > best[0]:
                    best = (score, item)
            if time_exhausted:
                break
        if time_exhausted:
            break
    if best is None:
        raise AdaptiveSolverError("grid search produced no incumbent")
    best_detail = enumerate_layout(usable, field_bounds, spec, best[1]["theta_deg"],
                                   best[1]["phase_a"], best[1]["phase_b"], include_points=True)
    unique = sorted(set(scored), key=lambda x: (-x[0], x[1], x[2], x[3]))
    return {
        "status": "GRID_TIME_LIMIT_BEST_FOUND" if time_exhausted else "GRID_COMPLETE_FINITE_SEARCH",
        "best": best_detail,
        "best_count": best_detail["count"],
        "best_theta_deg": best_detail["theta_deg"],
        "best_phase_a": best_detail["phase_a"],
        "best_phase_b": best_detail["phase_b"],
        "evaluated_layouts": evaluated,
        "declared_grid_layouts": angle_count * d * d,
        "angle_step_deg": angle_step,
        "phase_divisions": d,
        "elapsed_seconds": time.perf_counter() - started,
        "top_results": [{"count": n, "theta_deg": t, "phase_a": pa, "phase_b": pb} for n,t,pa,pb in unique[:10]],
    }


def run_adaptive_solver(
    case: dict[str, Any], usable, field_bounds, *,
    max_wall_time_seconds: float = 8.0,
    max_grid_evaluations: int = 512,
    phase_divisions_cap: int = 8,
    allow_phase_arrangement: bool = True,
    allow_orientation_bnb: bool = True,
    arrangement_max_edges: int = 120,
    arrangement_max_sites: int = 50000,
    arrangement_max_fragments: int = 1200,
    bnb_max_edges: int = 100,
    bnb_max_sites: int = 20000,
    bnb_max_nodes: int = 100,
    min_remaining_for_research_seconds: float = 0.4,
    boundary_uncertainty_m: Any = 0,
    obstacle_uncertainty_m: Any = 0,
) -> dict:
    """Choose methods adaptively and return a proof-aware finite plan + certificate."""
    if not math.isfinite(float(max_wall_time_seconds)) or max_wall_time_seconds <= 0:
        raise AdaptiveSolverError("max_wall_time_seconds must be finite and positive")
    started = time.perf_counter()
    crop = case.get("crop", {})
    raw_row_spacing = crop.get("row_spacing_m", 0)
    raw_in_row_spacing = crop.get("in_row_spacing_m", 0)
    raw_plants_per_hole = crop.get("plants_per_hole_after_thinning", 1)
    if isinstance(raw_row_spacing, bool) or isinstance(raw_in_row_spacing, bool):
        raise AdaptiveSolverError("crop spacing must be numeric metres, not boolean")
    try:
        row_spacing = float(raw_row_spacing)
        in_row_spacing = float(raw_in_row_spacing)
    except (TypeError, ValueError) as exc:
        raise AdaptiveSolverError("crop spacing must be finite numeric metres") from exc
    if not math.isfinite(row_spacing) or not math.isfinite(in_row_spacing) or row_spacing <= 0 or in_row_spacing <= 0:
        raise AdaptiveSolverError("crop spacing must be finite and positive")
    if isinstance(raw_plants_per_hole, bool) or not isinstance(raw_plants_per_hole, Integral) or raw_plants_per_hole <= 0:
        raise AdaptiveSolverError("plants_per_hole_after_thinning must be a positive integer")
    plants_per_hole = int(raw_plants_per_hole)
    specs = _make_specs(row_spacing, in_row_spacing)
    spec = specs["rectangular_crop"]
    obstacle_count = len(case.get("obstacles", []))
    complexity = _geom_complexity(usable, obstacle_count, spec.a_length, spec.b_length)
    attempts = []

    grid_budget_time = max(0.2, min(2.0, max_wall_time_seconds * 0.35))
    grid = _grid_search(usable, field_bounds, spec, max_evaluations=max_grid_evaluations,
                        phase_divisions_cap=phase_divisions_cap, time_budget_seconds=grid_budget_time)
    incumbent = grid["best"]
    selected_method = "GRID"
    attempts.append({"method":"GRID", "status":grid["status"], "best_count":grid["best_count"],
                     "evaluated_layouts":grid["evaluated_layouts"], "elapsed_seconds":grid["elapsed_seconds"]})

    def remaining():
        return max(0.0, max_wall_time_seconds - (time.perf_counter() - started))

    # Fixed-angle phase arrangement can refine the grid's winning orientation.
    if (allow_phase_arrangement and complexity["boundary_edge_count"] <= arrangement_max_edges and
            complexity["estimated_bbox_lattice_sites"] <= arrangement_max_sites and
            not usable.is_empty and remaining() > min_remaining_for_research_seconds):
        budget = min(2.0, max(0.15, remaining() * 0.45))
        try:
            arr = optimize_phase_fixed_orientation(
                usable, spec.a_length, spec.b_length, grid["best_theta_deg"],
                max_boundary_fragments=arrangement_max_fragments,
                max_lattice_index_sites=arrangement_max_sites,
                time_budget_seconds=budget,
            )
            theta = math.radians(grid["best_theta_deg"] % spec.angle_period_deg)
            usable_bounds = usable.bounds
            cx = (usable_bounds[0] + usable_bounds[2]) / 2.0
            cy = (usable_bounds[1] + usable_bounds[3]) / 2.0
            pa_global = (arr["best_phase_a"] + (cx*math.cos(theta) + cy*math.sin(theta))/spec.a_length) % 1.0
            pb_global = (arr["best_phase_b"] + (-cx*math.sin(theta) + cy*math.cos(theta))/spec.b_length) % 1.0
            check = enumerate_layout(usable, field_bounds, spec, grid["best_theta_deg"], pa_global, pb_global, True)
            match = check["count"] == arr["max_count"]
            attempts.append({"method":"PHASE_ARRANGEMENT", "status":"RECONCILED" if match else "HOLD_COUNT_MISMATCH",
                             "reported_count":arr["max_count"], "recomputed_count":check["count"],
                             "tested_phase_points":arr["tested_phase_points"], "boundary_fragments":arr["phase_pieces"],
                             "elapsed_seconds":arr["elapsed_seconds"], "numeric_topology_verified":False})
            if match and check["count"] > incumbent["count"]:
                incumbent = check
                selected_method = "PHASE_ARRANGEMENT_FIXED_ORIENTATION"
        except (PhaseArrangementError, Exception) as exc:
            attempts.append({"method":"PHASE_ARRANGEMENT", "status":"SKIPPED_OR_FALLBACK", "reason":f"{type(exc).__name__}: {exc}"})
    else:
        attempts.append({"method":"PHASE_ARRANGEMENT", "status":"SKIPPED_COMPLEXITY_OR_BUDGET"})

    # Continuous orientation/phase BnB is experimental and only attempted for
    # modest geometry, modest index envelopes, and a meaningful remaining budget.
    if (allow_orientation_bnb and complexity["boundary_edge_count"] <= bnb_max_edges and
            complexity["estimated_bbox_lattice_sites"] <= bnb_max_sites and
            not usable.is_empty and remaining() > min_remaining_for_research_seconds):
        budget = min(2.0, max(0.15, remaining() * 0.45))
        try:
            bnb = optimize_rectangular_lattice(
                usable, spec.a_length, spec.b_length,
                max_nodes=bnb_max_nodes, seed_grid_angle_step=max(5.0, grid["angle_step_deg"]),
                seed_phase_divisions=max(2, min(4, grid["phase_divisions"])),
                max_candidate_indices=bnb_max_sites, time_budget_seconds=budget,
            )
            check = enumerate_layout(usable, field_bounds, spec, bnb["best_theta_deg"],
                                     bnb["best_phase_a"], bnb["best_phase_b"], True)
            match = check["count"] == bnb["best_found_count"]
            attempts.append({"method":"ORIENTATION_PHASE_BNB", "status":"RECONCILED" if match else "HOLD_COUNT_MISMATCH",
                             "reported_count":bnb["best_found_count"], "recomputed_count":check["count"],
                             "processed_nodes":bnb["processed_nodes"], "evaluated_layouts":bnb["evaluated_layouts"],
                             "upper_bound_count_numerical_only":bnb["upper_bound_count"],
                             "elapsed_seconds":bnb["elapsed_seconds"], "optimality_proven":False})
            if match and check["count"] > incumbent["count"]:
                incumbent = check
                selected_method = "ORIENTATION_PHASE_BNB"
        except (SearchInputError, Exception) as exc:
            attempts.append({"method":"ORIENTATION_PHASE_BNB", "status":"SKIPPED_OR_FALLBACK", "reason":f"{type(exc).__name__}: {exc}"})
    else:
        attempts.append({"method":"ORIENTATION_PHASE_BNB", "status":"SKIPPED_COMPLEXITY_OR_BUDGET"})

    search_elapsed = time.perf_counter() - started

    # A zero-count incumbent is not an actionable planting plan and must not be
    # passed into the non-empty lattice/certificate builders. Return a safe HOLD
    # record instead of crashing or treating an empty set as a feasible solution.
    if int(incumbent.get("count", 0)) <= 0:
        source_cert = verify_case_points(case, [])
        if usable.is_empty:
            usable_cert = {"status":"HOLD_EMPTY_USABLE_GEOMETRY", "certified":False, "point_count":0}
            no_candidate_reason = "USABLE_GEOMETRY_EMPTY"
        else:
            usable_cert = verify_candidate_set(mapping(usable), [], [], allow_empty_candidates=False)
            no_candidate_reason = "SEARCH_DID_NOT_FIND_A_FEASIBLE_SITE"
        try:
            upper_bound = certified_lattice_upper_bound(usable, spec)
        except (CertifiedBoundError, Exception) as exc:
            upper_bound = {"status":"BOUND_UNAVAILABLE", "certified":False,
                           "reason":f"{type(exc).__name__}: {exc}"}
        hold_status = "HOLD_NO_FEASIBLE_CANDIDATE_FOUND"
        elapsed = time.perf_counter() - started
        return {
            "schema":"prouve-adaptive-solver-result-v0.2",
            "status":hold_status,
            "no_candidate_reason":no_candidate_reason,
            "selected_method":selected_method,
            "best_found_count":0,
            "best_theta_deg":float(incumbent.get("theta_deg", grid["best_theta_deg"])),
            "best_phase_a":float(incumbent.get("phase_a", grid["best_phase_a"])),
            "best_phase_b":float(incumbent.get("phase_b", grid["best_phase_b"])),
            "evaluated_grid_layouts":int(grid["evaluated_layouts"]),
            "solver_elapsed_seconds":float(elapsed),
            "grid":{k:v for k,v in grid.items() if k != "best"},
            "method_attempts":attempts,
            "complexity":complexity,
            "compute_budget":{"max_wall_time_seconds":max_wall_time_seconds,
                               "search_elapsed_seconds":search_elapsed,
                               "total_elapsed_seconds":elapsed,
                               "time_budget_scope":"Grid/Arrangement/BnB search stages; feasibility and bound certificates run to completion",
                               "max_grid_evaluations":max_grid_evaluations,
                               "bnb_max_nodes":bnb_max_nodes,
                               "arrangement_max_fragments":arrangement_max_fragments},
            "planting_positions":[],
            "rational_lattice_certificate":None,
            "lattice_relation_verification":{"status":"HOLD_EMPTY_CANDIDATE_SET", "certified":False, "point_count":0},
            "source_constraint_feasibility_certificate":source_cert,
            "represented_usable_geometry_feasibility_certificate":usable_cert,
            "certified_upper_bound":upper_bound,
            "optimality":{"proven":False, "status":"NOT_COMPUTED_NO_FEASIBLE_INCUMBENT",
                           "upper_bound_count":upper_bound.get("upper_bound_count"),
                           "relative_gap_to_certified_upper_bound":None,
                           "scope":"No non-empty candidate plan was found; no lower-bound or optimality claim is made.",
                           "not_scope":"An empty point set is not a usable planting recommendation."},
            "field_deployment_authorized":False,
            "notices":[
                "No non-empty feasible candidate set was found by this run; an empty plan is not certified as a planting solution.",
                "If the represented usable geometry is empty, the geometric preprocessing stage leaves no area for planting.",
                "If the represented usable geometry is non-empty, this result only says the configured search did not find a point; it does not prove that no lattice placement exists.",
                "Field deployment remains unauthorized pending survey/CRS/uncertainty QA and agronomist approval."
            ]
        }

    # Convert the floating search result into a mathematically exact rational
    # orthogonal lattice close to the selected angle. All accepted indices are
    # reconstructed from one exact basis/phase tuple before certification.
    points, lattice_certificate = build_rational_lattice_plan(
        incumbent, spec.a_length, spec.b_length, incumbent["theta_deg"], plants_per_hole
    )
    lattice_relation = verify_rational_lattice_relation(points, lattice_certificate)
    case_for_cert = dict(case)
    settings = dict(case_for_cert.get("settings", {}))
    settings["boundary_setback_m"] = settings.get("boundary_setback_m", 0)
    settings["obstacle_buffer_m"] = settings.get("obstacle_buffer_m", 0)
    case_for_cert["settings"] = settings
    case_for_cert["verification_uncertainty"] = {"boundary_m":boundary_uncertainty_m, "obstacle_m":obstacle_uncertainty_m}
    # Minimum pairwise spacing is proven by the exact orthogonal lattice
    # relation (unique integer index pairs + exact basis lengths), avoiding a
    # redundant O(n^2) pairwise distance loop for large generated plans.
    source_cert = verify_case_points(case_for_cert, points)
    usable_cert = verify_candidate_set(
        mapping(usable), [], points,
        allow_empty_candidates=False,
    ) if not usable.is_empty else {"status":"HOLD_EMPTY_USABLE_GEOMETRY", "certified":False}
    try:
        upper_bound = certified_lattice_upper_bound(usable, spec)
        upper_bound_status = upper_bound.get("status")
        upper_bound_certified = upper_bound.get("certified") is True
    except (CertifiedBoundError, Exception) as exc:
        upper_bound = {"status":"BOUND_UNAVAILABLE", "certified":False, "reason":f"{type(exc).__name__}: {exc}"}
        upper_bound_status = "BOUND_UNAVAILABLE"
        upper_bound_certified = False
    feasibility_pass = (
        lattice_relation.get("certified") is True and
        source_cert.get("status") == "CERTIFIED_FEASIBLE" and
        usable_cert.get("status") == "CERTIFIED_FEASIBLE"
    )
    ub_count = upper_bound.get("upper_bound_count") if upper_bound_certified else None
    relative_gap = (max(0, int(ub_count)-len(points))/int(ub_count)) if ub_count else None
    if not feasibility_pass:
        result_status = "HOLD_FORMAL_FEASIBILITY_CERTIFICATE_FAILED"
        optimality_proven = False
    elif ub_count is not None and int(ub_count) < len(points):
        result_status = "HOLD_CERTIFIED_UPPER_BOUND_CONFLICT"
        optimality_proven = False
    elif ub_count is not None and int(ub_count) == len(points):
        result_status = "OPTIMAL_WITHIN_DECLARED_RECTANGULAR_LATTICE_FAMILY_FOR_REPRESENTED_USABLE_GEOMETRY"
        optimality_proven = True
    else:
        result_status = "FEASIBLE_CERTIFIED_BEST_FOUND_NOT_PROVEN_OPTIMAL"
        optimality_proven = False
    elapsed = time.perf_counter() - started
    return {
        "schema": "prouve-adaptive-solver-result-v0.1",
        "status": result_status,
        "selected_method": selected_method,
        "best_found_count": int(incumbent["count"]),
        "best_theta_deg": float(incumbent["theta_deg"]),
        "best_phase_a": float(incumbent["phase_a"]),
        "best_phase_b": float(incumbent["phase_b"]),
        "evaluated_grid_layouts": int(grid["evaluated_layouts"]),
        "solver_elapsed_seconds": float(elapsed),
        "grid": {k:v for k,v in grid.items() if k != "best"},
        "method_attempts": attempts,
        "complexity": complexity,
        "compute_budget": {"max_wall_time_seconds":max_wall_time_seconds,
                           "search_elapsed_seconds":search_elapsed,
                           "total_elapsed_seconds":elapsed,
                           "time_budget_scope":"Grid/Arrangement/BnB search stages; exact feasibility and bound certificates run to completion and may extend total runtime",
                           "max_grid_evaluations":max_grid_evaluations,
                           "bnb_max_nodes":bnb_max_nodes,
                           "arrangement_max_fragments":arrangement_max_fragments},
        "planting_positions": points,
        "rational_lattice_certificate": lattice_certificate,
        "lattice_relation_verification": lattice_relation,
        "source_constraint_feasibility_certificate": source_cert,
        "represented_usable_geometry_feasibility_certificate": usable_cert,
        "certified_upper_bound": upper_bound,
        "optimality": {"proven":optimality_proven,
                       "status":result_status,
                       "upper_bound_count":ub_count,
                       "relative_gap_to_certified_upper_bound":relative_gap,
                       "scope":"all translations and orientations of the declared rectangular lattice family within the decimalized represented usable polygon; conditional on a passing exact-rational lattice relation and usable-geometry feasibility certificate",
                       "not_scope":"unrestricted free-point packing; unrepresented physical geometry; uncertain survey truth; other crop spacing profiles"},
        "field_deployment_authorized":False,
        "notices":[
            "The rational lattice relation, source-constraint feasibility, and represented-usable-geometry feasibility are separate certificates.",
            "An optimality conclusion is issued only when the exact-rational feasible lattice lower bound matches the certified upper bound for the same declared rectangular lattice family and represented usable geometry.",
            "Survey/CRS provenance, uncertainty adequacy, agronomic approval, and field validation are separate gates; deployment remains unauthorized."
        ]
    }
