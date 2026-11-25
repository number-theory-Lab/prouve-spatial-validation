from pathlib import Path

ROOT = Path(__file__).resolve().parent

# Geometry hardening: strict numeric/type validation and explicit empty-area status.
p = ROOT / 'geometry_engine_v02.py'
s = p.read_text(encoding='utf-8')
s = s.replace('''    try:
        normalized = [(float(p[0]), float(p[1])) for p in points]
    except (TypeError, ValueError, IndexError) as exc:
        raise GeometryInputError(f"{name}: รูปแบบพิกัดต้องเป็น [[x,y], ...]") from exc
''','''    try:
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
''')
s = s.replace('''    settings = case.get("settings", {})
    setback = float(settings.get("boundary_setback_m", 0.5))
    obstacle_clearance = float(settings.get("obstacle_buffer_m", 0.5))
    quad_segs = int(settings.get("quad_segs", DEFAULT_QUAD_SEGS))
    tolerance = float(settings.get("geometry_tolerance_m", DEFAULT_TOLERANCE))

    if not all(math.isfinite(v) and v >= 0 for v in (setback, obstacle_clearance)):
''','''    if not isinstance(case, dict):
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
''')
s = s.replace('''    field = _points_to_polygon(case.get("field", {}).get("vertices", []), "ขอบเขตแปลง")
    obstacle_specs = case.get("obstacles", [])
''','''    field_spec = case.get("field", {})
    if not isinstance(field_spec, dict):
        raise GeometryInputError("field ต้องเป็น object/dictionary")
    field = _points_to_polygon(field_spec.get("vertices", []), "ขอบเขตแปลง")
    obstacle_specs = case.get("obstacles", [])
    if not isinstance(obstacle_specs, list):
        raise GeometryInputError("obstacles ต้องเป็นรายการ แม้ไม่มีสิ่งกีดขวางให้ใช้ []")
''')
s = s.replace('''    for idx, spec in enumerate(obstacle_specs, start=1):
        name = str(spec.get("name", f"สิ่งกีดขวาง {idx}"))
''','''    for idx, spec in enumerate(obstacle_specs, start=1):
        if not isinstance(spec, dict):
            raise GeometryInputError(f"obstacles[{idx}] ต้องเป็น object/dictionary")
        name = str(spec.get("name", f"สิ่งกีดขวาง {idx}"))
''')
s = s.replace('''            "usable_area_calculated": True,
            "boundary_clearance_verified": (
''','''            "input_geometry_validated": True,
            "usable_area_calculated": True,
            "usable_area_nonempty": not usable.is_empty,
            "boundary_clearance_verified": (
''')
p.write_text(s, encoding='utf-8')

# Safety rules imported by patched optimizer and pipeline.

# Optimization hardening and honest bound status.
p = ROOT / 'optimization_engine_v04.py'
s = p.read_text(encoding='utf-8')
s = s.replace('''from geometry_engine_v02 import compute_usable_area, GeometryInputError
''','''from geometry_engine_v02 import compute_usable_area, GeometryInputError
from engine_safety import classify_optimality, conservative_integer_upper_bound
''')
s = s.replace('''def _make_specs(row_spacing: float, in_row_spacing: float) -> dict[str, LatticeSpec]:
    rect_area = row_spacing * in_row_spacing
''','''def _finite_positive(value: Any, name: str) -> float:
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
''')
s = s.replace('''    t = math.radians(theta_deg)
''','''    if isinstance(theta_deg, bool) or not math.isfinite(float(theta_deg)):
        raise OptimizationInputError("theta_deg ต้องเป็นตัวเลขที่มีค่าจำกัด")
    t = math.radians(theta_deg)
''', 1)
s = s.replace('''    js = np.arange(j0, j1 + 1, dtype=np.int32)
    ii = np.arange(i0, i1 + 1, dtype=np.int32)
''','''    if max(abs(j0), abs(j1), abs(i0), abs(i1)) > np.iinfo(np.int64).max - 2:
        raise OptimizationInputError("ขอบเขตดัชนี lattice เกินช่วง int64")
    candidate_total = (j1 - j0 + 1) * (i1 - i0 + 1)
    if candidate_total < 0 or candidate_total > 5_000_000:
        raise OptimizationInputError("จำนวน candidate points เกินขีดจำกัดความปลอดภัย 5,000,000 จุด")
    js = np.arange(j0, j1 + 1, dtype=np.int64)
    ii = np.arange(i0, i1 + 1, dtype=np.int64)
''')
s = s.replace('''def _phase_values(divisions: int) -> list[float]:
    if divisions < 2:
        raise OptimizationInputError("phase_divisions ต้องไม่น้อยกว่า 2")
''','''def _phase_values(divisions: int) -> list[float]:
    if isinstance(divisions, bool) or not isinstance(divisions, int) or divisions < 2:
        raise OptimizationInputError("phase_divisions ต้องเป็นจำนวนเต็มตั้งแต่ 2 ขึ้นไป")
    if divisions > 200:
        raise OptimizationInputError("phase_divisions เกินขีดจำกัด 200 ใน branch รุ่นนี้")
''')
s = s.replace('''    if not (0 < angle_step_deg <= spec.angle_period_deg):
        raise OptimizationInputError("angle_step_deg ไม่อยู่ในช่วงที่ถูกต้อง")
    phases = _phase_values(phase_divisions)
''','''    if isinstance(angle_step_deg, bool) or not math.isfinite(float(angle_step_deg)) or not (0 < angle_step_deg <= spec.angle_period_deg):
        raise OptimizationInputError("angle_step_deg ต้องเป็นค่าจำกัดในช่วง (0, angle_period_deg]")
    if not math.isfinite(float(refine_angle_step_deg)) or refine_angle_step_deg <= 0:
        raise OptimizationInputError("refine_angle_step_deg ต้องเป็นค่าบวกและมีค่าจำกัด")
    if isinstance(refine_phase_divisions, bool) or not isinstance(refine_phase_divisions, int) or refine_phase_divisions < 1:
        raise OptimizationInputError("refine_phase_divisions ต้องเป็นจำนวนเต็มตั้งแต่ 1 ขึ้นไป")
    if isinstance(top_k, bool) or not isinstance(top_k, int) or top_k < 0:
        raise OptimizationInputError("top_k ต้องเป็นจำนวนเต็มตั้งแต่ 0 ขึ้นไป")
    phases = _phase_values(phase_divisions)
''')
s = s.replace('''    # ceil is intentionally conservative under floating point round-off.
    upper = int(math.ceil(quotient - 1e-12))
    return {
''','''    # No epsilon is subtracted before ceil. Because Shapely/GEOS area and
    # buffering are floating-point calculations, this is still an estimate,
    # not a formally certified real-arithmetic upper bound.
    bound_conversion = conservative_integer_upper_bound(
        quotient, source_bound_certified=False
    )
    upper = bound_conversion["upper_bound_count"]
    return {
''')
s = s.replace('''        "upper_bound_count": upper,
        "circumradius_m": spec.circumradius,
''','''        "upper_bound_count": upper,
        "upper_bound_certified": False,
        "upper_bound_status": "ESTIMATE_ONLY_FLOATING_GEOMETRY",
        "rounding_rule": "ceil(q); no epsilon subtraction",
        "circumradius_m": spec.circumradius,
''')
s = s.replace('''        return {"expanded_area_m2": 0.0, "cell_area_m2": spec.cell_area,
                "upper_bound_count": 0, "circumradius_m": spec.circumradius}
''','''        return {"expanded_area_m2": 0.0, "cell_area_m2": spec.cell_area,
                "upper_bound_count": 0, "upper_bound_certified": False,
                "upper_bound_status": "ESTIMATE_ONLY_EMPTY_GEOMETRY",
                "circumradius_m": spec.circumradius}
''')
s = s.replace('''    if row_spacing <= 0 or in_row_spacing <= 0 or plants_per_hole <= 0:
        raise OptimizationInputError("ข้อมูลระยะปลูกและจำนวนต้นต่อหลุมต้องเป็นค่าบวก")
''','''    row_spacing = _finite_positive(row_spacing, "crop.row_spacing_m")
    in_row_spacing = _finite_positive(in_row_spacing, "crop.in_row_spacing_m")
    if isinstance(plants_per_hole, bool) or not isinstance(plants_per_hole, int) or plants_per_hole <= 0:
        raise OptimizationInputError("plants_per_hole_after_thinning ต้องเป็นจำนวนเต็มบวก")
''')
s = s.replace('''    rectangular_gap = max(0.0, (rectangular_bound["upper_bound_count"] - rectangular_search["best_count"]) / rectangular_bound["upper_bound_count"]) if rectangular_bound["upper_bound_count"] else 0.0
''','''    rectangular_gap = ((rectangular_bound["upper_bound_count"] - rectangular_search["best_count"]) / rectangular_bound["upper_bound_count"]
                       if rectangular_bound["upper_bound_count"] > 0 else None)
    if rectangular_search["best_count"] > rectangular_bound["upper_bound_count"]:
        rectangular_optimality_status = "BOUND_CONFLICT"
    elif rectangular_search["best_count"] == 0:
        rectangular_optimality_status = "NO_FEASIBLE_POINTS_IN_ENUMERATED_SEARCH"
    else:
        rectangular_optimality_status = "BEST_FOUND_NOT_PROVEN_OPTIMAL"
''')
s = s.replace('''        search["relative_gap"] = max(0.0, (ub - search["best_count"]) / ub) if ub else 0.0
        search["proven_optimal_over_continuous_lattice_family"] = search["best_count"] >= ub
''','''        search["relative_gap"] = ((ub - search["best_count"]) / ub) if ub > 0 else None
        search["proven_optimal_over_continuous_lattice_family"] = False
        search["optimality_status_pre_verification"] = (
            "BOUND_CONFLICT" if search["best_count"] > ub else
            "NO_FEASIBLE_POINTS_IN_ENUMERATED_SEARCH" if search["best_count"] == 0 else
            "BEST_FOUND_NOT_PROVEN_OPTIMAL"
        )
''')
s = s.replace('''                "continuous_lattice_optimum_proven": rectangular_search["best_count"] >= rectangular_bound["upper_bound_count"],
''','''                "continuous_lattice_optimum_proven": False,
                "optimality_status_pre_verification": rectangular_optimality_status,
''')
s = s.replace('''                    "continuous_lattice_optimum_proven": srch["proven_optimal_over_continuous_lattice_family"],
''','''                    "continuous_lattice_optimum_proven": False,
                    "optimality_status_pre_verification": srch["optimality_status_pre_verification"],
''')
s = s.replace('''            "continuous_lattice_optimum_proven": rectangular_search["best_count"] >= rectangular_bound["upper_bound_count"],
''','''            "continuous_lattice_optimum_proven": False,
            "optimality_status_pre_verification": rectangular_optimality_status,
            "upper_bound_certified": False,
''')
s = s.replace('''            "best_found_count": rectangular_search["best_count"],
            "upper_bound_count": rectangular_bound["upper_bound_count"],
''','''            "best_found_count": rectangular_search["best_count"],
            "upper_bound_count": rectangular_bound["upper_bound_count"],
            "upper_bound_certified": False,
            "upper_bound_status": rectangular_bound.get("upper_bound_status"),
''')
s = s.replace('''            "independent_verifier_required": True,
            "generated_points": len(points),
            "point_export": "optimized_planting_positions.csv",
            "status_before_independent_verification": "PENDING",
''','''            "independent_verifier_required": True,
            "generated_points": len(points),
            "point_export": "optimized_planting_positions.csv",
            "status_before_independent_verification": "PENDING",
            "verifier_passed": False,
            "optimality_certified": False,
''')
s = s.replace('''            "Geometric upper bound applies only to the specified lattice family, not arbitrary free point placements.",
''','''            "Geometric upper-bound count is estimate-only because Shapely/GEOS floating geometry is not outward-rounded or formally interval-certified.",
            "A finite-grid winner is not a continuous-family optimum; equality with an uncertified estimate is insufficient for an optimality claim.",
            "Geometric upper bound applies only to the specified lattice family, not arbitrary free point placements.",
''')
p.write_text(s, encoding='utf-8')
