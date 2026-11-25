"""Shapely-free reference verifier for simple polygon + rectangular-lattice plans.

This is an independent implementation candidate for PATCH-08..PATCH-10. It
supports simple, hole-free polygon rings only. It is a numerical cross-check,
not a formal exact-geometry kernel.
"""
from __future__ import annotations
import math
from collections import defaultdict

TOL = 1e-7


def _finite_pair(p):
    return (isinstance(p, (list, tuple)) and len(p) == 2 and
            all(isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(float(v)) for v in p))


def _point_segment_distance(p, a, b):
    dx, dy = b[0]-a[0], b[1]-a[1]
    den = dx*dx + dy*dy
    if den == 0:
        return math.hypot(p[0]-a[0], p[1]-a[1])
    t = max(0.0, min(1.0, ((p[0]-a[0])*dx + (p[1]-a[1])*dy)/den))
    return math.hypot(p[0]-(a[0]+t*dx), p[1]-(a[1]+t*dy))


def _ring_edges(ring):
    return list(zip(ring, ring[1:] + ring[:1]))


def _point_on_boundary(p, ring, tol=TOL):
    return any(_point_segment_distance(p, a, b) <= tol for a, b in _ring_edges(ring))


def _inside_or_boundary(p, ring):
    if _point_on_boundary(p, ring):
        return True
    x, y = p
    inside = False
    for (x1, y1), (x2, y2) in _ring_edges(ring):
        if (y1 > y) != (y2 > y):
            xin = x1 + (y-y1)*(x2-x1)/(y2-y1)
            if x < xin:
                inside = not inside
    return inside


def _boundary_distance(p, ring):
    return min(_point_segment_distance(p, a, b) for a, b in _ring_edges(ring))


def _orient(a, b, c):
    return (b[0]-a[0])*(c[1]-a[1]) - (b[1]-a[1])*(c[0]-a[0])


def _on_segment(a, b, p):
    return (min(a[0], b[0])-TOL <= p[0] <= max(a[0], b[0])+TOL and
            min(a[1], b[1])-TOL <= p[1] <= max(a[1], b[1])+TOL and
            abs(_orient(a, b, p)) <= TOL)


def _segments_intersect(a, b, c, d):
    o1, o2, o3, o4 = _orient(a,b,c), _orient(a,b,d), _orient(c,d,a), _orient(c,d,b)
    if ((o1 > TOL and o2 < -TOL) or (o1 < -TOL and o2 > TOL)) and ((o3 > TOL and o4 < -TOL) or (o3 < -TOL and o4 > TOL)):
        return True
    return ((abs(o1) <= TOL and _on_segment(a,b,c)) or
            (abs(o2) <= TOL and _on_segment(a,b,d)) or
            (abs(o3) <= TOL and _on_segment(c,d,a)) or
            (abs(o4) <= TOL and _on_segment(c,d,b)))


def _valid_ring(ring, label):
    if not isinstance(ring, list) or len(ring) < 3 or not all(_finite_pair(p) for p in ring):
        raise ValueError(f"{label}: invalid coordinate ring")
    clean = [tuple(map(float, p)) for p in ring]
    if len(clean) >= 4 and clean[0] == clean[-1]:
        clean = clean[:-1]
    if len(clean) < 3 or len(set(clean)) < 3:
        raise ValueError(f"{label}: fewer than three distinct vertices")
    if any(math.dist(clean[k], clean[(k+1)%len(clean)]) <= TOL for k in range(len(clean))):
        raise ValueError(f"{label}: zero-length edge")
    n = len(clean)
    for i in range(n):
        a, b = clean[i], clean[(i+1)%n]
        for j in range(i+1, n):
            if j == i or j == (i+1)%n or (j+1)%n == i:
                continue
            if _segments_intersect(a, b, clean[j], clean[(j+1)%n]):
                raise ValueError(f"{label}: self-intersecting polygon")
    signed = sum(clean[i][0]*clean[(i+1)%n][1] - clean[(i+1)%n][0]*clean[i][1]
                 for i in range(n))/2
    if abs(signed) <= TOL:
        raise ValueError(f"{label}: zero area")
    return clean


def verify_plan_reference(case: dict, result: dict):
    field = _valid_ring(case["field"]["vertices"], "field")
    obstacles = [_valid_ring(o["vertices"], o.get("name", "obstacle")) for o in case.get("obstacles", [])]
    settings = case.get("settings", {})
    crop = case.get("crop", {})
    setback = float(settings.get("boundary_setback_m", 0.0))
    obstacle_clearance = float(settings.get("obstacle_buffer_m", 0.0))
    row = float(crop.get("row_spacing_m", 0.75))
    along = float(crop.get("in_row_spacing_m", 0.25))
    theta_deg = float(result["search"]["rectangular_crop_row"]["best_theta_deg"])
    pa = float(result["search"]["rectangular_crop_row"]["best_phase_a_fraction"])
    pb = float(result["search"]["rectangular_crop_row"]["best_phase_b_fraction"])
    vals = (setback, obstacle_clearance, row, along, theta_deg, pa, pb)
    if not all(math.isfinite(v) for v in vals) or min(setback, obstacle_clearance) < 0 or min(row, along) <= 0:
        raise ValueError("non-finite or invalid model parameter")
    points = result.get("planting_positions")
    if not isinstance(points, list) or len(points) == 0:
        return {"verifier": "python_reference_no_shapely_v1", "implementation_independent_of_optimizer": True,
                "all_checks_passed": False, "verified_point_count": 0,
                "status": "NO_FEASIBLE_POINTS", "reason": "EMPTY_PLAN_NOT_ELIGIBLE_FOR_VERIFICATION"}

    t = math.radians(theta_deg)
    ax, ay = along*math.cos(t), along*math.sin(t)
    bx, by = -row*math.sin(t), row*math.cos(t)
    failures = {k: 0 for k in ("outside_field", "boundary_clearance", "obstacle_clearance",
                               "coordinate_reconstruction", "duplicate_lattice_indices",
                               "row_spacing", "in_row_spacing")}
    seen = set(); rows = defaultdict(list)
    min_boundary = math.inf; min_obstacle = math.inf
    for entry in points:
        x, y = float(entry["x_m"]), float(entry["y_m"])
        i, j = int(entry["lattice_i"]), int(entry["lattice_j"])
        if not math.isfinite(x) or not math.isfinite(y):
            failures["coordinate_reconstruction"] += 1
            continue
        if (i, j) in seen: failures["duplicate_lattice_indices"] += 1
        seen.add((i, j)); rows[i].append((j, x, y))
        p = (x, y)
        if not _inside_or_boundary(p, field): failures["outside_field"] += 1
        db = _boundary_distance(p, field); min_boundary = min(min_boundary, db)
        if db < setback - TOL: failures["boundary_clearance"] += 1
        for obs in obstacles:
            if _inside_or_boundary(p, obs):
                failures["obstacle_clearance"] += 1
                min_obstacle = 0.0
                break
            do = _boundary_distance(p, obs); min_obstacle = min(min_obstacle, do)
            if do < obstacle_clearance - TOL:
                failures["obstacle_clearance"] += 1
                break
        xr = (pa+j)*ax + (pb+i)*bx
        yr = (pa+j)*ay + (pb+i)*by
        if math.hypot(x-xr, y-yr) > 2e-8:
            failures["coordinate_reconstruction"] += 1
    row_keys = sorted(rows)
    for i, entries in rows.items():
        entries.sort()
        for left, right in zip(entries, entries[1:]):
            if (right[0]-left[0])*along < along-TOL:
                failures["in_row_spacing"] += 1
    for x, i in enumerate(row_keys):
        for j in row_keys[x+1:]:
            if (j-i)*row < row-TOL:
                failures["row_spacing"] += 1
    passed = all(v == 0 for v in failures.values())
    return {"verifier": "python_reference_no_shapely_v1",
            "implementation_independent_of_optimizer": True, "checks": failures,
            "all_checks_passed": passed, "verified_point_count": len(points),
            "minimum_boundary_clearance_m": min_boundary,
            "minimum_obstacle_clearance_m": None if not obstacles else min_obstacle,
            "required_boundary_setback_m": setback,
            "required_obstacle_clearance_m": obstacle_clearance,
            "status": "VERIFIED_FEASIBLE" if passed else "VERIFICATION_FAILED",
            "scope": "Independent numerical check for simple hole-free polygons; does not establish agronomic suitability or global optimality."}
