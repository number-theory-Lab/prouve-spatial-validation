#!/usr/bin/env python3
"""PROUVÉ Spatial V0.4 — Optimization & Research Validation.

Searches discrete orientation/phase grids for rectangular, square and triangular
lattices. Results are best-found over the explicitly enumerated search grid,
not automatically a continuous/global optimum. Coordinates are local XY metres.
Requires Shapely >= 2 and NumPy.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import shapely
from shapely.geometry import Polygon
from shapely import affinity

from geometry_engine_v02 import compute_usable_area, GeometryInputError
from engine_safety import classify_optimality, conservative_integer_upper_bound
from certified_upper_bound import certified_lattice_upper_bound, CertifiedBoundError

TAU = 2.0 * math.pi


class OptimizationInputError(ValueError):
    pass


@dataclass(frozen=True)
class LatticeSpec:
    name: str
    family: str
    a_length: float
    b_length: float
    gamma_deg: float
    cell_area: float
    circumradius: float
    angle_period_deg: float
    phases_description: str


def _finite_positive(value: Any, name: str) -> float:
    if isinstance(value, bool):
        raise OptimizationInputError(f"{name} ต้องเป็นตัวเลข ไม่ใช่ boolean")
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise OptimizationInputError(f"{name} ต้องเป็นตัวเลข") from exc
    if not math.isfinite(result) or result <= 0:
        raise OptimizationInputError(f"{name} ต้องเป็นค่าบวกและมีค่าจำกัด")
    return result


def _make_specs(row_spacing: float, in_row_spacing: float) -> dict[str, LatticeSpec]:
    row_spacing = _finite_positive(row_spacing, "row_spacing")
    in_row_spacing = _finite_positive(in_row_spacing, "in_row_spacing")
    rect_area = row_spacing * in_row_spacing
    if not math.isfinite(rect_area) or rect_area <= 0:
        raise OptimizationInputError("cell area ไม่อยู่ในช่วงตัวเลขที่รองรับ")
    square_spacing = math.sqrt(rect_area)
    triangular_spacing = math.sqrt(2.0 * rect_area / math.sqrt(3.0))
    return {
        "rectangular_crop": LatticeSpec(
            "Rectangular crop-row lattice", "rectangular", in_row_spacing,
            row_spacing, 90.0, rect_area,
            0.5 * math.hypot(in_row_spacing, row_spacing), 180.0,
            "two independent fractional phases in [0,1)"
        ),
        "square_equal_density": LatticeSpec(
            "Square lattice (equal nominal area per station)", "square",
            square_spacing, square_spacing, 90.0, square_spacing ** 2,
            square_spacing / math.sqrt(2.0), 90.0,
            "two independent fractional phases in [0,1)"
        ),
        "triangular_equal_density": LatticeSpec(
            "Triangular lattice (equal nominal area per station)", "triangular",
            triangular_spacing, triangular_spacing, 60.0,
            (math.sqrt(3.0) / 2.0) * triangular_spacing ** 2,
            (math.sqrt(3.0) / 2.0) * triangular_spacing, 60.0,
            "two independent fractional phases in [0,1)"
        ),
    }


def _basis(spec: LatticeSpec, theta_deg: float) -> tuple[np.ndarray, np.ndarray]:
    if isinstance(theta_deg, bool) or not math.isfinite(float(theta_deg)):
        raise OptimizationInputError("theta_deg ต้องเป็นตัวเลขที่มีค่าจำกัด")
    t = math.radians(theta_deg)
    if spec.family in ("rectangular", "square"):
        a = np.array([spec.a_length * math.cos(t), spec.a_length * math.sin(t)])
        b = np.array([-spec.b_length * math.sin(t), spec.b_length * math.cos(t)])
    elif spec.family == "triangular":
        a = spec.a_length * np.array([math.cos(t), math.sin(t)])
        t2 = t + math.radians(60.0)
        b = spec.b_length * np.array([math.cos(t2), math.sin(t2)])
    else:
        raise OptimizationInputError(f"Unknown lattice family: {spec.family}")
    return a, b


def _project_bbox_coefficients(field_bounds: tuple[float, float, float, float],
                               a: np.ndarray, b: np.ndarray) -> tuple[float, float, float, float]:
    minx, miny, maxx, maxy = field_bounds
    corners = np.array([[minx, miny], [minx, maxy], [maxx, miny], [maxx, maxy]], dtype=float)
    matrix = np.column_stack([a, b])
    inv = np.linalg.inv(matrix)
    coeffs = corners @ inv.T
    return (float(coeffs[:, 0].min()), float(coeffs[:, 1].min()),
            float(coeffs[:, 0].max()), float(coeffs[:, 1].max()))


def _candidate_indices(bounds: tuple[float, float, float, float],
                       phase_a: float, phase_b: float) -> tuple[np.ndarray, np.ndarray]:
    amin, bmin, amax, bmax = bounds
    # Add one full index at either end to protect against round-off at envelope edges.
    j0 = math.floor(amin - phase_a) - 1
    j1 = math.ceil(amax - phase_a) + 1
    i0 = math.floor(bmin - phase_b) - 1
    i1 = math.ceil(bmax - phase_b) + 1
    if max(abs(j0), abs(j1), abs(i0), abs(i1)) > np.iinfo(np.int64).max - 2:
        raise OptimizationInputError("ขอบเขตดัชนี lattice เกินช่วง int64")
    candidate_total = (j1 - j0 + 1) * (i1 - i0 + 1)
    if candidate_total < 0 or candidate_total > 5_000_000:
        raise OptimizationInputError("จำนวน candidate points เกินขีดจำกัดความปลอดภัย 5,000,000 จุด")
    js = np.arange(j0, j1 + 1, dtype=np.int64)
    ii = np.arange(i0, i1 + 1, dtype=np.int64)
    jj_grid, ii_grid = np.meshgrid(js, ii)
    return jj_grid.ravel(), ii_grid.ravel()


def _polygon_rings_for_scanline(geom):
    if geom.is_empty:
        return
    if geom.geom_type == "Polygon":
        yield geom.exterior.coords
        for ring in geom.interiors:
            yield ring.coords
    elif hasattr(geom, "geoms"):
        for child in geom.geoms:
            yield from _polygon_rings_for_scanline(child)


def _candidate_indices_for_basis(usable, a: np.ndarray, b: np.ndarray,
                                 max_candidates: int = 5_000_000,
                                 max_scanline_spans: int = 1_000_000) -> tuple[np.ndarray, np.ndarray]:
    """Enumerate lattice index cells intersecting usable geometry in basis coordinates.

    A candidate index (j,i) can contain a feasible phase point only if the
    unit square [j,j+1] x [i,i+1] intersects the transformed usable polygon.
    A scanline boundary envelope enumerates a conservative superset without
    taking the Cartesian product of the full projected bounding box. This is
    materially better for long, narrow, rotated polygons.
    """
    if usable.is_empty:
        return np.asarray([], dtype=np.int64), np.asarray([], dtype=np.int64)
    matrix = np.column_stack([a, b])
    try:
        inv = np.linalg.inv(matrix)
    except np.linalg.LinAlgError as exc:
        raise OptimizationInputError("lattice basis ไม่สามารถกลับเมทริกซ์ได้") from exc
    lattice_geom = affinity.affine_transform(
        usable, [float(inv[0,0]), float(inv[0,1]),
                 float(inv[1,0]), float(inv[1,1]), 0.0, 0.0]
    )
    row_bounds: dict[int, list[float]] = {}
    scanline_spans = 0
    for ring in _polygon_rings_for_scanline(lattice_geom):
        coords = list(ring)
        for p0, p1 in zip(coords, coords[1:]):
            x0, y0 = float(p0[0]), float(p0[1])
            x1, y1 = float(p1[0]), float(p1[1])
            if not all(math.isfinite(v) for v in (x0, y0, x1, y1)):
                raise OptimizationInputError("transformed polygon contains non-finite coordinates")
            row0 = math.ceil(min(y0, y1) - 1.0)
            row1 = math.floor(max(y0, y1))
            if row1 < row0:
                continue
            scanline_spans += row1 - row0 + 1
            if scanline_spans > max_scanline_spans:
                raise OptimizationInputError(
                    f"จำนวน scanline spans เกินขีดจำกัด {max_scanline_spans:,}; "
                    "โปรดแบ่งปัญหา/ปรับระยะปลูก หรือใช้ adaptive strategy"
                )
            for row in range(row0, row1 + 1):
                xs: list[float] = []
                for x, y in ((x0, y0), (x1, y1)):
                    if row <= y <= row + 1:
                        xs.append(x)
                if y0 != y1:
                    for y_target in (float(row), float(row + 1)):
                        if min(y0, y1) <= y_target <= max(y0, y1):
                            t = (y_target - y0) / (y1 - y0)
                            xs.append(x0 + t * (x1 - x0))
                if xs:
                    bounds = row_bounds.get(row)
                    lo, hi = min(xs), max(xs)
                    if bounds is None:
                        row_bounds[row] = [lo, hi]
                    else:
                        bounds[0] = min(bounds[0], lo)
                        bounds[1] = max(bounds[1], hi)
    js_parts: list[np.ndarray] = []
    ii_parts: list[np.ndarray] = []
    total = 0
    int64_min, int64_max = np.iinfo(np.int64).min, np.iinfo(np.int64).max
    for row, (xmin, xmax) in sorted(row_bounds.items()):
        # One extra index at each side protects against transform round-off and
        # includes cells that touch polygon boundaries under covers semantics.
        j0 = math.floor(xmin - 1.0) - 1
        j1 = math.ceil(xmax) + 1
        if any(v < int64_min or v > int64_max for v in (row, j0, j1)):
            raise OptimizationInputError("ดัชนี lattice เกินช่วง int64; โปรดแปลงพิกัดเป็น local XY")
        n = max(0, j1 - j0 + 1)
        total += n
        if total > max_candidates:
            raise OptimizationInputError(
                f"จำนวน candidate lattice cells เกินขีดจำกัด {max_candidates:,} จุด; "
                "โปรดลดขอบเขตการค้นหา/ปรับระยะปลูก หรือใช้ adaptive strategy"
            )
        if n:
            js_parts.append(np.arange(j0, j1 + 1, dtype=np.int64))
            ii_parts.append(np.full(n, row, dtype=np.int64))
    if not js_parts:
        return np.asarray([], dtype=np.int64), np.asarray([], dtype=np.int64)
    return np.concatenate(js_parts), np.concatenate(ii_parts)


def enumerate_layout(usable, field_bounds, spec: LatticeSpec, theta_deg: float,
                     phase_a: float, phase_b: float,
                     include_points: bool = False,
                     candidate_indices: tuple[np.ndarray, np.ndarray] | None = None) -> dict[str, Any]:
    """Count lattice stations covered by usable geometry for one angle/phase."""
    a, b = _basis(spec, theta_deg)
    if candidate_indices is None:
        js, ii = _candidate_indices_for_basis(usable, a, b)
    else:
        js, ii = candidate_indices
    ca = phase_a + js.astype(float)
    cb = phase_b + ii.astype(float)
    xs = ca * a[0] + cb * b[0]
    ys = ca * a[1] + cb * b[1]
    pts = shapely.points(xs, ys)
    mask = np.asarray(shapely.covers(usable, pts), dtype=bool)
    accepted = np.flatnonzero(mask)
    result: dict[str, Any] = {
        "count": int(len(accepted)),
        "theta_deg": float(theta_deg % spec.angle_period_deg),
        "phase_a": float(phase_a % 1.0),
        "phase_b": float(phase_b % 1.0),
        "candidate_count": int(len(xs)),
        "accepted_indices": accepted,
        "accepted_x": xs[accepted],
        "accepted_y": ys[accepted],
        "accepted_j": js[accepted],
        "accepted_i": ii[accepted],
        "a": a,
        "b": b,
    }
    if not include_points:
        result.pop("accepted_indices", None)
        result.pop("accepted_x", None)
        result.pop("accepted_y", None)
        result.pop("accepted_j", None)
        result.pop("accepted_i", None)
        result.pop("a", None)
        result.pop("b", None)
    return result


def _phase_values(divisions: int) -> list[float]:
    if isinstance(divisions, bool) or not isinstance(divisions, int) or divisions < 2:
        raise OptimizationInputError("phase_divisions ต้องเป็นจำนวนเต็มตั้งแต่ 2 ขึ้นไป")
    if divisions > 200:
        raise OptimizationInputError("phase_divisions เกินขีดจำกัด 200 ใน branch รุ่นนี้")
    return [k / divisions for k in range(divisions)]


def search_lattice(usable, field_bounds, spec: LatticeSpec,
                   angle_step_deg: float = 2.0,
                   phase_divisions: int = 10,
                   refine: bool = False,
                   refine_angle_step_deg: float = 0.25,
                   refine_phase_divisions: int = 4,
                   top_k: int = 10) -> dict[str, Any]:
    """Exhaustively enumerate the requested finite angle/phase grid.

    Optional local refinement is itself fully enumerated and is included in
    the declared candidate set. It does not imply continuous optimality.
    """
    if isinstance(angle_step_deg, bool) or isinstance(refine_angle_step_deg, bool):
        raise OptimizationInputError("angle steps ต้องเป็นตัวเลข ไม่ใช่ boolean")
    try:
        angle_step_deg = float(angle_step_deg)
        refine_angle_step_deg = float(refine_angle_step_deg)
    except (TypeError, ValueError) as exc:
        raise OptimizationInputError("angle steps ต้องเป็นตัวเลข") from exc
    if not math.isfinite(angle_step_deg) or not (0 < angle_step_deg <= spec.angle_period_deg):
        raise OptimizationInputError("angle_step_deg ต้องเป็นค่าจำกัดในช่วง (0, angle_period_deg]")
    if not math.isfinite(refine_angle_step_deg) or refine_angle_step_deg <= 0:
        raise OptimizationInputError("refine_angle_step_deg ต้องเป็นค่าบวกและมีค่าจำกัด")
    if isinstance(refine_phase_divisions, bool) or not isinstance(refine_phase_divisions, int) or refine_phase_divisions < 1:
        raise OptimizationInputError("refine_phase_divisions ต้องเป็นจำนวนเต็มตั้งแต่ 1 ขึ้นไป")
    if isinstance(top_k, bool) or not isinstance(top_k, int) or top_k < 0:
        raise OptimizationInputError("top_k ต้องเป็นจำนวนเต็มตั้งแต่ 0 ขึ้นไป")
    phases = _phase_values(phase_divisions)
    angle_count = int(math.ceil(spec.angle_period_deg / angle_step_deg))
    coarse_evaluations = angle_count * phase_divisions * phase_divisions
    if coarse_evaluations > 2_000_000:
        raise OptimizationInputError("จำนวน layouts ใน coarse grid เกินขีดจำกัด 2,000,000")
    angles = [min(k * angle_step_deg, spec.angle_period_deg - 1e-10)
              for k in range(angle_count)]
    started = time.perf_counter()
    best = None
    scored: list[tuple[int, float, float, float]] = []
    evaluated = 0

    def evaluate(theta, pa, pb, candidate_indices=None):
        nonlocal best, evaluated
        item = enumerate_layout(usable, field_bounds, spec, theta, pa, pb, False, candidate_indices)
        evaluated += 1
        score = (item["count"], -theta, -pa, -pb)
        scored.append((item["count"], theta % spec.angle_period_deg, pa % 1.0, pb % 1.0))
        if best is None or score > best[0]:
            best = (score, item)

    for theta in angles:
        angle_candidates = _candidate_indices_for_basis(usable, *_basis(spec, theta))
        for pa in phases:
            for pb in phases:
                evaluate(theta, pa, pb, angle_candidates)

    coarse_best = best[1]
    refinement_evaluated = 0
    if refine:
        expected_angle_offsets = int(math.ceil((2.0 * angle_step_deg) / refine_angle_step_deg)) + 2
        expected_phase_offsets = 2 * refine_phase_divisions + 1
        if expected_angle_offsets * expected_phase_offsets * expected_phase_offsets > 2_000_000:
            raise OptimizationInputError("จำนวน layouts ใน refinement เกินขีดจำกัด 2,000,000")
        angle_offsets = np.arange(
            -angle_step_deg, angle_step_deg + refine_angle_step_deg * 0.5,
            refine_angle_step_deg
        )
        phase_delta = 1.0 / phase_divisions
        fine_step = phase_delta / refine_phase_divisions
        offsets = np.arange(-phase_delta, phase_delta + fine_step * 0.5, fine_step)
        seen = set()
        candidate_cache: dict[float, tuple[np.ndarray, np.ndarray]] = {}
        for dt in angle_offsets:
            theta = (coarse_best["theta_deg"] + dt) % spec.angle_period_deg
            cache_key = round(theta, 9)
            if cache_key not in candidate_cache:
                candidate_cache[cache_key] = _candidate_indices_for_basis(usable, *_basis(spec, theta))
            angle_candidates = candidate_cache[cache_key]
            for da in offsets:
                pa = (coarse_best["phase_a"] + da) % 1.0
                for db in offsets:
                    pb = (coarse_best["phase_b"] + db) % 1.0
                    key = (round(theta, 9), round(pa, 9), round(pb, 9))
                    if key in seen:
                        continue
                    seen.add(key)
                    evaluate(theta, pa, pb, angle_candidates)
                    refinement_evaluated += 1

    assert best is not None
    final_candidates = _candidate_indices_for_basis(usable, *_basis(spec, best[1]["theta_deg"]))
    best_layout = enumerate_layout(
        usable, field_bounds, spec, best[1]["theta_deg"],
        best[1]["phase_a"], best[1]["phase_b"], include_points=True,
        candidate_indices=final_candidates
    )
    evaluated += 1  # final point regeneration is a deterministic evaluation
    elapsed = time.perf_counter() - started
    unique_scored = sorted(set(scored), key=lambda x: (-x[0], x[1], x[2], x[3]))
    return {
        "spec": spec,
        "best": best_layout,
        "best_count": best_layout["count"],
        "best_theta_deg": best_layout["theta_deg"],
        "best_phase_a": best_layout["phase_a"],
        "best_phase_b": best_layout["phase_b"],
        "coarse_best_count": coarse_best["count"],
        "evaluated_layouts": evaluated,
        "coarse_layouts": len(angles) * phase_divisions * phase_divisions,
        "refinement_layouts": refinement_evaluated,
        "angle_step_deg": angle_step_deg,
        "phase_divisions": phase_divisions,
        "refine_enabled": refine,
        "top_results": [
            {"count": n, "theta_deg": t, "phase_a": pa, "phase_b": pb}
            for n, t, pa, pb in unique_scored[:top_k]
        ],
        "elapsed_seconds": elapsed,
    }


def _conservative_buffer_radius(distance: float, quad_segs: int) -> float:
    if distance <= 0:
        return 0.0
    return distance / math.cos(math.pi / (4.0 * quad_segs))


def lattice_upper_bound(usable, spec: LatticeSpec, quad_segs: int = 128) -> dict[str, Any]:
    """Return a rationally certified packing upper bound plus legacy estimate.

    The certificate uses the convex-hull Steiner enclosure implemented in
    certified_upper_bound.py. The old GEOS round-buffer bound is retained only
    as an explicitly non-certified comparison metric.
    """
    if isinstance(quad_segs, bool) or not isinstance(quad_segs, int) or quad_segs < 8:
        raise OptimizationInputError("quad_segs ต้องเป็นจำนวนเต็มตั้งแต่ 8 ขึ้นไป")
    try:
        certified = certified_lattice_upper_bound(usable, spec)
    except CertifiedBoundError as exc:
        raise OptimizationInputError(f"ไม่สามารถสร้าง certified upper bound ได้: {exc}") from exc

    estimate = None
    if usable.is_empty:
        estimate = {
            "expanded_area_m2": 0.0,
            "legacy_estimate_count": 0,
            "legacy_estimate_status": "EMPTY_GEOMETRY",
        }
    else:
        r = _conservative_buffer_radius(spec.circumradius, quad_segs)
        expanded = usable.buffer(r, quad_segs=quad_segs, join_style="round")
        expanded_area = float(expanded.area)
        quotient = expanded_area / spec.cell_area
        conversion = conservative_integer_upper_bound(quotient, source_bound_certified=False)
        estimate = {
            "expanded_area_m2": expanded_area,
            "legacy_quotient_estimate": quotient,
            "legacy_estimate_count": conversion["upper_bound_count"],
            "legacy_estimate_status": "ESTIMATE_ONLY_FLOATING_GEOMETRY",
            "legacy_rounding_rule": "ceil(q); no epsilon subtraction",
        }

    return {
        **certified,
        "upper_bound_count": certified["upper_bound_count"],
        "upper_bound_certified": certified["certified"],
        "upper_bound_status": certified["status"],
        "bound_method": "exact-rational convex-hull Steiner enclosure",
        "legacy_geos_estimate": estimate,
        "certificate_scope_note": (
            "Upper bound is certified for the ideal Euclidean lattice family and "
            "the represented polygon vertices. It does not certify that a numerical "
            "candidate layout is exactly feasible; a matching best-found count does "
            "not yet authorize an optimum claim."
        ),
    }


def _make_points(best: dict[str, Any], plants_per_hole: int) -> list[dict[str, Any]]:
    output = []
    order = sorted(range(best["count"]), key=lambda idx: (int(best["accepted_i"][idx]), int(best["accepted_j"][idx])))
    for n, idx in enumerate(order, start=1):
        output.append({
            "plant_id": f"V04-P{n:04d}",
            "lattice_i": int(best["accepted_i"][idx]),
            "lattice_j": int(best["accepted_j"][idx]),
            "x_m": round(float(best["accepted_x"][idx]), 9),
            "y_m": round(float(best["accepted_y"][idx]), 9),
            "plants_in_hole": plants_per_hole,
        })
    return output


def run_benchmarks(case: dict[str, Any], *, angle_step_deg: float = 2.0,
                   phase_divisions: int = 10, refine: bool = True,
                   run_comparison_lattices: bool = True) -> dict[str, Any]:
    v02 = compute_usable_area(case)
    result02 = v02["result"]
    usable = v02["geometries"]["usable"]
    # Prepare the static polygon once; vectorized covers is much faster in repeated searches.
    shapely.prepare(usable)
    field = v02["geometries"]["field"]
    crop = case.get("crop", {})
    if not isinstance(crop, dict):
        raise OptimizationInputError("crop ต้องเป็น object/dictionary")
    row_spacing = _finite_positive(crop.get("row_spacing_m", 0.75), "crop.row_spacing_m")
    in_row_spacing = _finite_positive(crop.get("in_row_spacing_m", 0.25), "crop.in_row_spacing_m")
    raw_plants_per_hole = crop.get("plants_per_hole_after_thinning", 1)
    if isinstance(raw_plants_per_hole, bool) or not isinstance(raw_plants_per_hole, int) or raw_plants_per_hole <= 0:
        raise OptimizationInputError("plants_per_hole_after_thinning ต้องเป็นจำนวนเต็มบวก")
    plants_per_hole = raw_plants_per_hole
    specs = _make_specs(row_spacing, in_row_spacing)

    # V0.3 baseline: x=0.50 + j*0.25, y=0.50 + i*0.75.
    # In the canonical rectangular basis, this corresponds to phase fractions 0 and 2/3.
    fixed_phase = enumerate_layout(
        usable, field.bounds, specs["rectangular_crop"], 0.0, 0.0,
        (0.5 % row_spacing) / row_spacing, include_points=True
    )
    fixed_points = _make_points(fixed_phase, plants_per_hole)

    area = float(usable.area)
    area_estimate = area / (row_spacing * in_row_spacing)
    rectangular_search = search_lattice(
        usable, field.bounds, specs["rectangular_crop"], angle_step_deg,
        phase_divisions, refine=refine
    )
    rectangular_bound = lattice_upper_bound(usable, specs["rectangular_crop"])
    rectangular_gap = ((rectangular_bound["upper_bound_count"] - rectangular_search["best_count"]) / rectangular_bound["upper_bound_count"]
                       if rectangular_bound["upper_bound_count"] > 0 else None)
    if rectangular_search["best_count"] > rectangular_bound["upper_bound_count"]:
        rectangular_optimality_status = "BOUND_CONFLICT"
    elif rectangular_search["best_count"] == 0:
        rectangular_optimality_status = "NO_FEASIBLE_POINTS_IN_ENUMERATED_SEARCH"
    else:
        rectangular_optimality_status = "BEST_FOUND_NOT_PROVEN_OPTIMAL"

    methods = [
        {
            "method": "Area-per-plant estimate",
            "category": "density_estimate_only",
            "count": area_estimate,
            "integer_estimate_floor": math.floor(area_estimate),
            "nominal_cell_area_m2": row_spacing * in_row_spacing,
            "agronomically_row_feasible": None,
            "note": "ค่าประมาณจากพื้นที่หารพื้นที่ต่อหลุม ไม่ใช่ชุดพิกัดที่จัดวางได้ และไม่ใช่ upper bound",
        },
        {
            "method": "V0.3 fixed rectangular grid",
            "category": "feasible_fixed_layout",
            "count": fixed_phase["count"],
            "theta_deg": 0.0,
            "phase_a_fraction": 0.0,
            "phase_b_fraction": (0.5 % row_spacing) / row_spacing,
            "agronomically_row_feasible": True,
            "note": "แนวแถวขนานแกน X และ anchor เดิม (0.50, 0.50) เมตร",
        },
        {
            "method": "Optimized rectangular crop-row lattice",
            "category": "crop_row_lattice",
            "count": rectangular_search["best_count"],
            "theta_deg": rectangular_search["best_theta_deg"],
            "phase_a_fraction": rectangular_search["best_phase_a"],
            "phase_b_fraction": rectangular_search["best_phase_b"],
            "agronomically_row_feasible": True,
            "note": "ค้นหาทิศทางและ phase ภายในชุดพารามิเตอร์ที่แจกแจงไว้; ยังไม่ใช่การจัดวางอิสระทุกรูปแบบ",
        },
    ]

    comparison_searches = {}
    if run_comparison_lattices:
        for key in ("square_equal_density", "triangular_equal_density"):
            comparison_searches[key] = search_lattice(
                usable, field.bounds, specs[key], angle_step_deg,
                phase_divisions, refine=refine
            )
            methods.append({
                "method": specs[key].name,
                "category": "geometry_only_equal_density_benchmark",
                "count": comparison_searches[key]["best_count"],
                "theta_deg": comparison_searches[key]["best_theta_deg"],
                "phase_a_fraction": comparison_searches[key]["best_phase_a"],
                "phase_b_fraction": comparison_searches[key]["best_phase_b"],
                "agronomically_row_feasible": False,
                "note": "ปรับ cell area ให้เท่ากับระยะปลูก 0.25×0.75 ม. เพื่อเทียบรูปทรง lattice; ไม่รักษาเงื่อนไขแถวข้าวโพด 0.75 ม. จึงเป็น benchmark เชิงเรขาคณิต ไม่ใช่แผนปลูกที่แนะนำ",
            })

    upper_bounds = {
        "rectangular_crop_row_lattice": rectangular_bound,
    }
    for key, search in comparison_searches.items():
        upper_bounds[key] = lattice_upper_bound(usable, specs[key])
        ub = upper_bounds[key]["upper_bound_count"]
        search["upper_bound"] = ub
        search["relative_gap"] = ((ub - search["best_count"]) / ub) if ub > 0 else None
        search["proven_optimal_over_continuous_lattice_family"] = False
        search["optimality_status_pre_verification"] = (
            "BOUND_CONFLICT" if search["best_count"] > ub else
            "NO_FEASIBLE_POINTS_IN_ENUMERATED_SEARCH" if search["best_count"] == 0 else
            "BEST_FOUND_NOT_PROVEN_OPTIMAL"
        )

    points = _make_points(rectangular_search["best"], plants_per_hole)
    output = {
        "project": "PROUVÉ Spatial",
        "version": "0.4",
        "use_case": "PS-FU01",
        "coordinate_system": "Local planar XY; metres (not geographic coordinates)",
        "input": {
            "row_spacing_m": row_spacing,
            "in_row_spacing_m": in_row_spacing,
            "plants_per_hole_after_thinning": plants_per_hole,
            "usable_area_m2": area,
            "field_area_m2": float(field.area),
            "boundary_setback_m": result02["parameters"]["boundary_setback_m"],
            "obstacle_buffer_m": result02["parameters"]["obstacle_buffer_m"],
        },
        "benchmark_methods": methods,
        "search": {
            "rectangular_crop_row": {
                "best_count": rectangular_search["best_count"],
                "best_theta_deg": rectangular_search["best_theta_deg"],
                "best_phase_a_fraction": rectangular_search["best_phase_a"],
                "best_phase_b_fraction": rectangular_search["best_phase_b"],
                "evaluated_layouts": rectangular_search["evaluated_layouts"],
                "coarse_layouts": rectangular_search["coarse_layouts"],
                "refinement_layouts": rectangular_search["refinement_layouts"],
                "angle_step_deg": angle_step_deg,
                "phase_divisions": phase_divisions,
                "upper_bound_count": rectangular_bound["upper_bound_count"],
                "upper_bound_certified": rectangular_bound["upper_bound_certified"],
                "upper_bound_status": rectangular_bound["upper_bound_status"],
                "relative_gap_to_upper_bound": rectangular_gap,
                "best_over_enumerated_search_grid_proven": True,
                "continuous_lattice_optimum_proven": False,
                "optimality_status_pre_verification": rectangular_optimality_status,
                "top_results": rectangular_search["top_results"],
                "elapsed_seconds": rectangular_search["elapsed_seconds"],
            },
            "comparison_lattices": {
                key: {
                    "best_count": srch["best_count"],
                    "best_theta_deg": srch["best_theta_deg"],
                    "best_phase_a_fraction": srch["best_phase_a"],
                    "best_phase_b_fraction": srch["best_phase_b"],
                    "evaluated_layouts": srch["evaluated_layouts"],
                    "upper_bound_count": srch["upper_bound"],
                    "relative_gap_to_upper_bound": srch["relative_gap"],
                    "best_over_enumerated_search_grid_proven": True,
                    "continuous_lattice_optimum_proven": False,
                    "optimality_status_pre_verification": srch["optimality_status_pre_verification"],
                    "elapsed_seconds": srch["elapsed_seconds"],
                } for key, srch in comparison_searches.items()
            },
        },
        "optimality_evidence": {
            "rectangular_lattice_upper_bound": rectangular_bound,
            "interpretation": "Certified packing upper bound: centered fundamental cells of accepted points tile the plane and fit within the radius-R parallel body of the convex hull of the represented usable geometry; Steiner's formula and rational outward bounds yield an integer upper bound. Applies only to the declared lattice family, not arbitrary free-point placement.",
            "relative_gap_definition": "(certified_upper_bound_count - best_found_count) / certified_upper_bound_count",
            "rectangular_relative_gap": rectangular_gap,
            "best_found_count": rectangular_search["best_count"],
            "upper_bound_count": rectangular_bound["upper_bound_count"],
            "upper_bound_certified": rectangular_bound["upper_bound_certified"],
            "upper_bound_status": rectangular_bound.get("upper_bound_status"),
            "upper_bound_method": rectangular_bound.get("bound_method"),
            "proof_scope": rectangular_bound.get("proof_scope"),
            "proof_outline": rectangular_bound.get("proof_outline"),
            "exact_area_upper_fraction": rectangular_bound.get("exact_area_upper_fraction"),
            "exact_cell_area_lower_fraction": rectangular_bound.get("exact_cell_area_lower_fraction"),
            "exact_quotient_fraction": rectangular_bound.get("exact_quotient_fraction"),
            "legacy_geos_estimate": rectangular_bound.get("legacy_geos_estimate"),
            "continuous_lattice_optimum_proven": False,
            "optimality_status_pre_verification": rectangular_optimality_status,
        },
        "verification": {
            "independent_verifier_required": True,
            "generated_points": len(points),
            "point_export": "optimized_planting_positions.csv",
            "status_before_independent_verification": "PENDING",
            "verifier_passed": False,
            "optimality_certified": False,
        },
        "limitations": [
            "Best found is exact only over the explicitly enumerated finite angle/phase search grid.",
            "Refinement searches a finite local grid around the coarse winner; it is not a continuous search proof.",
            "The geometric upper bound applies only to the specified lattice family, not arbitrary free point placements.",
            "Square and triangular grids are equal-nominal-density geometric benchmarks; they do not preserve the 0.75 m crop row-spacing rule and are not agronomic recommendations.",
            "Area-per-plant is a density estimate, not a feasible point placement or upper bound.",
            "Coordinates and PS-FU01 field are synthetic local XY test data, not a surveyed farm boundary.",
            "The model covers planting-hole centres and geometric clearances only; it does not establish crop health, yield, root competition, irrigation access, or machinery access.",
        ],
        "planting_positions": points,
    }
    return {"result": output, "v02": v02}


def export_csv(points: list[dict[str, Any]], path: Path) -> None:
    fields = ["plant_id", "lattice_i", "lattice_j", "x_m", "y_m", "plants_in_hole"]
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(points)


def export_benchmarks_csv(methods: list[dict[str, Any]], path: Path) -> None:
    fields = ["method", "category", "count", "theta_deg", "phase_a_fraction",
              "phase_b_fraction", "agronomically_row_feasible", "note"]
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in methods:
            writer.writerow({k: row.get(k) for k in fields})


def main() -> int:
    parser = argparse.ArgumentParser(description="PROUVE Spatial V0.4 optimization and research validation")
    parser.add_argument("case", nargs="?", default="PS-FU01_V03.json")
    parser.add_argument("--output", default="v04_output.json")
    parser.add_argument("--positions", default="optimized_planting_positions.csv")
    parser.add_argument("--benchmarks", default="benchmark_results.csv")
    parser.add_argument("--angle-step", type=float, default=2.0)
    parser.add_argument("--phase-divisions", type=int, default=10)
    parser.add_argument("--no-refine", action="store_true")
    parser.add_argument("--no-comparison-lattices", action="store_true")
    args = parser.parse_args()
    case = json.loads(Path(args.case).read_text(encoding="utf-8"))
    computed = run_benchmarks(case, angle_step_deg=args.angle_step,
                              phase_divisions=args.phase_divisions,
                              refine=not args.no_refine,
                              run_comparison_lattices=not args.no_comparison_lattices)
    result = computed["result"]
    Path(args.output).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    export_csv(result["planting_positions"], Path(args.positions))
    export_benchmarks_csv(result["benchmark_methods"], Path(args.benchmarks))
    print(json.dumps({
        "methods": [{"method": m["method"], "count": m["count"]} for m in result["benchmark_methods"]],
        "rectangular_search": result["search"]["rectangular_crop_row"],
        "optimality_evidence": result["optimality_evidence"],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
