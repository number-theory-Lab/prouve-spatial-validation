# PROUVÉ Spatial — App Integration Contract V0.1 (สำหรับ Engine Branch V0.2)

**สถานะ:** Design / Contract Draft เท่านั้น — ยังไม่ merge เข้าสู่เว็บแอป V0.5.2 และยังไม่กำหนด app release version

## 1. จุดประสงค์

กำหนดรูปแบบข้อมูลที่แอปควรใช้แสดงผลจาก Engine Pipeline โดยแยกให้ชัดระหว่าง:

1. จำนวนตำแหน่งที่ค้นพบใน search space ที่ประกาศไว้
2. certified upper bound ของ lattice family
3. สถานะการตรวจสอบ feasibility
4. สถานะการอนุญาตใช้ข้อมูลภาคสนาม

แอปต้องไม่เปลี่ยน `BEST_FOUND_NOT_PROVEN_OPTIMAL` เป็นคำว่า “เหมาะสมที่สุด” หรือ “optimal” เพียงเพราะมีจำนวนจุดสูงที่สุดในกริดที่ทดลอง

## 2. Contract fields

อ้างอิง `reports/final_pipeline_output/evidence_report.json` เป็นตัวอย่างจริงจาก synthetic fixture:

- `engine_branch`, `run_id`, `pipeline_status`
- `field_deployment_authorized`
- `geometry.areas_m2`, `geometry.geometry_status`, `geometry.geometry_checks`
- `optimization.best_found_count`
- `optimization.upper_bound_count`, `optimization.upper_bound_certified`, `optimization.upper_bound_status`, `optimization.upper_bound_method`
- `optimization.relative_gap_to_certified_upper_bound`
- `optimization.best_over_finite_declared_search_grid`, `optimization.continuous_lattice_optimum_proven`
- `optimization.evaluated_layouts`, `optimization.angle_step_deg`, `optimization.phase_divisions`, `optimization.elapsed_seconds`
- `verification.reference_no_shapely`, `verification.shapely_geos`, `verification.agreement`, `verification.both_passed`
- `source_hashes`, `input_hashes`, `notices`

ตำแหน่งปลูกจริงถูกส่งแยกใน `planting_positions.csv` โดยอ้างอิง `plant_id`, `lattice_i`, `lattice_j`, `x_m`, `y_m`, `plants_in_hole`

## 3. ข้อกำหนดด้าน UI

### A. ผลการค้นหา

หัวข้อที่แนะนำ: **“แผนที่พบจากการค้นหาภายใต้เงื่อนไขนี้”**

แสดง:
- Best-found count
- แผนที่จุดปลูกและรหัสจุด
- spacing profile ที่ใช้
- angle step, phase divisions และจำนวน layout ที่ประเมิน
- ข้อความกำกับว่าเป็น finite search result

ห้ามใช้ข้อความ “ได้คำตอบดีที่สุดทั้งหมดแล้ว” เว้นแต่ engine ส่งสถานะ formal certificate ซึ่งมีทั้ง certified upper bound และ formal feasibility certificate ที่ผ่านการตรวจสอบจริง

### B. ขอบเขตบนและช่องว่าง

เมื่อ `upper_bound_certified=true` ให้แสดง:
- Certified upper bound count
- Bound method และ scope
- Relative gap ต่อ certified upper bound
- คำอธิบายว่า upper bound ไม่ใช่จำนวนต้นที่วางได้จริง และไม่ใช่ optimum certificate โดยลำพัง

หาก certificate ไม่พร้อม/ไม่รองรับ lattice family ให้ซ่อนสถานะ certified และแสดงเป็น estimate-only พร้อม label ชัดเจน

### C. Verification

แสดงสถานะแยกสองชุด:
- Reference Verifier (no Shapely)
- Shapely/GEOS cross-check
- Agreement: `AGREE` หรือ `HOLD`

เมื่อ disagreement หรือ check fail ต้องหยุดการส่งออกแผนว่า feasible และแสดง `HOLD` ไม่ควรแสดงปุ่มยืนยันแผนปลูกจริง

### D. ความพร้อมของข้อมูลภาคสนาม

`field_deployment_authorized=false` ต้องคงการแสดงสถานะ “ข้อมูลทดลอง/ยังไม่อนุญาตใช้วางแผนภาคสนาม” แม้ pipeline ผ่านทั้งหมด

การปลดล็อกต้องอาศัย survey QA, independent checkpoints, uncertainty calibration, agronomist-approved crop profile และ field gate ที่เกี่ยวข้อง ไม่ใช่การกดปุ่มใน UI

## 4. State mapping ที่ต้องรักษา

| Engine status | UI presentation |
|---|---|
| `SYNTHETIC_PIPELINE_PASS_EXPLORATORY_ONLY` | ผ่านการคำนวณและตรวจสอบในข้อมูลทดลอง — ยังไม่อนุญาตใช้ภาคสนาม |
| `HOLD_VERIFIER_DISAGREEMENT` | หยุด: ตัวตรวจสอบให้ผลไม่ตรงกัน |
| `HOLD_FEASIBILITY_VERIFICATION_FAILED` | หยุด: แผนไม่ผ่านการตรวจสอบ feasibility |
| `HOLD_GEOMETRY_CHECK_FAILED` | หยุด: geometry/clearance ไม่ผ่าน |
| `BEST_FOUND_NOT_PROVEN_OPTIMAL` | พบแผนดีที่สุดใน finite search ที่ระบุ แต่ยังไม่พิสูจน์ continuous optimum |
| `BOUND_MATCH_NUMERIC_FEASIBILITY_ONLY` | จำนวนตรงกับ upper bound แต่ feasibility ยังเป็น numerical-only; ห้ามติดป้าย optimal |
| `OPTIMAL_WITHIN_DECLARED_LATTICE_FAMILY` | อนุญาตเฉพาะเมื่อ upper bound certified และ formal feasibility certificate ผ่านจริง พร้อมระบุ family/scope |

## 5. ข้อห้ามทางผลิตภัณฑ์

- อย่าเรียก geometry-only station counts ว่าจำนวนต้นที่ปลูกได้จริง
- อย่าผูกตำแหน่งกับ lat/long โดยตรง; Engine รับ local metric XY และต้องมี CRS/transform provenance
- อย่าใช้ crop spacing ค่า synthetic เป็นคำแนะนำเกษตร
- อย่าซ่อน input/source hashes และ run ID เมื่อส่งออก evidence report
- อย่า merge branch V0.2 เข้าสู่เว็บไซต์จนกว่า benchmark, verifier scope, precision guard และ field-data gate จะได้รับการทบทวน

## 6. ตัวอย่างผลสังเคราะห์

Run ID: `cf033ea8846a7dec`  
Best found: 63  
Certified upper bound: 77  
Relative gap: 18.18%  
Verifier agreement: `AGREE`  
Pipeline: `SYNTHETIC_PIPELINE_PASS_EXPLORATORY_ONLY`  
Field deployment authorized: `false`

นี่เป็นตัวอย่างเพื่อออกแบบ UI เท่านั้น ไม่ใช่ข้อมูลสวนหรือคำแนะนำปลูกจริง
