# PROUVÉ Spatial — Engine Branch V0.3

> **หมายเหตุสถานะ:** ไฟล์นี้เป็นรายงานฐานของ V0.3 ก่อน hardening. สำหรับสถานะล่าสุด ผลทดสอบรอบสุดท้าย และข้อจำกัดที่ผ่านการตรวจเพิ่มเติม ให้ใช้ `AUDIT_REPORT_V0_3_1_TH.md`, `RELEASE_NOTES_V0_3_1_TH.md` และ `NEXT_GATE_STATUS_V0_3_1_TH.md` ซึ่ง supersede ข้อสรุปเชิงสถานะของเอกสารนี้

**วันที่:** 25 พฤศจิกายน 2569  
**สถานะ:** Research / Development Candidate — ยังไม่ใช่ Release และยังไม่อนุญาตใช้ภาคสนาม  
**ความสัมพันธ์กับรุ่นก่อน:** พัฒนาต่อจาก V0.2 โดยเก็บ `baseline/` และ provenance เดิมไว้ ไม่เขียนทับ source หรือเว็บไซต์ V0.5.2

## 1. สรุปผล

V0.3 มุ่งปิดช่องว่างสามเรื่องตามแผน: (1) Formal Feasibility Certificate, (2) Adaptive Solver Architecture และ (3) App Result & Evidence Interface

ผลที่ตรวจสอบได้ในรอบนี้:

- ชุดทดสอบรวม **93/93 PASS** หลังการแก้ไขล่าสุด
- Formal Feasibility Certificate ใช้ `Fraction` ตรวจ point-in-polygon, boundary/hole, obstacle clearance และ squared distances โดยไม่มี epsilon ในการตัดสิน pass/fail
- รองรับ GeoJSON `Polygon` ที่มี holes และ `MultiPolygon` ที่ components ไม่แตะ/ทับกัน
- Geometry Engine V0.3 รับ Polygon/MultiPolygon และ obstacles แบบ GeoJSON; การ buffer/difference ยังคำนวณผ่าน Shapely/GEOS
- Adaptive Solver ใช้ Grid เป็น incumbent/fallback เสมอ และทดลอง Phase Arrangement กับ orientation/phase BnB เมื่อผ่าน complexity/time gates
- Candidate ที่มาจากวิธีทดลองถูกสร้างกลับด้วย production enumerator; count mismatch ทำให้ candidate นั้นไม่ถูกเลือก
- Candidate ที่เลือกถูกแปลงเป็น rational orthogonal lattice และตรวจ source geometry กับ represented usable geometry แยกกัน
- App Result & Evidence Viewer เป็นไฟล์ HTML offline prototype อ่าน Evidence JSON/CSV/GeoJSON ได้ แต่ยังไม่ merge เข้าเว็บไซต์ V0.5.2

## 2. ผล pipeline ตัวอย่าง

### Fixture A — Synthetic rectangular field

| รายการ | ผล |
|---|---:|
| พื้นที่แปลง | 400 m² |
| พื้นที่ usable ที่แทนใน geometry | 324 m² |
| Best found | 70 จุด |
| Certified upper bound | 77 จุด |
| Gap | 9.09% |
| วิธีที่เลือก | GRID |
| Rational lattice relation | PASS |
| Source feasibility | 70/70 PASS |
| Represented usable feasibility | 70/70 PASS |
| Optimality | `FEASIBLE_CERTIFIED_BEST_FOUND_NOT_PROVEN_OPTIMAL` |

### Fixture B — MultiPolygon with hole and obstacle

| รายการ | ผล |
|---|---:|
| พื้นที่แปลงรวม | 3,100 m² |
| พื้นที่ usable ที่แทนใน geometry | ประมาณ 2,709.689 m² |
| Best found | 150 จุด |
| Certified upper bound | 209 จุด |
| Gap | 28.23% |
| วิธีที่เลือก | GRID (วิธีทดลองถูก skip ตาม complexity/budget) |
| Rational lattice relation | PASS |
| Source feasibility | 150/150 PASS |
| Represented usable feasibility | 150/150 PASS |
| Optimality | `FEASIBLE_CERTIFIED_BEST_FOUND_NOT_PROVEN_OPTIMAL` |

เวลา search อยู่ในงบที่กำหนด แต่เวลารวมของ Fixture B ประมาณ 3.55 วินาที สูงกว่า search budget 3 วินาที เนื่องจาก exact certificates และ upper-bound calculation เป็นขั้นตอนบังคับที่รันจนจบและไม่ถูกยกเลิกกลางคำสั่ง รายงานแยก `search_elapsed_seconds` กับ `total_elapsed_seconds` ไว้ชัดเจน จึงไม่อ้างว่าเป็น hard wall-clock deadline

## 3. Formal Feasibility Certificate

โมดูล `engine/formal_feasibility_certificate.py` ตรวจชุด candidate points เทียบกับ canonical decimal geometry ที่ส่งเข้ามา:

- Point-in-ring ด้วย exact rational ray crossing
- Polygon shell / holes และ MultiPolygon components
- ตรวจ self-intersection, ring touching/overlap และ topology กำกวม
- ระยะจาก point ถึง segment เปรียบเทียบ squared distance กับ squared clearance โดยไม่ต้องใช้ square root
- ตรวจ boundary setback, obstacle exclusion/clearance และ optional pairwise spacing
- บันทึก hashes ของ geometry/candidate set ที่ตรวจ

**ความหมายของคำว่า exact:** เป็น exact เมื่อเทียบกับ canonical decimal representation ของข้อมูลที่ serialize มา เช่น float `0.1` ถูกตีความเป็น rational `1/10` ไม่ใช่การรับรองว่าการสำรวจพื้นดินไม่มี measurement error และไม่ใช่การรับรอง CRS/datum

Lattice relation certificate แยกต่างหากตรวจ rational rotation, orthogonal basis, basis lengths, unique integer indices และ lower bound ของ pairwise spacing

## 4. Certified Upper Bound

`engine/certified_upper_bound_v03.py` ใช้ rational Steiner enclosure สำหรับ declared rectangular 90-degree lattice family บน decimalized represented usable polygon โดยมี proof note แยกไว้

ขอบเขตนี้ใช้กับ lattice family และ geometry representation ที่ระบุ ไม่ใช่ upper bound สำหรับ arbitrary free-point placement, ไม่รับรองความจริงของ boundary survey และไม่รับรอง agronomic feasibility

ใน pipeline ตัวอย่าง Best Found ยังต่ำกว่า Upper Bound ทั้งสองกรณี จึงรายงาน gap และไม่ประกาศ optimum

## 5. Adaptive Solver

- **Grid:** deterministic finite search; เป็น baseline/incumbent และ fallback
- **Phase Arrangement:** fixed-orientation experimental refinement; ใช้ complexity/time caps และ re-evaluate ด้วย production enumerator
- **Orientation–Phase BnB:** experimental; ใช้ node/time/index caps และ re-evaluate ด้วย production enumerator
- **Selection:** เลือกเฉพาะ candidate ที่สร้างกลับแล้ว count ตรง และผ่าน rational lattice + feasibility certificates
- **Fallback:** error, timeout, cap หรือ mismatch ไม่ทำให้ candidate ทดลองถูกยอมรับ; คง grid incumbent หรือ HOLD

Complexity features ใช้เพื่อ scheduling ไม่ใช่ทฤษฎีวัดความยาก งาน Geometry/GEOS บางคำสั่งหยุดกลาง operation ไม่ได้ จึงเป็น best-effort search budget ไม่ใช่ hard real-time guarantee

## 6. App Result & Evidence Interface

`app/app_result_evidence_viewer_v0_3.html` เป็น standalone HTML prototype แบบ offline ไม่มี CDN และไม่รัน solver ใน browser ผู้ใช้สามารถเปิด Evidence JSON, planting CSV และ geometry GeoJSON เพื่อดู:

- แผนที่ขอบเขตและตำแหน่งปลูก
- Best-found count, certified upper bound และ gap
- วิธีที่เลือกและวิธีที่ทดลอง
- Rational lattice / source geometry / usable geometry certificates
- Runtime budget, source hashes, input hashes และ notices

ไฟล์นี้ยังไม่ merge เข้าเว็บไซต์ V0.5.2, ยังไม่ผ่าน device/browser/accessibility acceptance และไม่ใช่ app release

## 7. การทดสอบ

รัน full suite หลังการแก้ไขล่าสุด:

```bash
PYTHONPATH=engine:adapter:prototype:tests:. python -m unittest \
  tests.test_engine_branch tests.test_certified_upper_bound tests.test_geometry_stress \
  tests.test_scanline_candidate_enumeration prototype.test_engine_safety_and_reference \
  prototype.test_exact_phase_arrangement prototype.test_continuous_lattice_bnb \
  adapter.test_handoff_adapter tests.test_formal_feasibility_certificate \
  tests.test_geometry_engine_v03_topology tests.test_adaptive_solver \
  tests.test_handoff_adapter_v03_geojson tests.test_pipeline_runner_v03 -v
```

ผลล่าสุด: **93 tests, 6.579 seconds, OK** ใน environment ที่บันทึกไว้ใน report

การตรวจ JavaScript syntax ของ HTML viewer ทำด้วย `node --check` หลังการแก้ล่าสุด; ยังไม่ใช่ browser/device acceptance test

## 8. ข้อจำกัดและข้อห้ามในการกล่าวอ้าง

1. Exact feasibility หมายถึง exact ต่อ canonical decimal representation ของ geometry/points ที่ส่งเข้าตรวจ ไม่ใช่ survey truth
2. Geometry Engine สร้าง setback/buffer/difference ผ่าน GEOS floating geometry; candidate ถูกตรวจ exact ต่อ decimalized result ที่ serialize ออกมา
3. Certified upper bound ครอบคลุม declared rectangular lattice family บน represented usable geometry เท่านั้น; best-found ยังไม่เท่ากับ bound ใน fixture จึงยังไม่พิสูจน์ optimum
4. MultiPolygon components ที่แตะ/ทับกันถูกปฏิเสธ; รูป topology กำกวมต้องแก้ข้อมูลก่อน
5. Phase Arrangement ใช้ floating topology และ fixed orientation; BnB ยังเป็น numerical research prototype ไม่ใช่ formal continuous optimizer
6. Search budget แยกจากเวลารวม certificate; บาง geometry operation ไม่สามารถ cancel ได้กลางคำสั่ง
7. No CRS/datum/survey accuracy certificate, no GNSS calibration, no independent checkpoints, no agronomist approval, no farmer usability study
8. ยังไม่มีข้อมูลจริงของ FTS-01; fixtures ทั้งสองเป็น synthetic
9. App Viewer เป็น offline prototype เท่านั้น; ไม่มีการแก้ GitHub หรือ website V0.5.2
10. ห้ามใช้ synthetic crop spacing เป็นคำแนะนำการปลูกจริง

## 9. การตัดสินใจ

V0.3 ทำให้ pipeline มี candidate feasibility certificate เชิง rational สำหรับ geometry ที่ serialize และมี solver scheduling ที่มี fallback แต่ยังไม่ใช่ระบบภาคสนามหรือ continuous optimizer ที่ผ่านการพิสูจน์ครบถ้วน

คง V0.2 เป็น baseline, V0.3 เป็น development candidate และยังไม่ merge เข้า V0.5.2 จนกว่าจะผ่าน independent mathematical/code review, field calibration, crop-profile approval และ app acceptance tests
