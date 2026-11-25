#!/usr/bin/env python3
"""PROUVE Spatial V0.1 handoff adapter.

Converts an exported app boundary project (schema prouve-spatial-boundary-v0.5)
plus an explicit site/crop profile into the input shape expected by
geometry_engine_v02.compute_usable_area() and optimization_engine_v04.run_benchmarks().

This adapter does not run either engine and does not authorize field deployment.
It deliberately keeps exploratory, synthetic-demo, and reviewed-input states apart.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any


class HandoffError(ValueError):
    """Raised when app/profile data cannot safely be passed to the engines."""


SUPPORTED_METRIC_CRS = {"EPSG:32647", "EPSG:32648"}
SUPPORTED_INPUT_CRS = {"EPSG:4326", "EPSG:32647", "EPSG:32648", "LOCAL:METRE"}
LOCAL_CRS = "LOCAL:METRE"
APP_SCHEMA = "prouve-spatial-boundary-v0.5"
PROFILE_SCHEMA = "prouve-spatial-site-profile-v0.1"


def _canonical_bytes(obj: Any) -> bytes:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
                      allow_nan=False).encode("utf-8")


def _validate_polygonal_geojson(raw: Any, label: str) -> tuple[dict, int]:
    """Lightweight finite-coordinate gate; exact topology is rechecked downstream."""
    if not isinstance(raw, dict) or raw.get("type") not in {"Polygon", "MultiPolygon"}:
        raise HandoffError(f"{label}: ต้องเป็น GeoJSON Polygon หรือ MultiPolygon")
    coords = raw.get("coordinates")
    count = 0
    def walk(node, path):
        nonlocal count
        if not isinstance(node, (list, tuple)):
            raise HandoffError(f"{label}.{path}: invalid coordinate nesting")
        if len(node) >= 2 and isinstance(node[0], (int,float)) and not isinstance(node[0],bool):
            if len(node) != 2:
                raise HandoffError(f"{label}.{path}: V0.3 accepts 2-D XY coordinates only")
            x, y = _finite_number(node[0], f"{label}.{path}.x"), _finite_number(node[1], f"{label}.{path}.y")
            count += 1
            return [x,y]
        if not node:
            raise HandoffError(f"{label}.{path}: empty coordinate nesting")
        return [walk(child, f"{path}[{i}]") for i,child in enumerate(node)]
    clean = walk(coords, "coordinates")
    if count < 4:
        raise HandoffError(f"{label}: geometry needs at least one closed polygon ring")
    return {"type":raw["type"], "coordinates":clean}, count


def _sha256(obj: Any) -> str:
    return hashlib.sha256(_canonical_bytes(obj)).hexdigest()


def _finite_number(value: Any, name: str, *, minimum: float | None = None) -> float:
    if isinstance(value, bool):
        raise HandoffError(f"{name}: ต้องเป็นตัวเลข ไม่ใช่ true/false")
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise HandoffError(f"{name}: ต้องเป็นตัวเลข") from exc
    if not math.isfinite(result):
        raise HandoffError(f"{name}: ห้ามเป็น NaN หรือ Infinity")
    if minimum is not None and result < minimum:
        raise HandoffError(f"{name}: ต้องมีค่าไม่น้อยกว่า {minimum}")
    return result


def _points(value: Any, name: str) -> list[list[float]]:
    if not isinstance(value, list) or len(value) < 3:
        raise HandoffError(f"{name}: ต้องมีพิกัดอย่างน้อย 3 จุด")
    out: list[list[float]] = []
    for i, point in enumerate(value, start=1):
        if not isinstance(point, (list, tuple)) or len(point) < 2:
            raise HandoffError(f"{name} จุดที่ {i}: ต้องมี x และ y")
        x = _finite_number(point[0], f"{name}[{i}].x")
        y = _finite_number(point[1], f"{name}[{i}].y")
        out.append([x, y])
    if out[0] == out[-1]:
        out.pop()
    if len(out) < 3 or len({(p[0], p[1]) for p in out}) < 3:
        raise HandoffError(f"{name}: ต้องมีจุดที่แตกต่างกันอย่างน้อย 3 จุด")
    return out


def _review_ok(profile: dict[str, Any], key: str) -> bool:
    item = profile.get("reviews", {}).get(key, {})
    return isinstance(item, dict) and item.get("status") == "APPROVED" and bool(item.get("reviewer")) and bool(item.get("date"))


def adapt_project(app_doc: dict[str, Any], profile: dict[str, Any], *, mode: str = "exploratory") -> tuple[dict[str, Any], dict[str, Any]]:
    """Build engine case and audit record.

    Modes:
      - demo: permits LOCAL:METRE synthetic data; never field eligible.
      - exploratory: permits metric projected CRS and USER_CONFIRMED or
        SURVEY_VERIFIED boundaries; never field eligible.
      - field_candidate: requires SURVEY_VERIFIED + independent profile reviews.
        Even then, this is only an input gate, not field-deployment approval.
    """
    if mode not in {"demo", "exploratory", "field_candidate"}:
        raise HandoffError("mode ต้องเป็น demo, exploratory หรือ field_candidate")
    if not isinstance(app_doc, dict) or app_doc.get("schema") != APP_SCHEMA:
        raise HandoffError(f"ไฟล์แอปต้องมี schema={APP_SCHEMA}")
    if not isinstance(profile, dict) or profile.get("profile_schema") != PROFILE_SCHEMA:
        raise HandoffError(f"ไฟล์โปรไฟล์ต้องมี profile_schema={PROFILE_SCHEMA}")

    boundary = app_doc.get("boundary")
    handoff = app_doc.get("optimizerHandoff")
    if not isinstance(boundary, dict) or not isinstance(handoff, dict):
        raise HandoffError("ไม่พบ boundary หรือ optimizerHandoff ในไฟล์แอป")
    if handoff.get("acceptedForGeometryProcessing") is not True:
        raise HandoffError("แอประบุว่าแนวเขตยังไม่ผ่านการตรวจรูปทรงเบื้องต้น")
    validation = boundary.get("validation")
    if not isinstance(validation, dict) or validation.get("valid") is not True:
        raise HandoffError("validation.valid ต้องเป็น true; engine จะตรวจรูปทรงซ้ำอีกครั้ง")

    input_crs = boundary.get("inputระบบพิกัด")
    working_crs = boundary.get("workingระบบพิกัด")
    if input_crs not in SUPPORTED_INPUT_CRS:
        raise HandoffError("input CRS ไม่อยู่ในชุดที่รองรับของ Adapter รุ่นนี้")
    if (input_crs == LOCAL_CRS) != (working_crs == LOCAL_CRS):
        raise HandoffError("LOCAL:METRE ต้องเป็นทั้ง input CRS และ working CRS พร้อมกัน; ห้ามแปลง local เป็นพิกัดจริง")
    units = boundary.get("units")
    boundary_status = boundary.get("status")
    if units not in {"เมตร", "metre", "meter", "m"}:
        raise HandoffError("พิกัดทำงานต้องระบุหน่วยเป็นเมตร")
    if working_crs == LOCAL_CRS:
        if mode != "demo":
            raise HandoffError("LOCAL:METRE ใช้ได้เฉพาะ mode=demo เท่านั้น ห้ามใช้เป็นพิกัดแปลงจริง")
    elif working_crs not in SUPPORTED_METRIC_CRS:
        raise HandoffError("รองรับพิกัดคำนวณจริงเฉพาะ EPSG:32647 หรือ EPSG:32648 ใน adapter รุ่นนี้")

    if mode == "demo":
        if working_crs != LOCAL_CRS:
            raise HandoffError("mode=demo รุ่นนี้สงวนไว้สำหรับพิกัด LOCAL:METRE เท่านั้น")
    else:
        if boundary_status not in {"USER_CONFIRMED", "SURVEY_VERIFIED"}:
            raise HandoffError("แนวเขตยังเป็น DRAFT/NEEDS_FIELD_CHECK จึงยังส่งเข้า optimizer ไม่ได้")
        if boundary_status == "SURVEY_VERIFIED":
            survey = app_doc.get("surveyReference")
            if not isinstance(survey, dict) or not isinstance(survey.get("comparison"), dict) or survey["comparison"].get("passed") is not True:
                raise HandoffError("สถานะ SURVEY_VERIFIED ต้องมี surveyReference.comparison.passed=true")
            if survey.get("crs") != working_crs:
                raise HandoffError("CRS ของข้อมูลสำรวจกับ working CRS ไม่ตรงกัน")
            if survey.get("geometry") is not None:
                _validate_polygonal_geojson(survey.get("geometry"), "surveyReference.geometry")
            else:
                _points(survey.get("vertices"), "surveyReference.vertices")
            if not isinstance(survey.get("metadata"), dict):
                raise HandoffError("SURVEY_VERIFIED ต้องมี surveyReference.metadata")
        elif mode == "field_candidate":
            raise HandoffError("field_candidate ต้องมีสถานะ SURVEY_VERIFIED; USER_CONFIRMED ใช้ได้เฉพาะ exploratory")

    source_geometry = boundary.get("sourceGeometry")
    working_geometry = boundary.get("workingGeometry")
    if source_geometry is not None or working_geometry is not None:
        if source_geometry is None or working_geometry is None:
            raise HandoffError("ต้องส่งทั้ง sourceGeometry และ workingGeometry")
        source_geometry, source_vertex_count = _validate_polygonal_geojson(source_geometry, "boundary.sourceGeometry")
        working_geometry, working_vertex_count = _validate_polygonal_geojson(working_geometry, "boundary.workingGeometry")
        if source_geometry["type"] != working_geometry["type"]:
            raise HandoffError("ชนิด sourceGeometry และ workingGeometry ต้องตรงกันใน adapter รุ่นนี้")
        source_points = None
        vertices = None
    else:
        source_vertices = boundary.get("sourceVertices")
        working_vertices = boundary.get("workingVertices")
        if not isinstance(source_vertices, list) or not isinstance(working_vertices, list):
            raise HandoffError("sourceVertices และ workingVertices ต้องเป็นรายการพิกัด หรือใช้ sourceGeometry/workingGeometry")
        if len(source_vertices) != len(working_vertices):
            raise HandoffError("จำนวน sourceVertices และ workingVertices ไม่ตรงกัน")
        source_points = _points(source_vertices, "boundary.sourceVertices")
        vertices = _points(working_vertices, "boundary.workingVertices")
        source_vertex_count = len(source_points)
        working_vertex_count = len(vertices)

    site = profile.get("site")
    if not isinstance(site, dict) or not str(site.get("site_id", "")).strip():
        raise HandoffError("ต้องระบุ site.site_id")
    site_id = str(site["site_id"]).strip()

    settings_in = profile.get("settings")
    if not isinstance(settings_in, dict):
        raise HandoffError("ต้องระบุ settings จากผู้รับผิดชอบพื้นที่/ผู้เชี่ยวชาญอย่างชัดเจน")
    required_settings = ("boundary_setback_m", "obstacle_buffer_m", "quad_segs", "geometry_tolerance_m")
    for key in required_settings:
        if key not in settings_in:
            raise HandoffError(f"settings.{key} ห้ามปล่อยว่างหรือใช้ค่า default โดยไม่ระบุที่มา")
    setback = _finite_number(settings_in["boundary_setback_m"], "boundary_setback_m", minimum=0)
    obstacle_buffer = _finite_number(settings_in["obstacle_buffer_m"], "obstacle_buffer_m", minimum=0)
    quad_segs_num = _finite_number(settings_in["quad_segs"], "quad_segs", minimum=8)
    if int(quad_segs_num) != quad_segs_num:
        raise HandoffError("quad_segs ต้องเป็นจำนวนเต็ม")
    tolerance = _finite_number(settings_in["geometry_tolerance_m"], "geometry_tolerance_m", minimum=1e-15)

    obstacle_list = profile.get("obstacles")
    if not isinstance(obstacle_list, list):
        raise HandoffError("ต้องระบุ obstacles เป็นรายการ แม้ไม่มีสิ่งกีดขวางให้ใช้ []")
    obstacles = []
    for i, obstacle in enumerate(obstacle_list, start=1):
        if not isinstance(obstacle, dict):
            raise HandoffError(f"obstacles[{i}] ต้องเป็น object")
        name = str(obstacle.get("name", f"obstacle-{i}"))
        if obstacle.get("geometry") is not None:
            geom, _ = _validate_polygonal_geojson(obstacle.get("geometry"), f"obstacles[{i}].geometry")
            obstacles.append({"name": name, "geometry": geom})
        elif obstacle.get("type") in {"Polygon", "MultiPolygon"}:
            geom, _ = _validate_polygonal_geojson({"type":obstacle.get("type"), "coordinates":obstacle.get("coordinates")}, f"obstacles[{i}]")
            obstacles.append({"name": name, "geometry": geom})
        else:
            obstacles.append({"name": name, "vertices": _points(obstacle.get("vertices"), f"obstacles[{i}].vertices")})

    crop = profile.get("crop")
    if not isinstance(crop, dict):
        raise HandoffError("ต้องระบุ crop profile; ห้ามใช้ค่าเริ่มต้นใน optimizer แทนข้อมูลพืชจริง")
    crop_name = str(crop.get("crop_name", "")).strip()
    crop_id = str(crop.get("profile_id", "")).strip()
    if not crop_name or not crop_id:
        raise HandoffError("ต้องระบุ crop_name และ profile_id")
    row_spacing = _finite_number(crop.get("row_spacing_m"), "crop.row_spacing_m", minimum=1e-12)
    in_row_spacing = _finite_number(crop.get("in_row_spacing_m"), "crop.in_row_spacing_m", minimum=1e-12)
    plants_per_hole_n = _finite_number(crop.get("plants_per_hole_after_thinning"), "crop.plants_per_hole_after_thinning", minimum=1)
    if int(plants_per_hole_n) != plants_per_hole_n:
        raise HandoffError("plants_per_hole_after_thinning ต้องเป็นจำนวนเต็ม")

    uncertainty = profile.get("uncertainty", {"status": "NOT_CALIBRATED"})
    if not isinstance(uncertainty, dict):
        raise HandoffError("uncertainty ต้องเป็น object และต้องระบุสถานะ")

    warnings: list[str] = []
    if mode == "demo":
        gate_status = "DEMO_ONLY"
        warnings.extend(["พิกัด LOCAL:METRE เป็นพิกัดสังเคราะห์ ไม่ใช่ตำแหน่งจริง", "ห้ามใช้ผลลัพธ์เป็นคำแนะนำหรือแผนลงปลูก"])
    elif boundary_status == "USER_CONFIRMED":
        gate_status = "EXPLORATORY_ONLY"
        warnings.extend(["USER_CONFIRMED เป็นการยืนยันของผู้ใช้ ไม่เท่ากับการสำรวจอิสระหรือการรับรองโดยผู้เชี่ยวชาญ", "ผลลัพธ์ใช้ทดสอบกระบวนการได้ แต่ห้ามอ้างว่าเป็นแผนภาคสนามที่ผ่านการตรวจรับ"])
    else:
        gate_status = "SURVEY_VERIFIED_EXPERT_REVIEW_PENDING"
        warnings.append("สถานะแอป SURVEY_VERIFIED ไม่ได้แทนการอนุมัติ Crop Profile, clearance และ uncertainty model")

    if mode == "field_candidate":
        needed = ("boundary", "obstacles", "settings", "crop", "uncertainty")
        missing = [key for key in needed if not _review_ok(profile, key)]
        if missing:
            raise HandoffError("field_candidate ยังไม่ผ่าน review: " + ", ".join(missing))
        if uncertainty.get("status") != "APPROVED":
            raise HandoffError("field_candidate ต้องมี uncertainty.status=APPROVED; review flag อย่างเดียวไม่เพียงพอ")
        sources = profile.get("sources", {})
        source_keys = ("boundary", "obstacles", "settings", "crop")
        source_missing = [key for key in source_keys if not isinstance(sources.get(key), str) or not sources.get(key).strip()]
        if source_missing:
            raise HandoffError("field_candidate ต้องระบุ sources: " + ", ".join(source_missing))
        gate_status = "INPUT_GATE_PASSED_NOT_FIELD_VALIDATED"
        warnings.extend(["ผ่านเฉพาะประตูข้อมูลก่อนคำนวณ ไม่ใช่การอนุญาตให้ลงปลูก", "ยังต้องผ่าน E12/E13 และการทบทวนภาคสนาม/การใช้งานแยกต่างหาก"])

    # Do not absorb positional uncertainty into setbacks automatically. Store it
    # in the audit record and require an expert-approved model before field mode.
    if mode != "field_candidate" and uncertainty.get("status") != "APPROVED":
        warnings.append("ความไม่แน่นอนด้านตำแหน่งยังไม่ได้รับอนุมัติ/สอบเทียบ และไม่ถูกนำไปรวมกับ setback อัตโนมัติ")

    case = {
        "project": "PROUVÉ Spatial",
        "version": "handoff-v0.1",
        "use_case": site_id,
        "coordinate_system": f"Local planar XY; metres; source working CRS={working_crs}",
        "crs": working_crs,
        "field": ({"geometry": working_geometry} if working_geometry is not None else {"vertices": vertices}),
        "obstacles": obstacles,
        "settings": {
            "boundary_setback_m": setback,
            "obstacle_buffer_m": obstacle_buffer,
            "quad_segs": int(quad_segs_num),
            "geometry_tolerance_m": tolerance,
        },
        "crop": {
            "profile_id": crop_id,
            "crop_name": crop_name,
            "row_spacing_m": row_spacing,
            "in_row_spacing_m": in_row_spacing,
            "plants_per_hole_after_thinning": int(plants_per_hole_n),
        },
        "handoff_metadata": {
            "source_app_schema": app_doc["schema"],
            "boundary_status": boundary_status,
            "boundary_id": app_doc.get("project", {}).get("id"),
            "boundary_name": app_doc.get("project", {}).get("name"),
            "source_input_crs": input_crs,
            "working_crs": working_crs,
            "site_profile_id": profile.get("profile_id"),
            "mode": mode,
            "source_boundary_geometry": source_geometry if source_geometry is not None else None,
        },
    }
    audit = {
        "adapter": "PROUVE Spatial Handoff Adapter V0.3.1",
        "gate_status": gate_status,
        "eligible_for_engine_run": True,
        "field_deployment_authorized": False,
        "mode": mode,
        "site_id": site_id,
        "boundary_status": boundary_status,
        "working_crs": working_crs,
        "source_vertex_count": source_vertex_count,
        "vertex_count": working_vertex_count,
        "obstacle_count": len(obstacles),
        "crop_profile_id": crop_id,
        "input_hashes": {"app_project_sha256": _sha256(app_doc), "site_profile_sha256": _sha256(profile)},
        "engine_case_sha256": _sha256(case),
        "uncertainty": uncertainty,
        "warnings": warnings,
        "notices": [
            "adapter นี้จัดรูปแบบและตรวจประตูข้อมูลเท่านั้น; ไม่ได้เรียก Geometry Engine หรือ Optimization Engine",
            "Geometry Engine V0.3 ตรวจ topology ของ Polygon/MultiPolygon และ holes ซ้ำ; lightweight adapter check ไม่ใช่ topology certificate",
            "Optimization Engine V0.4 มีประเด็น upper-bound/status ที่ต้องแก้และทดสอบก่อนใช้ผล optimum",
            "Independent verifier ต้องปฏิเสธแผนว่าง และต้องแยก implementation/library ตามแผนทดสอบ",
            "ค่า uncertainty แยกจาก clearance; ห้ามบวก/รวมอัตโนมัติโดยไม่มีแบบจำลองที่ผู้เชี่ยวชาญอนุมัติ",
        ],
    }
    return case, audit


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare a guarded PROUVE Spatial engine handoff")
    parser.add_argument("app_project", type=Path)
    parser.add_argument("site_profile", type=Path)
    parser.add_argument("--mode", choices=("demo", "exploratory", "field_candidate"), default="exploratory")
    parser.add_argument("--out-dir", type=Path, default=Path("handoff_output"))
    args = parser.parse_args()
    app_doc = json.loads(args.app_project.read_text(encoding="utf-8"))
    profile = json.loads(args.site_profile.read_text(encoding="utf-8"))
    case, audit = adapt_project(app_doc, profile, mode=args.mode)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / "engine_case.json").write_text(json.dumps(case, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
    (args.out_dir / "handoff_audit.json").write_text(json.dumps(audit, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
    print(json.dumps({"gate_status": audit["gate_status"], "eligible_for_engine_run": audit["eligible_for_engine_run"],
                      "field_deployment_authorized": audit["field_deployment_authorized"], "warnings": audit["warnings"]},
                     ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
