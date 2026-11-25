# PROUVÉ Spatial — Research Benchmark Report V0.2

**วันที่:** 25 พฤศจิกายน 2569  
**ชุดข้อมูล:** รูปแปลงสังเคราะห์ 12 กรณี  
**วัตถุประสงค์:** เปรียบเทียบ finite angle/phase grid, Orientation–Phase BnB prototype และ fixed-orientation phase-arrangement prototype  
**สถานะ:** Research benchmark เท่านั้น — ไม่ใช่ผลภาคสนามหรือการรับรอง optimum

## 1. สรุปผล

- Geometry stress: 12 กรณี — 10 กรณีคำนวณพื้นที่ใช้ได้สำเร็จ, 1 กรณีพื้นที่ใช้ได้ว่างโดยถูกต้อง, 1 กรณีถูกปฏิเสธอย่างปลอดภัยเพราะ floating-point ULP ไม่รองรับ tolerance
- Certified upper bound: สร้างได้สำหรับ geometry ที่ไม่ว่างและ lattice family ที่รองรับ (rectangular/square 90° และ triangular 60°) โดยใช้ rational outward bounds; เป็น upper bound ไม่ใช่ proof ว่า candidate ที่พบ feasible แบบ exact
- Orientation–Phase BnB: รองรับ 8 จาก 10 กรณี geometry ไม่ว่าง; อีก 2 กรณี skip อย่างปลอดภัยเพราะ candidate-index envelope เกินเพดาน 50,000
- BnB ที่ equal layout-evaluation budget: เทียบกับ grid 48 evaluations ได้ดีกว่า 4 กรณี และแย่กว่า 4 กรณี ไม่มีกรณีเสมอ; ใน 8 กรณีที่รองรับ BnB ใช้เวลา 5.6–19.6 เท่าของ median grid (median 13.1×) เพราะ node-bound work เพิ่มเติม
- Fixed-orientation phase arrangement: ทำสำเร็จ 5 กรณี และ skip 5 กรณีจากข้อจำกัด complexity; ใน 5 กรณีที่สำเร็จให้ count เท่าหรือมากกว่า near-equal grid 29×29 แต่เท่ากับ grid 40×40 ทั้ง 5 กรณี
- Candidate verification ของ BnB ที่รองรับ: ทั้ง Reference verifier และ Shapely/GEOS verifier ผ่านและยืนยัน count ตรงกันทุก output ที่ตรวจ (PASS); นี่เป็น numerical verification ไม่ใช่ formal interval feasibility certificate

## 2. Benchmark design และความเท่าเทียมของงบ

### 2.1 Orientation + phase

**Grid baseline:** 3 orientation angles × 4 phase-A values × 4 phase-B values = 48 layout evaluations (grid 60°; phase divisions 4 ในชุด benchmark นี้)

**BnB equal layout-evaluation budget:** จำกัด BnB ที่ 4 nodes และนับ incumbent layout evaluations ให้เท่ากับ 48 เช่นเดียวกับ grid ในกรณีที่รองรับ อย่างไรก็ตาม BnB ยังมีงานคำนวณ node bounds และ polygon geometry เพิ่มเติม ซึ่งสะท้อนใน elapsed time จึงเป็น equal *layout-evaluation count* ไม่ใช่ equal CPU operations

**BnB wall-clock target:** ตั้ง target จาก median ของ grid 3 runs และบันทึกเวลา BnB ที่เกิดขึ้นจริง รอบคำนวณ/geometry operation บางรายการหยุดกลางคันไม่ได้ ทำให้ actual time เกิน target ได้ 1.20–2.73× (median 1.82×) จึงไม่ใช่ strict equal-wall-clock benchmark

### 2.2 Fixed-orientation phase arrangement

เปรียบเทียบเฉพาะ orientation 0°: arrangement candidate method กับ uniform phase grid ที่มีจำนวน candidate ใกล้เคียงกัน และ grid 40×40 (1,600 phases) การเปรียบเทียบนี้ไม่ครอบคลุมการค้นหา orientation ร่วมกัน และ topology ใช้ floating-point Shapely/GEOS จึงยังไม่เรียกว่า exact geometry implementation

## 3. ผลต่อรูปแปลง

| กรณี | Geometry | Certified UB | Grid 48 | BnB 48 eval | Δ BnB−Grid | Phase arrangement |
|---|---|---:|---:|---:|---:|---:|
| `concave_L` | PASS | 215 | 135 | 136 | +1 | 135 |
| `concave_U` | PASS | 233 | 142 | 141 | -1 | 150 |
| `radial_concave_24` | PASS | 842 | 557 | 560 | +3 | — |
| `many_obstacles_25` | PASS | 1720 | 1550 | 1545 | -5 | — |
| `obstacle_dense_36` | PASS | 460 | 353 | 371 | +18 | — |
| `narrow_corridor` | PASS | 1936 | 1500 | SKIP | — | — |
| `near_degenerate_sliver` | PASS | 193428 | 166665 | SKIP | — | — |
| `near_touching_obstacles` | PASS | 176 | 150 | 148 | -2 | 150 |
| `large_projected_coords` | PASS | 1754 | 1691 | 1690 | -1 | 1691 |
| `tiny_scale` | PASS | 125 | 104 | 112 | +8 | 112 |
| `setback_erases_area` | PASS_EMPTY_USABLE_AREA | 0 | — | — | — | — |
| `very_large_offset` | SAFE_REJECT | — | — | — | — | — |

`SKIP` หมายถึง prototype ปฏิเสธการรันตาม complexity guard ไม่ใช่ผลล้มเหลวของ Geometry Engine

## 4. รายละเอียด Orientation–Phase BnB

ใน 8 กรณีที่รองรับ BnB ดีกว่า grid 4 กรณี:

- `concave_L`: 136 เทียบกับ 135 (+1)
- `radial_concave_24`: 560 เทียบกับ 557 (+3)
- `obstacle_dense_36`: 371 เทียบกับ 353 (+18)
- `tiny_scale`: 112 เทียบกับ 104 (+8)

และต่ำกว่า grid 4 กรณี:

- `concave_U`: 141 เทียบกับ 142 (−1)
- `many_obstacles_25`: 1545 เทียบกับ 1550 (−5)
- `near_touching_obstacles`: 148 เทียบกับ 150 (−2)
- `large_projected_coords`: 1690 เทียบกับ 1691 (−1)

ระหว่างการตรวจทานพบ bug ในการแปลง phase: BnB ใช้ centered local frame แต่ส่งค่ากลับเสมือนเป็น global-local-XY phase ทำให้การสร้าง layout กลับไม่ตรง หลังแก้การแปลง phase กลับสู่ global local-XY frame และเก็บ centered phase แยกไว้ ผล BnB ทั้ง 8 กรณีที่รองรับผ่านการสร้างซ้ำจาก Optimization Engine และ verifier สองชุด โดย `search_count_matches=true` ทุกกรณี

ถึงอย่างนั้น BnB ยังเป็น research prototype: node upper bounds อาศัย platform `libm` trigonometric values พร้อม `nextafter`/ULP margin ไม่ใช่ directed-rounding interval proof; BnB upper bound ใน benchmark จึงไม่ใช่ certified bound และไม่อนุญาตให้อ้าง continuous optimum

## 5. รายละเอียด Phase Arrangement

ผล 5 กรณีที่สำเร็จ:

| กรณี | Arrangement count | Near-equal grid count | Grid 40×40 | เวลา Arrangement (s) | เวลา near-grid median (s) | เวลา Grid 40×40 (s) |
|---|---:|---:|---:|---:|---:|---:|
| `concave_L` | 135 | 135 | 135 | 0.1883 | 0.2442 | 0.4439 |
| `concave_U` | 150 | 150 | 150 | 0.1952 | 0.2590 | 0.5004 |
| `near_touching_obstacles` | 150 | 150 | 150 | 0.0645 | 0.0671 | 0.3038 |
| `large_projected_coords` | 1691 | 1691 | 1691 | 0.4302 | 0.7059 | 2.9082 |
| `tiny_scale` | 112 | 104 | 112 | 0.0088 | 0.0077 | 0.3250 |


ใน 4 จาก 5 กรณี arrangement ใช้เวลาน้อยกว่า near-equal grid; ใน `tiny_scale` ใช้เวลามากกว่าเล็กน้อย (1.13× หากเรียงตามผลชุดปัจจุบัน) ผล count สูงกว่า near-equal grid 1 กรณี (`tiny_scale`) แต่ **ทุก 5 กรณีมี count เท่ากับ grid 40×40** จึงยังไม่แสดงว่าหา count ที่ดีกว่า dense grid ได้ในชุดนี้ ส่วนการใช้งานจริงจำกัดด้วยเพดาน boundary fragments 600 และ candidate sites 250,000; 5 กรณีที่เกินเพดานต้อง fallback ไปใช้ grid/adaptive search

## 6. Certified upper bound — ความหมายและผล

`engine/certified_upper_bound.py` ใช้ convex-hull + Steiner parallel-body area bound และคำนวณ outward rational bounds สำหรับ polygon vertices และ spacing ที่รับเข้ามาในรูป binary-float values:

N × A_cell ≤ A_hull + P_hull × R_cell + π × R_cell², and N_UB = floor(Q_upper).

สำหรับ basis angle 90° ใช้ determinant area ab และ covering radius 0.5 × sqrt(a²+b²); สำหรับ 60° ใช้ lower rational bound ของ sqrt(3) ใน cell area และ upper rational bound ของ covering radius

ขอบเขตนี้ใช้กับ ideal Euclidean lattice family และ represented valid polygonal usable geometry เท่านั้น; convex hull อาจเติมบริเวณเว้า จึงอาจหลวมมาก แต่ไม่ควรนำค่า legacy GEOS buffer estimate มาแทน certificate โดยไม่มี proof

**ข้อจำกัดที่ยังเหลือ:** geometry vertices เป็นผลจาก Geometry Engine/GEOS floating operations; certificate พิสูจน์ bound สำหรับตัวเลข vertex ที่แทนอยู่ ไม่ได้พิสูจน์ว่ารูปทรงนั้นตรงกับสวนจริงหรือแนวเขตสำรวจ และ candidate feasibility ยังเป็น numerical checks ไม่ใช่ exact proof ดังนั้นแม้ best count เท่ากับ UB ในอนาคต ก็ยังต้องมี independent formal feasibility certificate ก่อนกล่าวว่า optimum

## 7. ข้อสรุปการพัฒนา

1. คง finite angle/phase grid เป็น fallback ที่เสถียรและใช้เป็น production comparator ต่อไป
2. เก็บ BnB เป็น research prototype สำหรับกรณีที่ผลประโยชน์เชิง count คุ้มต้นทุน; ยังไม่แทน grid
3. เก็บ Phase Arrangement เป็น fixed-orientation acceleration candidate เมื่อผ่าน complexity guard; ยังไม่เป็น solver หลักและไม่อ้าง formal exactness
4. พัฒนาชั้นเลือก solver ตาม complexity ของ geometry และ budget ที่ผู้ใช้กำหนด พร้อมแสดง fallback/skip status
5. ก่อนแสดง optimum ต้องพัฒนา formal feasibility verifier ที่เข้มกว่าการตรวจ floating-point สองชุดในปัจจุบัน

## 8. ข้อจำกัดทั่วไป

- ทุก geometry, spacing และ obstacle ในรายงานเป็น synthetic fixtures
- ผลลัพธ์ไม่ใช่คำแนะนำทางเกษตร ไม่ได้คำนวณผลผลิต การรอดของพืช ทางเดินเครื่องจักร ระบบน้ำ หรือความเหมาะสมของดิน
- เวลา benchmark ใช้ environment Python 3.13.5, NumPy 2.3.5, Shapely 2.1.2 และเครื่องเดียวกันในรอบทดลองนี้; ไม่ควรสรุปประสิทธิภาพทั่วไปจากค่าเวลา absolute
- benchmark workers ถูกแยกรันทีละกรณีแล้วรวมผล เนื่องจากการรันทุกกรณีใน process เดียวเกินเวลา execution window; ตัวเลขจึงมาจาก individual worker runs ที่เก็บ JSON แยก
- ผลทั้งหมดไม่ใช่ external audit หรือ proof review โดยบุคคลที่สาม
