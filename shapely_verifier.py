"""Second, GEOS/Shapely-based feasibility checker for pipeline cross-checks."""
from __future__ import annotations
import math
import shapely
from shapely.geometry import Point
from geometry_engine_v02 import compute_usable_area


def verify_plan_shapely(case: dict, result: dict) -> dict:
    if not isinstance(result, dict) or not isinstance(case, dict):
        raise ValueError("case and result must be objects")
    computed = compute_usable_area(case)
    usable = computed["geometries"]["usable"]
    points = result.get("planting_positions")
    if not isinstance(points, list) or not points:
        return {"verifier": "shapely_geos_v1", "all_checks_passed": False,
                "verified_point_count": 0, "status": "NO_FEASIBLE_POINTS",
                "reason": "EMPTY_PLAN_NOT_ELIGIBLE_FOR_VERIFICATION"}
    xs, ys = [], []
    seen_indices, seen_coords = set(), set()
    failures = {"outside_usable_geometry": 0, "invalid_coordinates": 0,
                "duplicate_lattice_indices": 0, "duplicate_coordinates": 0,
                "declared_count_mismatch": 0}
    layout = result.get("search", {}).get("rectangular_crop_row", {})
    declared = layout.get("best_count")
    if declared is not None and (isinstance(declared, bool) or not isinstance(declared, int) or declared != len(points)):
        failures["declared_count_mismatch"] += 1
    for p in points:
        if not isinstance(p, dict):
            failures["invalid_coordinates"] += 1
            continue
        x, y, i, j = p.get("x_m"), p.get("y_m"), p.get("lattice_i"), p.get("lattice_j")
        if (isinstance(x, bool) or isinstance(y, bool) or not isinstance(x, (int, float)) or
            not isinstance(y, (int, float)) or not math.isfinite(float(x)) or not math.isfinite(float(y)) or
            isinstance(i, bool) or isinstance(j, bool) or not isinstance(i, int) or not isinstance(j, int)):
            failures["invalid_coordinates"] += 1
            continue
        x, y = float(x), float(y)
        xs.append(x); ys.append(y)
        if (i, j) in seen_indices:
            failures["duplicate_lattice_indices"] += 1
        seen_indices.add((i, j))
        ck = (round(x, 9), round(y, 9))
        if ck in seen_coords:
            failures["duplicate_coordinates"] += 1
        seen_coords.add(ck)
    if xs:
        geoms = shapely.points(xs, ys)
        mask = shapely.covers(usable, geoms)
        failures["outside_usable_geometry"] = int((~mask).sum())
    passed = all(v == 0 for v in failures.values()) and len(xs) == len(points)
    return {"verifier": "shapely_geos_v1", "all_checks_passed": passed,
            "verified_point_count": len(points), "status": "VERIFIED_FEASIBLE" if passed else "VERIFICATION_FAILED",
            "checks": failures,
            "scope": "GEOS/ Shapely coverage check against independently reconstructed usable geometry; shares geometry library with engine and is not the no-Shapely reference check."}
