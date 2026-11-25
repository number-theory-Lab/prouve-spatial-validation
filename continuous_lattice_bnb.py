#!/usr/bin/env python3
"""PROUVE Spatial research prototype: interval branch-and-bound for a rectangular lattice.

This is an isolated research prototype, not a replacement for V0.4 and not wired
into the published app. It maximizes the number of lattice points covered by a
represented Shapely polygon over theta in [0, 180] degrees and phases in [0,1]^2.

The node upper bound counts lattice indices whose interval-enclosed swept AABB
intersects the usable polygon. This is conservative at the geometric set level
provided the interval calculations enclose the true coordinate ranges. Python's
platform libm is not a formally verified interval transcendental implementation;
therefore the result is labelled NUMERICALLY_CONSERVATIVE, not a formal proof.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import heapq
import itertools
import math
import time
from typing import Callable

import numpy as np
import shapely
from shapely.geometry import Polygon, box


class SearchInputError(ValueError):
    pass


def _down(x: float) -> float:
    return math.nextafter(float(x), -math.inf)


def _up(x: float) -> float:
    return math.nextafter(float(x), math.inf)


def _imul(a: tuple[float, float], b: tuple[float, float]) -> tuple[float, float]:
    vals = (a[0]*b[0], a[0]*b[1], a[1]*b[0], a[1]*b[1])
    return _down(min(vals)), _up(max(vals))


def _iadd(a: tuple[float, float], b: tuple[float, float]) -> tuple[float, float]:
    return _down(a[0] + b[0]), _up(a[1] + b[1])


def _isub(a: tuple[float, float], b: tuple[float, float]) -> tuple[float, float]:
    return _down(a[0] - b[1]), _up(a[1] - b[0])


def _trig_range(lo: float, hi: float, kind: str) -> tuple[float, float]:
    """Enclose sin/cos on a closed radian interval using endpoint + extrema checks."""
    if hi < lo:
        raise SearchInputError("invalid angular interval")
    if hi - lo >= 2.0 * math.pi:
        return (-1.0, 1.0)
    fn: Callable[[float], float] = math.sin if kind == "sin" else math.cos
    vals = [fn(lo), fn(hi)]
    offset = math.pi / 2 if kind == "sin" else 0.0
    k0 = math.ceil((lo - offset) / math.pi)
    k1 = math.floor((hi - offset) / math.pi)
    for k in range(k0, k1 + 1):
        vals.append(fn(offset + k * math.pi))
    # Inflate by several ulps to reduce the risk of libm endpoint rounding inward.
    mn, mx = min(vals), max(vals)
    for _ in range(8):
        mn, mx = _down(mn), _up(mx)
    return max(-1.0, mn), min(1.0, mx)


def _coord_interval(
    i: int, j: int, theta_deg: tuple[float, float],
    phase_a: tuple[float, float], phase_b: tuple[float, float],
    spacing_a: float, spacing_b: float, center: tuple[float, float],
) -> tuple[float, float, float, float]:
    """AABB enclosing one lattice site's position over a parameter box."""
    theta = (math.radians(theta_deg[0]), math.radians(theta_deg[1]))
    c = _trig_range(*theta, "cos")
    s = _trig_range(*theta, "sin")
    u = (_down((j + phase_a[0]) * spacing_a), _up((j + phase_a[1]) * spacing_a))
    v = (_down((i + phase_b[0]) * spacing_b), _up((i + phase_b[1]) * spacing_b))
    x = _iadd((center[0], center[0]), _isub(_imul(u, c), _imul(v, s)))
    y = _iadd((center[1], center[1]), _iadd(_imul(u, s), _imul(v, c)))
    return x[0], y[0], x[1], y[1]


def _candidate_index_ranges(poly, spacing_a: float, spacing_b: float):
    minx, miny, maxx, maxy = poly.bounds
    cx, cy = (minx + maxx) / 2.0, (miny + maxy) / 2.0
    radius = math.hypot((maxx-minx)/2.0, (maxy-miny)/2.0)
    # For an orthogonal rectangular basis, the absolute projection on either
    # unit basis vector is at most radius. Add two indices as a safety margin.
    ra, rb = radius / spacing_a, radius / spacing_b
    j0, j1 = math.floor(-ra - 1.0) - 2, math.ceil(ra) + 2
    i0, i1 = math.floor(-rb - 1.0) - 2, math.ceil(rb) + 2
    return (i0, i1, j0, j1), (cx, cy)


def _count_layout(poly, theta_deg: float, phase_a: float, phase_b: float,
                  spacing_a: float, spacing_b: float, center: tuple[float, float],
                  index_ranges) -> int:
    i0, i1, j0, j1 = index_ranges
    theta = math.radians(theta_deg % 180.0)
    c, s = math.cos(theta), math.sin(theta)
    is_ = np.arange(i0, i1 + 1, dtype=np.int64)
    js = np.arange(j0, j1 + 1, dtype=np.int64)
    jj, ii = np.meshgrid(js, is_)
    u = (jj.ravel().astype(float) + (phase_a % 1.0)) * spacing_a
    v = (ii.ravel().astype(float) + (phase_b % 1.0)) * spacing_b
    xs = center[0] + u*c - v*s
    ys = center[1] + u*s + v*c
    pts = shapely.points(xs, ys)
    return int(np.count_nonzero(np.asarray(shapely.covers(poly, pts), dtype=bool)))


def _node_upper_bound(poly, theta, pa, pb, spacing_a, spacing_b, center, index_ranges):
    i0, i1, j0, j1 = index_ranges
    pminx, pminy, pmaxx, pmaxy = poly.bounds
    possible = 0
    for i in range(i0, i1 + 1):
        for j in range(j0, j1 + 1):
            xmin, ymin, xmax, ymax = _coord_interval(
                i, j, theta, pa, pb, spacing_a, spacing_b, center
            )
            if xmax < pminx or xmin > pmaxx or ymax < pminy or ymin > pmaxy:
                continue
            # Intersecting the AABB is necessary (not sufficient) for the true
            # swept locus to intersect the polygon, so this count is an upper bound.
            if poly.intersects(box(xmin, ymin, xmax, ymax)):
                possible += 1
    return possible


@dataclass
class SearchResult:
    status: str
    best_found_count: int
    best_theta_deg: float
    best_phase_a: float
    best_phase_b: float
    upper_bound_count: int | None
    absolute_gap: int | None
    evaluated_layouts: int
    processed_nodes: int
    queued_nodes: int
    max_nodes: int
    elapsed_seconds: float
    scope: str
    numeric_note: str


def optimize_rectangular_lattice(
    usable: Polygon, spacing_a: float, spacing_b: float, *,
    max_nodes: int = 5000, seed_grid_angle_step: float = 15.0,
    seed_phase_divisions: int = 4,
    max_candidate_indices: int = 50000,
    time_budget_seconds: float | None = None,
) -> dict:
    """Search continuous orientation and phases with interval B&B.

    `spacing_a` is along-row spacing; `spacing_b` is between-row spacing.
    Returns best found and a conservative integer upper bound for the represented
    polygon. It never claims formal optimality unless the tree closes, and even
    then the transcendental interval implementation needs independent validation.
    """
    if usable is None or usable.is_empty or not usable.is_valid:
        raise SearchInputError("usable polygon must be non-empty and valid")
    if not (math.isfinite(spacing_a) and spacing_a > 0 and math.isfinite(spacing_b) and spacing_b > 0):
        raise SearchInputError("spacing values must be finite and positive")
    if not isinstance(max_nodes, int) or max_nodes < 1:
        raise SearchInputError("max_nodes must be a positive integer")
    if not (0 < seed_grid_angle_step <= 180) or seed_phase_divisions < 2:
        raise SearchInputError("invalid seed grid")
    if isinstance(max_candidate_indices, bool) or not isinstance(max_candidate_indices, int) or max_candidate_indices < 1:
        raise SearchInputError("max_candidate_indices must be a positive integer")
    if time_budget_seconds is not None:
        if isinstance(time_budget_seconds, bool) or not math.isfinite(float(time_budget_seconds)) or float(time_budget_seconds) <= 0:
            raise SearchInputError("time_budget_seconds must be finite and positive")
        time_budget_seconds = float(time_budget_seconds)

    t0 = time.perf_counter()
    index_ranges, center = _candidate_index_ranges(usable, spacing_a, spacing_b)
    i0, i1, j0, j1 = index_ranges
    candidate_index_count = (i1-i0+1) * (j1-j0+1)
    if candidate_index_count > max_candidate_indices:
        raise SearchInputError(
            f"orientation-independent index envelope contains {candidate_index_count} sites, "
            f"exceeding max_candidate_indices={max_candidate_indices}; use grid/adaptive fallback"
        )
    best = (-1, 0.0, 0.0, 0.0)
    evaluated = 0

    def consider(theta, pa, pb):
        nonlocal best, evaluated
        score = _count_layout(usable, theta, pa, pb, spacing_a, spacing_b, center, index_ranges)
        evaluated += 1
        candidate = (score, theta % 180.0, pa % 1.0, pb % 1.0)
        if (candidate[0], -candidate[1], -candidate[2], -candidate[3]) > (best[0], -best[1], -best[2], -best[3]):
            best = candidate

    # Deterministic incumbent seed: the current finite-grid family, with a small
    # user-selectable grid. This is a starting point, not the certificate.
    n_angles = int(math.ceil(180.0 / seed_grid_angle_step))
    phases = [k / seed_phase_divisions for k in range(seed_phase_divisions)]
    seed_budget_exhausted = False
    seed_evaluations = 0
    for k in range(n_angles):
        theta = min(k * seed_grid_angle_step, 180.0 - 1e-10)
        for pa in phases:
            for pb in phases:
                # Always produce at least one feasible incumbent; after that,
                # stop seeding once the wall-clock budget has been consumed.
                if (seed_evaluations > 0 and time_budget_seconds is not None and
                        time.perf_counter() - t0 >= time_budget_seconds):
                    seed_budget_exhausted = True
                    break
                consider(theta, pa, pb)
                seed_evaluations += 1
            if seed_budget_exhausted:
                break
        if seed_budget_exhausted:
            break
    if (time_budget_seconds is not None and time.perf_counter() - t0 >= time_budget_seconds):
        seed_budget_exhausted = True

    root = ((0.0, 180.0), (0.0, 1.0), (0.0, 1.0))
    serial = itertools.count()
    heap = []
    if not seed_budget_exhausted:
        root_ub = _node_upper_bound(usable, *root, spacing_a, spacing_b, center, index_ranges)
        heap = [(-root_ub, 0, next(serial), root)]
    processed = 0
    tree_started = not seed_budget_exhausted

    while (heap and processed < max_nodes and
           (time_budget_seconds is None or time.perf_counter() - t0 < time_budget_seconds)):
        neg_ub, depth, _, node = heapq.heappop(heap)
        ub = -neg_ub
        if ub <= best[0]:
            continue
        processed += 1
        th, aa, bb = node
        # Sample the node center and all 8 corners. Corners explicitly include
        # phase/angle boundaries; Shapely covers() accepts points on the boundary.
        tc, ac, bc = (th[0]+th[1])/2, (aa[0]+aa[1])/2, (bb[0]+bb[1])/2
        for q in [(tc,ac,bc), (th[0],aa[0],bb[0]), (th[0],aa[0],bb[1]),
                  (th[0],aa[1],bb[0]), (th[0],aa[1],bb[1]), (th[1],aa[0],bb[0]),
                  (th[1],aa[0],bb[1]), (th[1],aa[1],bb[0]), (th[1],aa[1],bb[1])]:
            consider(*q)
        if ub <= best[0]:
            continue
        widths = ((th[1]-th[0])/180.0, aa[1]-aa[0], bb[1]-bb[0])
        dim = max(range(3), key=lambda k: (widths[k], -k))
        spans = [th, aa, bb]
        lo, hi = spans[dim]
        mid = (lo + hi) / 2.0
        if mid == lo or mid == hi:
            continue
        children = []
        for left, right in ((lo, mid), (mid, hi)):
            child_spans = list(spans)
            child_spans[dim] = (left, right)
            child = tuple(child_spans)
            child_ub = _node_upper_bound(usable, *child, spacing_a, spacing_b, center, index_ranges)
            if child_ub > best[0]:
                children.append((-child_ub, depth+1, next(serial), child))
        heap.extend(children)
        if children:
            heapq.heapify(heap)

    remaining_ub = (max([best[0]] + [-item[0] for item in heap]) if tree_started else None)
    closed = tree_started and (remaining_ub is not None) and (remaining_ub <= best[0])
    timed_out = (time_budget_seconds is not None and time.perf_counter() - t0 >= time_budget_seconds)
    if closed:
        status = "CLOSED_TREE_NUMERICALLY_CONSERVATIVE"
    elif timed_out:
        status = "TIME_LIMIT_BEST_FOUND_WITH_GAP"
    else:
        status = "NODE_LIMIT_BEST_FOUND_WITH_GAP"
    result = SearchResult(
        status=status,
        best_found_count=best[0], best_theta_deg=best[1],
        best_phase_a=best[2], best_phase_b=best[3],
        upper_bound_count=remaining_ub,
        absolute_gap=(max(0, remaining_ub-best[0]) if remaining_ub is not None else None),
        evaluated_layouts=evaluated, processed_nodes=processed,
        queued_nodes=len(heap), max_nodes=max_nodes,
        elapsed_seconds=time.perf_counter()-t0,
        scope="continuous orientation and phase of a rectangular lattice over the represented usable polygon only; not arbitrary free-point placement",
        numeric_note="Candidate coordinate ranges use outward nextafter inflation and an 8-ulp trig margin; formal directed-rounding proof of libm sin/cos is not claimed. Independent high-precision interval verification is required before a formal optimum certificate.",
    )
    out = asdict(result)
    # Search phases are represented in a coordinate frame centered on the
    # polygon envelope. Convert them back to the production engine's global
    # local-XY origin before exposing them to callers.
    theta_rad = math.radians(best[1] % 180.0)
    c_best, s_best = math.cos(theta_rad), math.sin(theta_rad)
    center_phase_a = (center[0] * c_best + center[1] * s_best) / spacing_a
    center_phase_b = (-center[0] * s_best + center[1] * c_best) / spacing_b
    global_phase_a = (best[2] + center_phase_a) % 1.0
    global_phase_b = (best[3] + center_phase_b) % 1.0
    out["best_phase_a_centered"] = best[2] % 1.0
    out["best_phase_b_centered"] = best[3] % 1.0
    out["best_phase_a"] = global_phase_a
    out["best_phase_b"] = global_phase_b
    out["phase_coordinate_frame"] = "global_local_xy_origin; centered phases retained in *_centered fields"
    out["center_phase_offsets_a_b"] = [center_phase_a, center_phase_b]
    out["index_ranges_i0_i1_j0_j1"] = list(index_ranges)
    out["candidate_index_envelope_size"] = candidate_index_count
    out["max_candidate_indices"] = max_candidate_indices
    out["time_budget_seconds"] = time_budget_seconds
    out["center_xy_m"] = list(center)
    out["spacing_a_m"] = spacing_a
    out["spacing_b_m"] = spacing_b
    out["best_plan_verified"] = False
    return out
