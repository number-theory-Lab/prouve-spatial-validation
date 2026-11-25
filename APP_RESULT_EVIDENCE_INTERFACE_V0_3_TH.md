# PROUVÉ Spatial — App Result & Evidence Interface V0.3

**สถานะ:** Standalone UI prototype / integration contract เท่านั้น — ยังไม่ merge เข้าเว็บ V0.5.2 และไม่ใช่ app release

## 1. หน้าที่ของหน้าผลลัพธ์

หน้าจอนี้มีหน้าที่นำเสนอผลจาก Engine V0.3 โดยแยกความหมายต่อไปนี้:

1. Best-found count: จำนวนจุดจากแผนที่ค้นพบภายใต้วิธีและงบการคำนวณที่ระบุ
2. Certified upper bound: ขอบเขตบนของ lattice family ที่ระบุ บน decimalized represented usable geometry
3. Feasibility certificates: การตรวจความสัมพันธ์กับ rational lattice, ข้อจำกัดจาก geometry ต้นทาง และการอยู่ใน represented usable geometry
4. Optimality status: แสดงตามหลักฐานจริง ห้ามเปลี่ยนสถานะ best-found ให้เป็น optimum โดยอัตโนมัติ
5. Field deployment gate: ใน demo นี้ต้องคง `field_deployment_authorized=false`

## 2. ไฟล์ต้นแบบ

`app/app_result_evidence_viewer_v0_3.html` เป็นหน้าเว็บแบบไฟล์เดียว ใช้งาน offline ได้ ไม่มี CDN หรือ external dependencies ผู้ใช้สามารถเปิด HTML ใน browser และเลือก Evidence JSON / Planting CSV / GeoJSON เพื่อดู run อื่นได้

หน้าเว็บนี้เป็นการแสดงผล ไม่ได้รัน Geometry Engine หรือ Optimizer ใน browser และยังไม่ได้เชื่อมกับ published V0.5.2

## 3. Input contract

### Evidence JSON

ฟิลด์หลัก:

- `schema`: `prouve-app-evidence-v0.3`
- `run_id`, `engine_branch`, `pipeline_status`
- `field_deployment_authorized`
- `geometry.source_field_geometry`
- `geometry.source_obstacle_geometries`
- `geometry.represented_usable_geometry`
- `optimization.best_found_count`
- `optimization.upper_bound_count`, `upper_bound_certified`, `upper_bound_status`
- `optimization.relative_gap_to_certified_upper_bound`
- `optimization.selected_method`, `method_attempts`, `compute_budget`
- `verification.rational_lattice_relation`
- `verification.source_constraint_feasibility`
- `verification.represented_usable_geometry_feasibility`
- `rational_lattice`
- `source_hashes`, `input_hashes`, `notices`

### Planting positions CSV

- `plant_id`, `lattice_i`, `lattice_j`
- `x_m_display`, `y_m_display`: presentation coordinates only; decimal floating values
- `x_m_exact_fraction`, `y_m_exact_fraction`: exact rational coordinates used by certificates
- `plants_in_hole`

ห้ามใช้ `x_m_display` แทน exact fractions ในการตรวจรับรองซ้ำ หาก export หรือ re-round ตำแหน่งสำหรับงานภาคสนาม ต้องสร้าง certificate ใหม่กับค่าที่จะนำไปใช้จริง

### Geometry GeoJSON

รับ `Polygon` หรือ `MultiPolygon` รวม interior rings (holes) ใน local metric XY; ต้องมี CRS/provenance ประกอบใน evidence package แยกต่างหาก

## 4. UI state mapping

| Engine state | Presentation |
|---|---|
| `SYNTHETIC_PIPELINE_PASS_FEASIBILITY_CERTIFIED_EXPLORATORY_ONLY` | ผ่าน feasibility ในข้อมูลทดลอง — ไม่อนุญาตใช้ภาคสนาม |
| `FEASIBLE_CERTIFIED_BEST_FOUND_NOT_PROVEN_OPTIMAL` | แผนผ่าน feasibility certificate แต่ยังไม่พิสูจน์ optimality |
| `OPTIMAL_WITHIN_DECLARED_RECTANGULAR_LATTICE_FAMILY_FOR_REPRESENTED_USABLE_GEOMETRY` | optimum ภายใน lattice family และ represented usable geometry ตาม certificate ที่แนบ |
| `HOLD_FORMAL_FEASIBILITY_CERTIFICATE_FAILED` | HOLD — feasibility ไม่ผ่าน |
| `HOLD_CERTIFIED_UPPER_BOUND_CONFLICT` | HOLD — best-found เกิน certified upper bound ต้องตรวจสอบซ้ำ |
| `HOLD_GEOMETRY_CHECK_FAILED` | HOLD — geometry check ไม่ผ่าน |

## 5. ข้อห้าม

- ห้ามแสดงว่าแผนผ่านการสำรวจหรือได้รับอนุญาตลงพื้นที่เพียงเพราะ exact-rational geometry certificate ผ่าน
- ห้ามซ่อนขอบเขตของ certificate, run ID, input hashes หรือ source hashes
- ห้ามแสดง rational fractions เป็นพิกัด GPS; coordinates เป็น local XY เมตร
- ห้ามใช้ synthetic crop profile เป็นคำแนะนำทางการเกษตร
- ห้าม merge เข้าสู่เว็บ V0.5.2 จนกว่าจะผ่าน app-side schema validation, device/browser tests, accessibility review และ field deployment gates
