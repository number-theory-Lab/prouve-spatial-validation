#!/usr/bin/env python3
"""PROUVE Spatial V0.2 - usable planting area geometry engine.

Coordinates are local planar XY coordinates in metres. This is not a
latitude/longitude engine. Requires Shapely >= 2.0.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

from shapely.geometry import Polygon, mapping
from shapely.ops import unary_union
from shapely.validation import explain_validity

DEFAULT_QUAD_SEGS = 64
DEFAULT_TOLERANCE = 1e-7


class GeometryInputError(ValueError):
    """Raised when the supplied field/obstacle geometry is invalid."""


def _points_to_polygon(points: list[list[float]], name: str) -> Polygon:
    if not isinstance(points, list) or len(points) < 3:
        raise GeometryInputError(f"{name}: ต้องมีพิกัดอย่างน้อย 3 จุด")
    try:
        normalized = []
        for idx, point in enumerate(points, start=1):
            if not isinstance(point, (list, tuple)) or len(point) != 2:
                raise GeometryInputError(f"{name}: จุดที่ {idx} ต้องมีพิกัด [x,y] เท่านั้น")
            if any(isinstance(v, bool) for v in point):
                raise GeometryInputError(f"{name}: จุดที่ {idx} ห้ามใช้ boolean เป็นพิกัด")
            x, y = float(point[0]), float(point[1])
            normalized.append((x, y))
    except (TypeError, ValueError, IndexError) as exc:
        if isinstance(exc, GeometryInputError):
            raise
        raise GeometryInputError(f"{name}: รูปแบบพิกัดต้องเป็น [[x,y], ...]") from exc
    if any(not math.isfinite(x) or not math.isfinite(y) for x, y in normalized):
        raise GeometryInputError(f"{name}: พิกัดต้องเป็นตัวเลขจำกัด ไม่ใช่ NaN/Infinity")
    # Permit a repeated closing point in input, but Shapely closes the ring itself.
    if len(normalized) >= 4 and normalized[0] == normalized[-1]:
        normalized = normalized[:-1]
    if len(set(normalized)) < 3:
        raise GeometryInputError(f"{name}: ต้องมีจุดพิกัดที่แตกต่างกันอย่างน้อย 3 จุด")
    geom = Polygon(normalized)
    if geom.is_empty or geom.area <= 0:
        raise GeometryInputError(f"{name}: รูปหลายเหลี่ยมไม่มีพื้นที่")
    if not geom.is_valid:
        raise GeometryInputError(f"{name}: รูปทรงไม่ถูกต้อง ({explain_validity(geom)})")
    return geom


def _conservative_buffer_radius(distance: float, quad_segs: int) -> float:
    """Slightly inflate round buffers so polygonized arcs do not under-clear.

    A circular arc is approximated with straight chords. Dividing the requested
    distance by cos(pi/(4*q)) compensates for the maximum half-segment angle,
    making the chord apothem at least the requested distance.
    """
    if distance == 0:
        return 0.0
    half_step = math.pi / (4.0 * quad_segs)
    return distance / math.cos(half_step)


def _inward_buffer_with_clearance(
    field: Polygon, distance: float, quad_segs: int, tolerance: float
):
    if distance == 0:
        return field
    actual = distance
    # For typical valid simple polygons the first pass meets the clearance.
    # If numerical/geometric approximation falls short, shrink slightly more.
    for _ in range(8):
        inset = field.buffer(-actual, quad_segs=quad_segs, join_style="round")
        if inset.is_empty:
            return inset
        measured = inset.distance(field.boundary)
        if measured >= distance - tolerance:
            return inset
        actual += (distance - measured) + max(tolerance, 1e-9)
    raise GeometryInputError(
        "ไม่สามารถสร้างพื้นที่เว้นขอบที่ยืนยันระยะปลอดภัยได้ภายในจำนวนครั้งที่กำหนด"
    )


def compute_usable_area(case: dict[str, Any]) -> dict[str, Any]:
    """Compute inset field minus buffered obstacles and return metrics/geometries."""
    if not isinstance(case, dict):
        raise GeometryInputError("case ต้องเป็น object/dictionary")
    settings = case.get("settings", {})
    if not isinstance(settings, dict):
        raise GeometryInputError("settings ต้องเป็น object/dictionary")
    raw_setback = settings.get("boundary_setback_m", 0.5)
    raw_obstacle_clearance = settings.get("obstacle_buffer_m", 0.5)
    raw_quad_segs = settings.get("quad_segs", DEFAULT_QUAD_SEGS)
    raw_tolerance = settings.get("geometry_tolerance_m", DEFAULT_TOLERANCE)
    if any(isinstance(v, bool) for v in (raw_setback, raw_obstacle_clearance, raw_quad_segs, raw_tolerance)):
        raise GeometryInputError("settings ต้องเป็นค่าตัวเลข ไม่ใช่ boolean")
    try:
        setback = float(raw_setback)
        obstacle_clearance = float(raw_obstacle_clearance)
        quad_segs_float = float(raw_quad_segs)
        tolerance = float(raw_tolerance)
    except (TypeError, ValueError) as exc:
        raise GeometryInputError("settings มีค่าที่ไม่ใช่ตัวเลข") from exc
    if not math.isfinite(quad_segs_float) or not quad_segs_float.is_integer():
        raise GeometryInputError("quad_segs ต้องเป็นจำนวนเต็มที่มีค่าจำกัด")
    quad_segs = int(quad_segs_float)

    if not all(math.isfinite(v) and v >= 0 for v in (setback, obstacle_clearance)):
        raise GeometryInputError("ระยะเว้นขอบและระยะ buffer ต้องเป็นตัวเลขตั้งแต่ 0 ขึ้นไป")
    if quad_segs < 8:
        raise GeometryInputError("quad_segs ต้องไม่น้อยกว่า 8 เพื่อควบคุมความคลาดเคลื่อนของส่วนโค้ง")
    if not math.isfinite(tolerance) or tolerance <= 0:
        raise GeometryInputError("geometry_tolerance_m ต้องเป็นค่าบวก")

    field_spec = case.get("field", {})
    if not isinstance(field_spec, dict):
        raise GeometryInputError("field ต้องเป็น object/dictionary")
    raw_field_vertices = field_spec.get("vertices", [])
    obstacle_specs = case.get("obstacles", [])
    # Reject coordinate magnitudes whose double-precision spacing exceeds the
    # declared geometric tolerance. This prevents silently claiming sub-ULP
    # clearance accuracy for very large absolute coordinate offsets.
    raw_coordinate_values = []
    for label, vertices in [("field", raw_field_vertices)] + [
        (f"obstacle_{idx}", spec.get("vertices", []) if isinstance(spec, dict) else [])
        for idx, spec in enumerate(obstacle_specs, start=1)
    ]:
        if isinstance(vertices, list):
            for point in vertices:
                if isinstance(point, (list, tuple)) and len(point) == 2:
                    for value in point:
                        if isinstance(value, (int, float)) and not isinstance(value, bool):
                            fv = float(value)
                            if math.isfinite(fv):
                                raw_coordinate_values.append(abs(fv))
    max_abs_coordinate = max(raw_coordinate_values, default=0.0)
    coordinate_ulp = math.ulp(max_abs_coordinate) if max_abs_coordinate else math.ulp(0.0)
    if coordinate_ulp > tolerance:
        raise GeometryInputError(
            "ความละเอียดพิกัด double-precision ไม่เพียงพอ: ULP ของพิกัดสูงสุด "
            f"({coordinate_ulp:.6g} m) มากกว่า geometry_tolerance_m ({tolerance:.6g} m). "
            "โปรดแปลงข้อมูลเป็น local XY โดยเลื่อนจุดกำเนิดให้อยู่ใกล้แปลงก่อนคำนวณ"
        )

    field = _points_to_polygon(raw_field_vertices, "ขอบเขตแปลง")
    if not isinstance(obstacle_specs, list):
        raise GeometryInputError("obstacles ต้องเป็นรายการ แม้ไม่มีสิ่งกีดขวางให้ใช้ []")
    obstacles: list[Polygon] = []
    obstacle_names: list[str] = []
    for idx, spec in enumerate(obstacle_specs, start=1):
        if not isinstance(spec, dict):
            raise GeometryInputError(f"obstacles[{idx}] ต้องเป็น object/dictionary")
        name = str(spec.get("name", f"สิ่งกีดขวาง {idx}"))
        obstacle = _points_to_polygon(spec.get("vertices", []), name)
        if not field.covers(obstacle):
            raise GeometryInputError(f"{name}: ต้องอยู่ภายในหรืออยู่บนขอบเขตแปลงทั้งหมด")
        obstacles.append(obstacle)
        obstacle_names.append(name)

    inset_field = _inward_buffer_with_clearance(field, setback, quad_segs, tolerance)
    if inset_field.is_empty:
        empty = Polygon()
        return _assemble_result(
            field, obstacles, empty, empty, empty, setback, obstacle_clearance,
            quad_segs, 0.0, tolerance, obstacle_names
        )

    if obstacles and obstacle_clearance > 0:
        effective_radius = _conservative_buffer_radius(obstacle_clearance, quad_segs)
        buffered = [
            obs.buffer(effective_radius, quad_segs=quad_segs, join_style="round")
            for obs in obstacles
        ]
        obstacle_union = unary_union(buffered)
        excluded_inside = obstacle_union.intersection(inset_field)
    elif obstacles:
        effective_radius = 0.0
        obstacle_union = unary_union(obstacles)
        excluded_inside = obstacle_union.intersection(inset_field)
    else:
        effective_radius = 0.0
        obstacle_union = Polygon()
        excluded_inside = Polygon()

    usable = inset_field.difference(excluded_inside)
    # Clean tiny numerical remnants while keeping the geometry valid.
    if not usable.is_valid:
        usable = usable.buffer(0)
    if not usable.is_valid:
        raise GeometryInputError("ผลลัพธ์พื้นที่ปลูกไม่ผ่านการตรวจสอบความถูกต้องของเรขาคณิต")

    return _assemble_result(
        field, obstacles, inset_field, obstacle_union, usable, setback,
        obstacle_clearance, quad_segs, effective_radius, tolerance,
        obstacle_names, excluded_inside
    )


def _assemble_result(
    field, obstacles, inset_field, obstacle_union, usable,
    setback, obstacle_clearance, quad_segs, effective_radius, tolerance,
    obstacle_names, excluded_inside=None
):
    if excluded_inside is None:
        excluded_inside = Polygon()
    field_area = float(field.area)
    inset_area = float(inset_field.area) if not inset_field.is_empty else 0.0
    usable_area = float(usable.area) if not usable.is_empty else 0.0
    boundary_loss = max(0.0, field_area - inset_area)
    obstacle_exclusion = max(0.0, inset_area - usable_area)
    total_loss = max(0.0, field_area - usable_area)

    boundary_clearance = (
        float(inset_field.distance(field.boundary)) if not inset_field.is_empty else None
    )
    obstacle_clearances = []
    for name, obs in zip(obstacle_names, obstacles):
        distance = None if usable.is_empty else float(usable.distance(obs.boundary))
        obstacle_clearances.append({"name": name, "minimum_clearance_m": distance})

    def geom_type(geom):
        return "Empty" if geom.is_empty else geom.geom_type

    def component_count(geom):
        if geom.is_empty:
            return 0
        if geom.geom_type == "Polygon":
            return 1
        if geom.geom_type == "MultiPolygon":
            return len(geom.geoms)
        if hasattr(geom, "geoms"):
            return sum(component_count(g) for g in geom.geoms)
        return 0

    result = {
        "project": "PROUVE Spatial",
        "version": "0.2",
        "use_case": "PS-FU01",
        "coordinate_system": "Local planar XY; metres",
        "parameters": {
            "boundary_setback_m": setback,
            "obstacle_buffer_m": obstacle_clearance,
            "buffer_quad_segs_per_quadrant": quad_segs,
            "obstacle_buffer_applied_radius_m": effective_radius,
            "geometry_tolerance_m": tolerance,
        },
        "areas_m2": {
            "total_field": field_area,
            "after_boundary_setback": inset_area,
            "boundary_setback_loss": boundary_loss,
            "obstacle_exclusion_inside_setback_field": obstacle_exclusion,
            "usable_planting_area": usable_area,
            "total_excluded_area": total_loss,
        },
        "geometry": {
            "inset_field_type": geom_type(inset_field),
            "usable_area_type": geom_type(usable),
            "usable_component_count": component_count(usable),
            "field_geometry_valid": bool(field.is_valid),
            "inset_geometry_valid": bool(inset_field.is_valid) if not inset_field.is_empty else True,
            "usable_geometry_valid": bool(usable.is_valid),
            "minimum_boundary_clearance_m": boundary_clearance,
            "obstacle_clearances": obstacle_clearances,
        },
        "status": {
            "input_geometry_validated": True,
            "usable_area_calculated": True,
            "usable_area_nonempty": not usable.is_empty,
            "boundary_clearance_verified": (
                boundary_clearance is None or boundary_clearance >= setback - tolerance
            ),
            "obstacle_clearance_verified": all(
                item["minimum_clearance_m"] is None
                or item["minimum_clearance_m"] >= obstacle_clearance - tolerance
                for item in obstacle_clearances
            ),
            "placement_optimization_performed": False,
            "maximum_plant_count_proven": False,
        },
        "notes": [
            "ผลนี้เป็นพื้นที่เชิงเรขาคณิตหลังเว้นขอบและสิ่งกีดขวาง ไม่ใช่จำนวนต้นที่ปลูกได้",
            "การ buffer แบบโค้งใช้การประมาณด้วยเส้นตรง 64 ส่วนต่อหนึ่งควอดแรนต์ และชดเชยรัศมีแบบ conservative เพื่อไม่ให้ระยะเคลียร์รันซ์ต่ำกว่าค่าที่กำหนด",
            "พิกัดเป็น local XY หน่วยเมตร ไม่ใช่ latitude/longitude และยังไม่ใช่ขอบเขตสำรวจ GPS จริง",
        ],
    }
    geometries = {
        "field": field,
        "obstacles": obstacles,
        "inset_field": inset_field,
        "obstacle_buffer_union": obstacle_union,
        "excluded_inside": excluded_inside,
        "usable": usable,
    }
    return {"result": result, "geometries": geometries}


def export_local_geometry_json(geometries: dict[str, Any], path: Path) -> None:
    """Export geometry using local XY metre coordinates (not RFC7946 GeoJSON)."""
    items = []
    for key in ("field", "inset_field", "obstacle_buffer_union", "usable"):
        geom = geometries[key]
        items.append({"name": key, "geometry_type": "Empty" if geom.is_empty else geom.geom_type,
                      "coordinates": None if geom.is_empty else mapping(geom)["coordinates"]})
    items.append({"name": "obstacles", "geometries": [mapping(g) for g in geometries["obstacles"]]})
    path.write_text(json.dumps({"coordinate_system": "Local planar XY; metres", "features": items},
                               ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="PROUVE Spatial V0.2 usable area calculator")
    parser.add_argument("case", nargs="?", default="PS-FU01.json", help="input case JSON")
    parser.add_argument("--output", default="v02_output.json", help="output results JSON")
    parser.add_argument("--geometry", default="usable_area_local_xy.json", help="output local geometry JSON")
    args = parser.parse_args()
    case_path = Path(args.case)
    case = json.loads(case_path.read_text(encoding="utf-8"))
    computed = compute_usable_area(case)
    Path(args.output).write_text(json.dumps(computed["result"], ensure_ascii=False, indent=2), encoding="utf-8")
    export_local_geometry_json(computed["geometries"], Path(args.geometry))
    print(json.dumps(computed["result"]["areas_m2"], ensure_ascii=False, indent=2))
    print("boundary clearance verified:", computed["result"]["status"]["boundary_clearance_verified"])
    print("obstacle clearance verified:", computed["result"]["status"]["obstacle_clearance_verified"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
