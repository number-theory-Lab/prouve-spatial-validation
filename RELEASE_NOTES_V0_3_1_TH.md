# PROUVÉ Spatial — Release Notes V0.3.1

**รุ่น:** Engine Branch V0.3.1  
**วันที่:** 25 พฤศจิกายน 2569  
**ประเภท:** Internal hardening release — ไม่ใช่ public production release

## จุดประสงค์ของรุ่น

ยกระดับความเข้มงวดของการตรวจ candidate, lattice metadata, geometry input และการจัดการกรณีไม่มีแผนที่เป็นไปได้ พร้อมปิดช่องว่างการทดสอบ Certified Upper Bound ของ implementation V0.3.1 โดยตรง

## การเปลี่ยนแปลง

- เพิ่ม strict 2D coordinate validation: ปฏิเสธ coordinate dimension ที่ไม่ใช่ XY, boolean และค่าที่ไม่ finite
- เพิ่ม strict integer validation สำหรับ lattice indices และ `plants_per_hole`
- ตรวจ consistency ของ rational rotation, orthogonal basis, basis lengths และ phase
- ไม่อนุญาต lattice certificate สำหรับ candidate set ว่าง
- เพิ่ม validation ของ input GeoJSON ใน Geometry Engine
- เพิ่ม safe HOLD branch เมื่อ usable geometry ว่าง หรือ finite search ไม่พบ candidate
- แยก `HOLD_EMPTY_USABLE_GEOMETRY` จาก `HOLD_NO_CANDIDATE_FOUND_WITHIN_SEARCH`
- เพิ่ม Upper Bound V0.3.1 test module โดยตรง รวมการสุ่ม 350 trials ต่อ lattice family สำหรับ rectangular 90° และ triangular 60°

## ผลตรวจสอบ

- Automated tests: **113/113 PASS**
- Python `compileall`: PASS
- Rectangular synthetic fixture: Best Found 70, Certified UB 77, gap 9.09%, optimality not proven
- MultiPolygon-with-holes synthetic fixture: Best Found 153, Certified UB 209, gap 26.79%, optimality not proven
- Empty usable area fixture: HOLD; no planting plan and no optimality claim

## ข้อจำกัด

- ยังไม่มี independent external review
- ยังไม่มี FTS-01 survey data, CRS verification, uncertainty calibration หรือ agronomic sign-off
- GEOS/Shapely buffer/overlay เป็น polygonal approximation
- Adaptive BnB/Arrangement ยังเป็น experimental search methods
- ยังไม่ merge กับ published app V0.5.2 และไม่อนุญาต field deployment

## ไฟล์หลักที่เพิ่ม/ปรับปรุง

- `engine/formal_feasibility_certificate.py`
- `engine/lattice_relation_certificate.py`
- `engine/geometry_engine_v03.py`
- `engine/certified_upper_bound_v03.py`
- `engine/adaptive_solver.py`
- `engine/pipeline_runner_v03.py`
- `adapter/handoff_adapter_v03.py`
- `tests/test_adversarial_hardening_v031.py`
- `tests/test_certified_upper_bound_v031.py`
- `fixtures/empty_geometry_app_project.json`
- `fixtures/empty_geometry_site_profile.json`

## Release decision

**Internal engineering gate: PASS WITH LIMITATIONS.**  
**Field deployment gate: BLOCKED.**
