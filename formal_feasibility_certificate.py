#!/usr/bin/env python3
"""Exact-rational feasibility checker for PROUVE Spatial candidates.

The checker certifies candidate-point feasibility relative to canonical decimal
input coordinates and clearances. It supports GeoJSON Polygon and MultiPolygon
with holes. It does NOT certify that a candidate set is optimal, nor does it
validate CRS provenance or the survey accuracy of the source geometry.

Geometry predicates and point-to-segment squared distances use fractions.Fraction;
no floating-point epsilon is used in topological or clearance decisions.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from fractions import Fraction
import hashlib
import json
import math
from typing import Any, Iterable


class CertificateInputError(ValueError):
    """Input geometry or candidate data cannot be certified."""


def _q(value: Any, label: str) -> Fraction:
    if isinstance(value, bool) or value is None:
        raise CertificateInputError(f"{label}: boolean/null is not a coordinate or metric")
    try:
        if isinstance(value, Fraction):
            out = value
        elif isinstance(value, int):
            out = Fraction(value, 1)
        elif isinstance(value, float):
            if not math.isfinite(value):
                raise CertificateInputError(f"{label}: NaN/Infinity is not allowed")
            # Canonical decimal interpretation; this is the shortest round-trip
            # decimal text for floats produced by Python/JSON serialization.
            out = Fraction(str(value))
        elif isinstance(value, str):
            out = Fraction(value.strip())
        else:
            raise CertificateInputError(f"{label}: unsupported numeric type {type(value).__name__}")
    except (ValueError, ZeroDivisionError) as exc:
        raise CertificateInputError(f"{label}: invalid rational/decimal value") from exc
    return out


def _pair(raw: Any, label: str) -> tuple[Fraction, Fraction]:
    if not isinstance(raw, (list, tuple)) or len(raw) != 2:
        raise CertificateInputError(f"{label}: coordinate must contain exactly [x,y]; 3-D and extra dimensions are unsupported")
    return _q(raw[0], f"{label}.x"), _q(raw[1], f"{label}.y")


def _cross(a, b, c) -> Fraction:
    return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])


def _on_segment(p, a, b) -> bool:
    return (_cross(a, b, p) == 0 and
            min(a[0], b[0]) <= p[0] <= max(a[0], b[0]) and
            min(a[1], b[1]) <= p[1] <= max(a[1], b[1]))


def _segments_intersect(a, b, c, d) -> bool:
    o1, o2, o3, o4 = _cross(a, b, c), _cross(a, b, d), _cross(c, d, a), _cross(c, d, b)
    if ((o1 > 0 and o2 < 0) or (o1 < 0 and o2 > 0)) and ((o3 > 0 and o4 < 0) or (o3 < 0 and o4 > 0)):
        return True
    return ((o1 == 0 and _on_segment(c, a, b)) or
            (o2 == 0 and _on_segment(d, a, b)) or
            (o3 == 0 and _on_segment(a, c, d)) or
            (o4 == 0 and _on_segment(b, c, d)))


def _ring_edges(ring):
    return list(zip(ring, ring[1:]))


def _validate_simple_ring(raw_ring: Any, label: str) -> tuple[tuple[Fraction, Fraction], ...]:
    if not isinstance(raw_ring, (list, tuple)) or len(raw_ring) < 4:
        raise CertificateInputError(f"{label}: closed linear ring needs at least 4 coordinate entries")
    pts = [_pair(p, f"{label}[{i}]") for i, p in enumerate(raw_ring)]
    if pts[0] != pts[-1]:
        raise CertificateInputError(f"{label}: ring must be explicitly closed (first point = last point)")
    vertices = pts[:-1]
    if len(set(vertices)) < 3:
        raise CertificateInputError(f"{label}: ring needs at least 3 distinct vertices")
    n = len(vertices)
    for i in range(n):
        if vertices[i] == vertices[(i + 1) % n]:
            raise CertificateInputError(f"{label}: consecutive duplicate vertices are not allowed")
    edges = [(vertices[i], vertices[(i + 1) % n]) for i in range(n)]
    for i in range(n):
        a, b = edges[i]
        for j in range(i + 1, n):
            c, d = edges[j]
            adjacent = (j == i + 1) or (i == 0 and j == n - 1)
            if not _segments_intersect(a, b, c, d):
                continue
            if not adjacent:
                raise CertificateInputError(f"{label}: self-intersecting or self-touching ring")
            # Adjacent edges share one endpoint by construction. Collinear
            # backtracking causes overlap beyond that endpoint and is rejected.
            shared = b if j == i + 1 else a
            other1 = a if j == i + 1 else b
            other2 = d if j == i + 1 else c
            if _cross(shared, other1, other2) == 0:
                v1 = (other1[0] - shared[0], other1[1] - shared[1])
                v2 = (other2[0] - shared[0], other2[1] - shared[1])
                if v1[0] * v2[0] + v1[1] * v2[1] > 0:
                    raise CertificateInputError(f"{label}: adjacent edges overlap by backtracking")
    twice_area = sum(vertices[i][0] * vertices[(i + 1) % n][1] -
                     vertices[(i + 1) % n][0] * vertices[i][1] for i in range(n))
    if twice_area == 0:
        raise CertificateInputError(f"{label}: zero-area ring")
    return tuple(pts)


def _point_ring_relation(p, ring) -> int:
    """Return 1 inside, 0 boundary, -1 outside using exact rational arithmetic."""
    inside = False
    for a, b in _ring_edges(ring):
        if _on_segment(p, a, b):
            return 0
        if (a[1] > p[1]) != (b[1] > p[1]):
            # Exact x coordinate of intersection with the horizontal ray.
            x_hit = a[0] + (p[1] - a[1]) * (b[0] - a[0]) / (b[1] - a[1])
            if x_hit > p[0]:
                inside = not inside
    return 1 if inside else -1


def _rings_touch_or_cross(r1, r2) -> bool:
    for a, b in _ring_edges(r1):
        for c, d in _ring_edges(r2):
            if _segments_intersect(a, b, c, d):
                return True
    return False


def _parse_polygon_coordinates(coords: Any, label: str):
    if not isinstance(coords, (list, tuple)) or not coords:
        raise CertificateInputError(f"{label}: Polygon coordinates must contain an exterior ring")
    shell = _validate_simple_ring(coords[0], f"{label}.exterior")
    holes = [_validate_simple_ring(r, f"{label}.hole[{i}]") for i, r in enumerate(coords[1:])]
    for i, hole in enumerate(holes):
        if _rings_touch_or_cross(shell, hole):
            raise CertificateInputError(f"{label}: hole {i} touches or crosses exterior ring")
        if _point_ring_relation(hole[0], shell) != 1:
            raise CertificateInputError(f"{label}: hole {i} is not strictly inside exterior ring")
        for j, other in enumerate(holes[:i]):
            if _rings_touch_or_cross(hole, other):
                raise CertificateInputError(f"{label}: holes {j} and {i} touch or cross")
            if _point_ring_relation(hole[0], other) == 1 or _point_ring_relation(other[0], hole) == 1:
                raise CertificateInputError(f"{label}: nested/overlapping holes are not supported")
    return (shell, *holes)


def _parse_geometry(raw: Any, label: str):
    if not isinstance(raw, dict):
        raise CertificateInputError(f"{label}: GeoJSON geometry object required")
    gtype = raw.get("type")
    coords = raw.get("coordinates")
    if gtype == "Polygon":
        return {"type": "Polygon", "polygons": [_parse_polygon_coordinates(coords, label)]}
    if gtype == "MultiPolygon":
        if not isinstance(coords, (list, tuple)) or not coords:
            raise CertificateInputError(f"{label}: MultiPolygon must contain at least one polygon")
        polygons = [_parse_polygon_coordinates(poly, f"{label}.polygon[{i}]") for i, poly in enumerate(coords)]
        # This certificate intentionally accepts strictly disjoint component
        # interiors and boundaries. Touching MultiPolygon components are held
        # rather than interpreted ambiguously.
        for i in range(len(polygons)):
            for j in range(i + 1, len(polygons)):
                pi, pj = polygons[i], polygons[j]
                if any(_rings_touch_or_cross(ri, rj) for ri in pi for rj in pj):
                    raise CertificateInputError("MultiPolygon components touching/crossing are outside supported topology")
                if _point_ring_relation(pi[0][0], pj[0]) == 1 or _point_ring_relation(pj[0][0], pi[0]) == 1:
                    raise CertificateInputError("MultiPolygon component interiors overlap")
        return {"type": "MultiPolygon", "polygons": polygons}
    raise CertificateInputError(f"{label}: only GeoJSON Polygon and MultiPolygon are supported")


def _polygon_relation(p, rings) -> int:
    shell_rel = _point_ring_relation(p, rings[0])
    if shell_rel <= 0:
        return shell_rel
    for hole in rings[1:]:
        rel = _point_ring_relation(p, hole)
        if rel == 0:
            return 0
        if rel == 1:
            return -1
    return 1


def _geometry_relation(p, geom) -> int:
    saw_boundary = False
    for polygon in geom["polygons"]:
        rel = _polygon_relation(p, polygon)
        if rel == 1:
            return 1
        if rel == 0:
            saw_boundary = True
    return 0 if saw_boundary else -1


def _point_segment_distance_sq(p, a, b) -> Fraction:
    dx, dy = b[0] - a[0], b[1] - a[1]
    wx, wy = p[0] - a[0], p[1] - a[1]
    length_sq = dx * dx + dy * dy
    if length_sq == 0:
        raise CertificateInputError("zero-length segment encountered")
    dot = wx * dx + wy * dy
    if dot <= 0:
        return wx * wx + wy * wy
    if dot >= length_sq:
        vx, vy = p[0] - b[0], p[1] - b[1]
        return vx * vx + vy * vy
    cross = dx * wy - dy * wx
    return cross * cross / length_sq


def _minimum_boundary_distance_sq(p, geom) -> Fraction:
    best: Fraction | None = None
    for polygon in geom["polygons"]:
        for ring in polygon:
            for a, b in _ring_edges(ring):
                d2 = _point_segment_distance_sq(p, a, b)
                if best is None or d2 < best:
                    best = d2
    if best is None:
        raise CertificateInputError("geometry has no boundary segments")
    return best


def _canonical_geom(geom) -> dict:
    def frac(v):
        return f"{v.numerator}/{v.denominator}"
    return {"type": geom["type"], "polygons": [[[frac(x) + "," + frac(y) for x, y in ring] for ring in poly]
                                                   for poly in geom["polygons"]]}


def _sha(obj: Any) -> str:
    raw = json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _iter_rings(geom):
    for polygon in geom["polygons"]:
        yield from polygon


def verify_candidate_set(
    field_geometry: dict,
    obstacle_geometries: list[dict],
    candidate_points: list[dict],
    *,
    boundary_setback_m: Any = 0,
    obstacle_clearance_m: Any = 0,
    boundary_uncertainty_m: Any = 0,
    obstacle_uncertainty_m: Any = 0,
    minimum_spacing_m: Any | None = None,
    allow_empty_candidates: bool = False,
    max_pair_checks: int = 2_000_000,
) -> dict:
    """Certify a finite candidate set against exact rational source geometry.

    Distances are checked by comparing exact squared distances with exact squared
    rational clearances. Uncertainty allowances are explicit additive margins;
    this function never estimates or invents them. Coordinates are interpreted
    as canonical decimal values (float inputs via shortest round-trip decimal).
    """
    field = _parse_geometry(field_geometry, "field")
    if not isinstance(obstacle_geometries, list):
        raise CertificateInputError("obstacle_geometries must be a list")
    obstacles = [_parse_geometry(g, f"obstacle[{i}]") for i, g in enumerate(obstacle_geometries)]
    if not isinstance(candidate_points, list):
        raise CertificateInputError("candidate_points must be a list")
    bs = _q(boundary_setback_m, "boundary_setback_m")
    oc = _q(obstacle_clearance_m, "obstacle_clearance_m")
    bu = _q(boundary_uncertainty_m, "boundary_uncertainty_m")
    ou = _q(obstacle_uncertainty_m, "obstacle_uncertainty_m")
    if min(bs, oc, bu, ou) < 0:
        raise CertificateInputError("clearances and uncertainty allowances must be non-negative")
    effective_boundary = bs + bu
    effective_obstacle = oc + ou
    spacing = None if minimum_spacing_m is None else _q(minimum_spacing_m, "minimum_spacing_m")
    if spacing is not None and spacing < 0:
        raise CertificateInputError("minimum_spacing_m must be non-negative")
    if not candidate_points and not allow_empty_candidates:
        return {"status": "HOLD_EMPTY_CANDIDATE_SET", "certified": False,
                "reason": "empty candidate set is not accepted by default", "point_count": 0}

    parsed_points = []
    ids = set()
    seen_xy = set()
    per_point = []
    for index, item in enumerate(candidate_points):
        if not isinstance(item, dict):
            raise CertificateInputError(f"candidate_points[{index}] must be an object")
        pid = str(item.get("plant_id", f"P{index+1}"))
        if pid in ids:
            raise CertificateInputError(f"duplicate plant_id: {pid}")
        ids.add(pid)
        p = (_q(item.get("x_m"), f"{pid}.x_m"), _q(item.get("y_m"), f"{pid}.y_m"))
        if p in seen_xy:
            per_point.append({"plant_id": pid, "status": "FAIL", "reasons": ["DUPLICATE_COORDINATE"]})
        else:
            per_point.append(None)
        seen_xy.add(p)
        parsed_points.append((pid, p))

    pairwise_failures = []
    if spacing is not None:
        checks = len(parsed_points) * (len(parsed_points) - 1) // 2
        if checks > max_pair_checks:
            return {"status": "HOLD_PAIRWISE_CHECK_CAP", "certified": False,
                    "reason": f"{checks} pair checks exceeds max_pair_checks={max_pair_checks}",
                    "point_count": len(parsed_points)}
        spacing_sq = spacing * spacing
        for i in range(len(parsed_points)):
            for j in range(i + 1, len(parsed_points)):
                p, q = parsed_points[i][1], parsed_points[j][1]
                dx, dy = p[0] - q[0], p[1] - q[1]
                if dx * dx + dy * dy < spacing_sq:
                    pairwise_failures.append([parsed_points[i][0], parsed_points[j][0]])

    final_points = []
    for index, (pid, p) in enumerate(parsed_points):
        existing_duplicate = per_point[index] is not None
        reasons = ["DUPLICATE_COORDINATE"] if existing_duplicate else []
        field_rel = _geometry_relation(p, field)
        # When the required clearance is exactly zero, topology alone decides
        # covers semantics; calculating a nearest boundary segment is redundant.
        field_dist2 = (_minimum_boundary_distance_sq(p, field) if effective_boundary > 0 else None)
        if field_rel == -1:
            reasons.append("OUTSIDE_FIELD_OR_INSIDE_FIELD_HOLE")
        elif effective_boundary > 0 and field_dist2 < effective_boundary * effective_boundary:
            reasons.append("BOUNDARY_CLEARANCE_BELOW_REQUIRED_MARGIN")
        obstacle_details = []
        for oi, obstacle in enumerate(obstacles):
            rel = _geometry_relation(p, obstacle)
            dist2 = (_minimum_boundary_distance_sq(p, obstacle) if effective_obstacle > 0 else None)
            passed = (rel != 1 and (effective_obstacle == 0 or dist2 >= effective_obstacle * effective_obstacle))
            obstacle_details.append({"obstacle_index": oi, "relation": {1: "INSIDE", 0: "BOUNDARY", -1: "OUTSIDE"}[rel],
                                     "clearance_passed": passed,
                                     "minimum_distance_squared": None if dist2 is None else f"{dist2.numerator}/{dist2.denominator}"})
            if rel == 1:
                reasons.append(f"INSIDE_OBSTACLE_{oi}")
            elif effective_obstacle > 0 and dist2 < effective_obstacle * effective_obstacle:
                reasons.append(f"OBSTACLE_CLEARANCE_BELOW_REQUIRED_MARGIN_{oi}")
        field_pass = field_rel != -1 and (effective_boundary == 0 or field_dist2 >= effective_boundary * effective_boundary)
        final_points.append({
            "plant_id": pid,
            "status": "PASS" if not reasons else "FAIL",
            "reasons": reasons,
            "field_relation": {1: "INSIDE", 0: "BOUNDARY", -1: "OUTSIDE"}[field_rel],
            "boundary_clearance_passed": field_pass,
            "minimum_boundary_distance_squared": None if field_dist2 is None else f"{field_dist2.numerator}/{field_dist2.denominator}",
            "required_boundary_clearance_squared": f"{(effective_boundary*effective_boundary).numerator}/{(effective_boundary*effective_boundary).denominator}",
            "obstacles": obstacle_details,
        })

    pairwise_by_id = {pid: [] for pid, _ in parsed_points}
    for a, b in pairwise_failures:
        pairwise_by_id[a].append(b)
        pairwise_by_id[b].append(a)
    for point in final_points:
        if pairwise_by_id[point["plant_id"]]:
            point["status"] = "FAIL"
            point["reasons"].append("MINIMUM_SPACING_VIOLATION")
            point["spacing_violations_with"] = pairwise_by_id[point["plant_id"]]

    failures = [p for p in final_points if p["status"] != "PASS"]
    all_pass = not failures and not pairwise_failures
    cert_payload = {
        "field": _canonical_geom(field),
        "obstacles": [_canonical_geom(g) for g in obstacles],
        "points": [{"plant_id": pid, "x": str(p[0]), "y": str(p[1])} for pid, p in parsed_points],
        "effective_boundary_clearance": str(effective_boundary),
        "effective_obstacle_clearance": str(effective_obstacle),
        "minimum_spacing": None if spacing is None else str(spacing),
    }
    return {
        "schema": "prouve-formal-feasibility-certificate-v0.1",
        "status": "CERTIFIED_FEASIBLE" if all_pass else "CERTIFIED_INFEASIBLE",
        "certified": True,
        "feasibility_passed": all_pass,
        "point_count": len(parsed_points),
        "passed_points": len(parsed_points) - len(failures),
        "failed_points": len(failures),
        "pairwise_spacing_checks": (len(parsed_points) * (len(parsed_points) - 1) // 2) if spacing is not None else 0,
        "pairwise_spacing_failures": pairwise_failures,
        "arithmetic": "exact rational arithmetic on canonical decimal inputs; no epsilon in point-in-polygon or squared-distance comparisons",
        "input_interpretation": "decimal strings/integers are exact; finite floats are interpreted by their shortest round-trip decimal string",
        "geometry_scope": "GeoJSON Polygon/MultiPolygon, including interior rings (holes); MultiPolygon components must be strictly disjoint and non-touching",
        "clearance_policy": "required_clearance = declared_clearance + explicitly supplied uncertainty allowance; no uncertainty is inferred",
        "optimality_claim": False,
        "source_geometry_sha256": _sha({"field": _canonical_geom(field), "obstacles": [_canonical_geom(g) for g in obstacles]}),
        "candidate_set_sha256": _sha(cert_payload),
        "effective_boundary_clearance_m": str(effective_boundary),
        "effective_obstacle_clearance_m": str(effective_obstacle),
        "minimum_spacing_m": None if spacing is None else str(spacing),
        "points": final_points,
        "limitations": [
            "This certifies feasibility of the finite submitted candidate set relative to the serialized source geometry and declared margins; it does not certify global optimality.",
            "CRS/datum correctness, survey accuracy, source provenance, and whether uncertainty allowances are adequate require separate gates.",
            "MultiPolygon components that touch or cross are rejected rather than normalized.",
            "Input decimal values are treated as exact mathematical values; this is not a claim about physical measurement truth."
        ]
    }


def case_to_geojson(case: dict) -> tuple[dict, list[dict]]:
    """Convert the current V0.2 case shape to GeoJSON Polygon inputs."""
    field = case.get("field", {})
    if isinstance(field, dict) and "geometry" in field:
        field_geom = field["geometry"]
    elif isinstance(field, dict) and field.get("type") in ("Polygon", "MultiPolygon"):
        field_geom = field
    else:
        verts = field.get("vertices", []) if isinstance(field, dict) else []
        ring = list(verts)
        if ring and ring[0] != ring[-1]:
            ring.append(ring[0])
        field_geom = {"type": "Polygon", "coordinates": [ring]}
    obstacles = []
    for spec in case.get("obstacles", []):
        if "geometry" in spec:
            obstacles.append(spec["geometry"])
        elif spec.get("type") in ("Polygon", "MultiPolygon"):
            obstacles.append(spec)
        else:
            ring = list(spec.get("vertices", []))
            if ring and ring[0] != ring[-1]:
                ring.append(ring[0])
            obstacles.append({"type": "Polygon", "coordinates": [ring]})
    return field_geom, obstacles


def verify_case_points(case: dict, points: list[dict], *, minimum_spacing_m: Any | None = None) -> dict:
    field, obstacles = case_to_geojson(case)
    settings = case.get("settings", {})
    uncertainty = case.get("verification_uncertainty", {})
    return verify_candidate_set(
        field, obstacles, points,
        boundary_setback_m=settings.get("boundary_setback_m", 0),
        obstacle_clearance_m=settings.get("obstacle_buffer_m", 0),
        boundary_uncertainty_m=uncertainty.get("boundary_m", 0),
        obstacle_uncertainty_m=uncertainty.get("obstacle_m", 0),
        minimum_spacing_m=minimum_spacing_m,
    )
