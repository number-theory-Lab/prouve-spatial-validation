# PROUVÉ Spatial — Engine Branch V0.3.1

**วันที่:** 25 พฤศจิกายน 2569  
**ประเภท:** Internal Engineering Hardening Release  
**สถานะ:** ผ่านการตรวจภายใน 113/113 tests; ยังไม่อนุญาตใช้งานภาคสนาม

## อ่านเอกสารตามลำดับ

1. `AUDIT_REPORT_V0_3_1_TH.md` — รายงานตรวจสอบฉบับหลัก: ขอบเขตการรับรอง, ผลทดสอบ, หลักฐานคณิตศาสตร์, limitations และ Engineering Gates
2. `RELEASE_NOTES_V0_3_1_TH.md` — สิ่งที่แก้ไข/เพิ่มในรุ่น V0.3.1
3. `NEXT_GATE_STATUS_V0_3_1_TH.md` — งานที่ยังต้องทำและสิ่งที่ต้องใช้จากผู้ใช้/ผู้เชี่ยวชาญ
4. `reports/all_tests_v0_3_1.log` — log ชุดทดสอบรอบสุดท้าย
5. `reports/v031_rectangular_release/evidence_report.json` — หลักฐาน pipeline สังเคราะห์กรณีสี่เหลี่ยม
6. `reports/v031_multipolygon_release/evidence_report.json` — หลักฐาน pipeline สังเคราะห์กรณี MultiPolygon มีรูและ obstacle
7. `reports/v031_empty_release/evidence_report.json` — หลักฐานกรณีพื้นที่ใช้ได้ว่างที่ระบบ HOLD อย่างปลอดภัย

เอกสาร V0.3 เดิม เช่น `BRANCH_REPORT_TH.md`, `CERTIFIED_UPPER_BOUND_PROOF_TH.md` และรายงานที่ลงวันที่/ติดป้าย V0.3 เป็นเอกสารฐานหรือประวัติการพัฒนา ให้ใช้รายงาน V0.3.1 ข้างต้นเป็นสถานะล่าสุด

## สิ่งที่ branch นี้ทำ

- Geometry preprocessing สำหรับ Polygon/MultiPolygon และ holes โดย Shapely/GEOS
- Formal feasibility verification สำหรับ candidate set ใน 2D decimal geometry ด้วย rational arithmetic
- Rational rectangular-lattice relation certificate
- Rational Steiner-enclosure upper bound สำหรับ lattice family มุมฐาน 90° และ 60°
- Adaptive search ที่มี Grid fallback และใช้ exact checks ก่อนแสดงผลรับรอง
- Evidence JSON pipeline และ offline viewer prototype

## ข้อจำกัดสำคัญ

- ตัวเลขและ fixtures ที่ทดสอบเป็น synthetic; ยังไม่มี FTS-01 field data
- certificate exact ต่อข้อมูล geometry ที่ serialize เท่านั้น ไม่รับรอง CRS, survey accuracy หรือโลกจริง
- Shapely/GEOS buffer/overlay เป็น polygonal approximation
- Best Found ไม่เท่ากับ proven optimum ใน pipeline fixtures
- Crop Profile ยังไม่ได้รับรองโดยผู้เชี่ยวชาญเกษตร
- ยังไม่มี independent external review และยังไม่ merge เข้ากับแอป V0.5.2

## Environment

ทดสอบใน Python 3.13.5, NumPy 2.3.5 และ Shapely 2.1.2; dependencies ระบุใน `requirements.txt`

รัน test suite จาก root ของ package:

```bash
export PYTHONPATH="$PWD/engine:$PWD/adapter:$PWD/prototype:$PWD/tests:$PWD"
python -m unittest \
  tests.test_adversarial_hardening_v031 \
  tests.test_certified_upper_bound_v031 \
  tests.test_formal_feasibility_certificate \
  tests.test_geometry_engine_v03_topology \
  tests.test_adaptive_solver \
  tests.test_pipeline_runner_v03 \
  tests.test_handoff_adapter_v03_geojson \
  tests.test_certified_upper_bound \
  tests.test_engine_branch \
  tests.test_geometry_stress \
  tests.test_scanline_candidate_enumeration \
  prototype.test_continuous_lattice_bnb \
  prototype.test_exact_phase_arrangement \
  prototype.test_engine_safety_and_reference \
  adapter.test_handoff_adapter -v
```

**คำตัดสิน:** internal engineering milestone ผ่านพร้อมข้อจำกัด; field deployment ยังคง BLOCKED
