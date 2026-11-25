# PROUVÉ Spatial — รายงานตรวจสอบและข้อกำหนดการเชื่อมระบบ

**Version:** 0.1  
**วันที่:** 25 พฤศจิกายน 2569  
**สถานะ:** ตรวจซอร์สและจัดทำตัวเชื่อมข้อมูลเบื้องต้น; ทดสอบ Adapter ด้วยข้อมูลสังเคราะห์ 11/11 กรณี; ยังไม่ใช่รุ่นเผยแพร่และยังไม่ผ่านการตรวจสอบภาคสนาม

## 1. ข้อสรุปการตรวจสอบ

เว็บไซต์ `prouve-spatial-validation` เป็น Development Copy ของ PROUVÉ Spatial V0.5.2 จริง แอปในปัจจุบันทำหน้าที่รวบรวมและจัดการหลักฐานพื้นที่ ได้แก่ วาด/แก้แนวเขต ตรวจรูปทรง คำนวณพื้นที่ บันทึกที่มาข้อมูล จัดการ CRS เปรียบเทียบแนวเขตกับผลสำรวจ นำเข้าข้อมูลพิกัดบางรูปแบบ และเตรียมภาพ GeoTIFF เป็นภาพ PNG สำหรับแสดงทับบนแผนที่

ใน `index.html` มีฟังก์ชัน `projectDoc()` และข้อมูล `optimizerHandoff` แต่ handoff ส่งต่อเฉพาะแนวเขตและสถานะ ยังไม่ส่งข้อมูลสิ่งกีดขวาง ระยะเว้น หรือ Crop Profile และในซอร์สแอปไม่พบการเรียกใช้ `geometry_engine_v02.py` หรือ `optimization_engine_v04.py` รวมทั้งไม่พบผลลัพธ์ `planting_positions` ดังนั้น ณ ตอนนี้ **แอปยังไม่ใช่ระบบ optimizer แบบครบวงจร**

Geometry Engine V0.2 และ Optimization Engine V0.4 เป็นโมดูล Python แยกกัน ตัวแรกคำนวณพื้นที่ใช้ปลูกหลังเว้นขอบและสิ่งกีดขวาง ส่วนตัวที่สองค้นหาตะแกรงตำแหน่งปลูกภายใต้ชุดมุมและ phase ที่กำหนดไว้

**ข้อสรุป:** สิ่งที่ขาดไม่ใช่ฟีเจอร์แผนที่เพิ่มอีกจำนวนมาก แต่คือสัญญาข้อมูลส่งต่อที่ปลอดภัย (handoff contract), ตัวรันงานที่ทำซ้ำได้, ตัวตรวจสอบผล และรายงานหลักฐานที่ผูกกับข้อมูลต้นทาง/พารามิเตอร์/รุ่นซอฟต์แวร์

## 2. แหล่งข้อมูลและขอบเขตการตรวจ

### Development Copy บน GitHub

- Repository: `number-theory-Lab/prouve-spatial-validation`
- จุดประสงค์ที่ระบุ: `PROUVE Spatial V0.5.2 Development Validation`
- main branch HEAD ที่ตรวจ: `9169c51f4fa7a5b55a5979c3f16de2cfbe9a7cde`
- `index.html` blob: `2b0341b8d69828de39e8a5ad9a27e4f116a0633b`
- `sw.js` blob: `b06f0a055d461c051aceee277ef09764ff8b0e6d`
- เอกสารหลัก: `VALIDATION_LOG_2026-11-23.md` และ `PROUVE_SPATIAL_NORTH_STAR_AND_RESEARCH_CORE.md`

### โมดูลวิจัยที่ตรวจอ่าน

- `geometry_engine_v02.py` จำนวน 275 บรรทัด
- `optimization_engine_v04.py` จำนวน 517 บรรทัด
- `independent_verifier.py`
- `independent_verification.json`
- เอกสาร PreField V0.3 ได้แก่ Patch Notes, Benchmark Register V0.2, Evidence Register V0.2, Traceability Register V0.2 และ Master Control Register V0.2

การตรวจนี้เป็นการอ่านซอร์สและเอกสาร ไม่ใช่การดึง ZIP เครื่องยนต์เดิมมารันในสภาพแวดล้อมสะอาด ทะเบียนหลักฐานของโครงการจัดระดับซอร์สเครื่องยนต์เป็น source reviewed แต่ยังไม่ re-executed ในแพ็กเกจนี้ ส่วนผลทดสอบที่เคยรายงานและผลตรวจ 1,754 จุดจึงยังเป็นหลักฐานที่รายงานไว้ ไม่ใช่ผลที่ผมทำซ้ำเองในรอบนี้

## 3. ความสามารถแอปที่มีอยู่และสิ่งที่ยังอ้างไม่ได้

| ส่วนของแอป | สิ่งที่ทำได้ตามซอร์ส | สิ่งที่ยังไม่พิสูจน์ |
|---|---|---|
| วาด/แก้แนวเขต | เพิ่ม ลบ ย้ายจุด ตรวจรูปหลายเหลี่ยมพื้นฐาน และคำนวณพื้นที่ | ความถูกต้องระดับแนวเขตที่ดินตามการรังวัด |
| CRS | เก็บ CRS ต้นทางและ CRS สำหรับคำนวณ รองรับ UTM เขต 47/48 | คุณภาพ datum/control หรือการสอบเทียบความไม่แน่นอนตำแหน่ง |
| เปรียบเทียบผลสำรวจ | เปรียบเทียบแนวเขตที่ร่างกับพิกัดสำรวจที่กรอกแยก โดยใช้จุดตัวอย่างตามแนว | การรับรองโดยผู้สำรวจหรือผู้เชี่ยวชาญโดยอัตโนมัติ |
| GPX/CSV/GeoJSON | นำเข้ารูปแบบพิกัด/รูปทรงที่กำหนดไว้ | การแลกเปลี่ยนข้อมูล GIS ได้ทุกชนิด หรือรองรับ GeoPackage/Shapefile ทั่วไป |
| GeoTIFF | อ่าน GeoTIFF บางรูปแบบ แปลงเป็น PNG เพื่อแสดงทับแผนที่ และสร้าง Field Pack | การสกัดแนวเขตอัตโนมัติ การเก็บ GeoTIFF ต้นฉบับใน Field Pack หรือการรับรองความแม่นยำตำแหน่ง |
| Offline/local storage | เก็บร่างและภาพชุดที่เตรียมไว้; cache แอป/ไลบรารีหลังเรียกใช้ขณะออนไลน์ | เปิดใช้งานครั้งแรกแบบไม่มี cache หรือมีแผนที่ฐานออฟไลน์ครบพื้นที่ |
| Optimizer handoff | ส่งแนวเขต CRS สถานะ และ provenance; ระบุว่าสิ่งกีดขวาง/ข้อมูลพืชต้องส่งแยก | การคำนวณ usable area, การรัน optimizer, verifier pass หรือแผนจุดปลูก |

ข้อควรระวัง: `optimizerHandoff.acceptedForGeometryProcessing` สะท้อนผลตรวจรูปทรงของแอปเท่านั้น ไม่ใช่การอนุมัติจาก Geometry Engine หรือการรับรองความเหมาะสมทางการเกษตร ส่วน `readyForFieldUse` ที่แอปสร้างขึ้นไม่ควรถูกใช้เป็นใบอนุญาตลงปลูกโดยตรง เพราะสถานะ `USER_CONFIRMED` คือการยืนยันของผู้ใช้ ไม่เท่ากับการสำรวจอิสระ

## 4. หน้าที่ของเครื่องยนต์และการจับคู่ข้อมูล

### Geometry Engine V0.2

รับข้อมูลหลักดังนี้:

- `field.vertices`: จุดยอดขอบเขตแปลงในพิกัดระนาบ XY หน่วยเมตร
- `obstacles`: รายการรูปหลายเหลี่ยมสิ่งกีดขวาง มีชื่อและพิกัด
- `settings.boundary_setback_m`: ระยะเว้นขอบแปลง
- `settings.obstacle_buffer_m`: ระยะเว้นสิ่งกีดขวาง
- ตัวเลือกเพิ่มเติม `quad_segs` และ `geometry_tolerance_m`

ผลลัพธ์เป็นพื้นที่ด้านในหลังเว้นขอบ พื้นที่ตัดออกจากสิ่งกีดขวาง พื้นที่ใช้ปลูกเชิงเรขาคณิต และการตรวจระยะเคลียร์รันซ์ ตัวเครื่องยนต์ระบุเองว่าไม่ได้ทำ placement optimization และยังไม่ได้พิสูจน์จำนวนต้นสูงสุด

### Optimization Engine V0.4

ต้องรับข้อมูลพืชเพิ่ม ได้แก่:

- `crop.row_spacing_m`
- `crop.in_row_spacing_m`
- `crop.plants_per_hole_after_thinning`

เครื่องยนต์ใช้ Geometry Engine แล้วเปรียบเทียบ baseline แบบตะแกรงสี่เหลี่ยม ค้นหามุมและ phase ภายในชุดค่าที่แจกแจงไว้ และอาจเปรียบเทียบตะแกรงสี่เหลี่ยมจัตุรัส/สามเหลี่ยมที่ปรับพื้นที่ต่อจุดให้ใกล้เคียงกัน การเปรียบเทียบสองแบบหลังเป็น benchmark เชิงเรขาคณิต ไม่ใช่คำแนะนำทางการเกษตร และผลที่ดีที่สุดใน finite search grid ไม่ได้แปลว่าเป็น global optimum โดยอัตโนมัติ

### สัญญาการแปลงข้อมูล

| ข้อมูลจากแอป | ส่งเข้าเครื่องยนต์เป็น | กติกา |
|---|---|---|
| `boundary.workingVertices` | `field.vertices` | ตรวจจำนวน/ความเป็นตัวเลข/หน่วย/CRS ก่อน และให้ Geometry Engine ตรวจซ้ำ |
| `boundary.workingระบบพิกัด` | `crs` และ provenance | Adapter V0.1 รับ EPSG:32647/32648; `LOCAL:METRE` ใช้ได้เฉพาะ demo |
| `boundary.status` | สถานะ gate | `USER_CONFIRMED` ใช้ exploratory; `SURVEY_VERIFIED` ต้องมีผลเทียบสำรวจผ่าน |
| ไม่มี obstacles ใน handoff ปัจจุบัน | `obstacles` จาก site profile | ต้องระบุชัด แม้ไม่มีสิ่งกีดขวางต้องใส่ `[]` |
| ไม่มี crop profile ใน handoff ปัจจุบัน | `crop` จากโปรไฟล์ที่ผู้เชี่ยวชาญตรวจ | ห้ามใช้ค่า default ของ optimizer แทนข้อมูลพืชจริง |
| ระยะเว้น/พารามิเตอร์ | `settings` | ระบุค่าชัดและเก็บแหล่งที่มา ห้ามใช้ค่า default เงียบ ๆ |
| ข้อมูลสำรวจ | audit record | เก็บค่าเดิมตามเอกสาร ห้ามนำ RMSE หรือค่าคลาดเคลื่อนที่รายงานมาแปลงเป็น hard bound โดยพลการ |
| uncertainty model | audit record แยก | ห้ามบวกเข้ากับ setback โดยอัตโนมัติหากไม่มีแบบจำลองที่ผู้เชี่ยวชาญอนุมัติ |

## 5. Blockers ที่ต้องปิดก่อนเชื่อม optimizer

ประเด็นเหล่านี้มีบันทึกไว้ใน PreField V0.3 Source Remediation Patch Notes แล้ว แต่ยังไม่พบหลักฐานว่าแพตช์ถูกติดตั้งและรันทดสอบซ้ำในซอร์สเครื่องยนต์

### A — การจัดประเภทเมื่อ BF มากกว่า UB

โค้ด V0.4 ใช้ `best_count >= upper_bound_count` เพื่อตั้ง `continuous_lattice_optimum_proven` หาก BF มากกว่า UB จะถูกจัดสถานะเหมือนพิสูจน์ optimum ได้ ทั้งที่เป็นความขัดแย้ง ต้องเปลี่ยนเป็น `BOUND_CONFLICT` และหยุดการรับรอง

### B — การปัดเศษ upper bound

`lattice_upper_bound()` ใช้ `ceil(quotient - 1e-12)` การลบค่าคงที่อาจทำให้ UB ต่ำกว่าค่าที่ควรเมื่อ quotient จริงอยู่เหนือจำนวนเต็มเล็กน้อย การออกใบรับรองต้องมีขอบเขตบนของพื้นที่ขยายและขอบเขตล่างของพื้นที่เซลล์ พร้อมการปัดเศษออกด้านที่ปลอดภัย ระหว่างยังไม่มีให้ติดป้าย `UB_ESTIMATE_ONLY` และห้ามรับรอง continuous-lattice optimum

### C — ตัวตรวจสอบอาจรับแผนว่าง

`independent_verifier.py` ตั้งตัวนับข้อผิดพลาดทุกตัวเริ่มที่ศูนย์ แล้วคำนวณ `passed = all(v == 0 ...)` รายการ `planting_positions` ที่ว่างอาจผ่านได้ ต้องให้ผลว่างเป็น `NO_FEASIBLE_POINTS`, `all_checks_passed=false` และ `verified_point_count=0`

### D — ความเป็นอิสระของ verifier ยังไม่เต็ม

verifier ไม่ import optimizer และไม่เรียก Geometry Engine โดยตรง แต่ยังใช้ Shapely/GEOS ร่วมกัน จึงแยก implementation บางส่วนแต่ยังไม่แยก dependency ทั้งหมด งาน B5 ต้องมี reference verifier อีกชุดที่ใช้วิธี/ไลบรารีแยก และทดสอบ disagreement, false acceptance และ missed violation

### E — ยังไม่มี pipeline แบบ end-to-end

แอป browser ยังไม่เรียก Python engines และไม่มีหน้าผล optimizer/ตำแหน่งปลูก ยังไม่มี service หรือ local runner ที่มีเวอร์ชันและสร้าง output bundle ซึ่งผูก input, parameter, source hash, จุดปลูก, verifier และ run manifest เข้าด้วยกัน

## 6. ตัวเชื่อมข้อมูล Handoff Adapter V0.1

ผมได้สร้าง `handoff_adapter.py` เพื่อแปลง app boundary export ร่วมกับ site/crop profile แยก เป็น input schema ที่ Geometry Engine V0.2 และ Optimization Engine V0.4 คาดหวัง ตัวนี้ยังไม่รัน engine

| โหมด | เงื่อนไข | สถานะที่ได้ |
|---|---|---|
| `demo` | ใช้ `LOCAL:METRE` และข้อมูลสังเคราะห์เท่านั้น | `DEMO_ONLY` |
| `exploratory` | CRS UTM เมตร และ boundary `USER_CONFIRMED` หรือ `SURVEY_VERIFIED` | `EXPLORATORY_ONLY` หรือ `SURVEY_VERIFIED_EXPERT_REVIEW_PENDING` |
| `field_candidate` | `SURVEY_VERIFIED`, มี survey vertices/metadata และ survey comparison ผ่าน, มี reviewer/date สำหรับ boundary, obstacles, settings, crop, uncertainty, ระบุ sources ครบ และ uncertainty status เป็น APPROVED | `INPUT_GATE_PASSED_NOT_FIELD_VALIDATED` |

แม้ผ่าน `field_candidate` ก็หมายถึงผ่านเฉพาะประตูข้อมูลก่อนรันเครื่องยนต์ ไม่ใช่อนุญาตให้ลงปลูกจริง ทุกโหมดตั้ง `field_deployment_authorized=false`

Adapter บังคับระบุระยะเว้นขอบ ระยะเว้นสิ่งกีดขวาง จำนวนส่วนโค้ง ความทนทานเชิงตัวเลข รายการ obstacles และ crop profile อย่างชัดเจน ตรวจ source CRS/working CRS, source vertices/working vertices และ survey reference geometry/metadata บล็อก CRS ที่ไม่รองรับ พิกัด NaN/Infinity ขอบเขตร่าง และระยะปลูกที่ไม่เป็นบวก; field_candidate ต้องมีผู้ทบทวนการตั้งค่า settings ด้วย พร้อมสร้าง SHA-256 สำหรับไฟล์แอป โปรไฟล์ และ engine case

## 7. ผลทดสอบ Adapter

`test_handoff_adapter.py` มี 13 กรณี ผลล่าสุด **13/13 PASS** ได้แก่:

1. USER_CONFIRMED ให้ได้เพียง exploratory
2. DRAFT ถูกปฏิเสธ
3. LOCAL:METRE ถูกปฏิเสธในโหมดพื้นที่จริง
4. ขาดการตั้งค่าระยะเว้นที่ชัดเจนถูกปฏิเสธ
5. ไม่ระบุ obstacles แม้ไม่มีสิ่งกีดขวางถูกปฏิเสธ
6. ระยะปลูกเป็นศูนย์ถูกปฏิเสธ
7. field_candidate ต้องผ่าน survey verification และ review
8. ข้อมูลที่ผ่าน review ได้เพียงผ่าน input gate ไม่ใช่ field validation
9. CRS ที่ไม่รองรับถูกปฏิเสธ
10. พิกัด NaN ถูกปฏิเสธ
11. uncertainty review flag เพียงอย่างเดียวไม่พอ หาก `uncertainty.status` ยังไม่ APPROVED
12. field_candidate ต้องมีผู้ทบทวน settings แยกต่างหาก
13. พิกัดต้นทาง (sourceVertices) ที่เป็น Infinity ถูกปฏิเสธ

ผลนี้ทดสอบเฉพาะ contract ของ Adapter ไม่ได้ทดสอบ geometry calculation, lattice search, upper-bound validity, browser, agronomy หรือภาคสนาม

## 8. ลำดับการพัฒนาต่อไป

| ลำดับ | งาน | เกณฑ์ปิด | สถานะ |
|---|---|---|---|
| 1 | ตรึงรุ่นแอปและ hash ของ engine sources | มี source/archive inventory ที่ทำซ้ำได้ | ทำบางส่วน; engine ZIP ยังรอ rerun |
| 2 | แก้ PATCH-01 ถึง PATCH-10 ใน engine branch แยก | มี fixture, expected result และ hash ครบทุกกรณี | ยังไม่เริ่ม |
| 3 | สร้าง pipeline runner: adapter → geometry → optimization → verifier → run bundle | คำสั่งเดียวสร้าง case, results, point CSV, verification และ manifest | ยังไม่เริ่ม |
| 4 | สร้าง independent verifier V2 | implementation/library แยก และผ่าน empty-plan/injected-error tests | ยังไม่เริ่ม |
| 5 | รัน Benchmark B0-B5 | input/profile/CRS/compute budget เท่ากันและทำซ้ำได้ | วางแผนแล้ว |
| 6 | เพิ่มแผง optimizer ใน browser | แสดง BF, UB, gap, assumptions, verification, provenance และดาวน์โหลดได้ | ยังไม่เริ่ม |
| 7 | FTS-01, E12/E13 | มี survey, uncertainty, agronomy review และ user-task evidence | รอผู้ใช้/ผู้เชี่ยวชาญ/ข้อมูลพื้นที่ |

## 9. ข้อวินิจฉัยและการตัดสินใจ

ยังไม่ควรแก้เว็บไซต์ Development Copy ที่เผยแพร่สาธารณะในตอนนี้ และยังไม่ควรเรียกแอปปัจจุบันว่า integrated optimizer ขั้นต่อไปที่ปลอดภัยคือเรียกคืน engine source ZIP ที่รันได้จริง แก้ blockers A-C และชุด PATCH-01..10 ใน branch แยก จากนั้นสร้าง local reproducible pipeline แล้วจึงออกแบบ UI optimizer ให้เรียก pipeline นั้น ไม่ควรเขียนอัลกอริทึมซ้ำลงใน `index.html`

หลักการแยกข้ออ้าง:

- `USER_CONFIRMED` ไม่เท่ากับ survey-certified
- GeoTIFF preview ไม่เท่ากับการสกัดขอบเขตหรือการตรวจความแม่นยำตำแหน่ง
- แผนที่ผ่านข้อจำกัดเรขาคณิตไม่เท่ากับคำแนะนำทางการเกษตร
- `BEST_FOUND` ใน finite search ไม่ใช่ global optimum
- `OPTIMAL_WITHIN_DECLARED_LATTICE_FAMILY` ใช้ได้เฉพาะตระกูลที่ระบุ และต้องมี UB ที่รับรองได้กับ verifier ผ่าน
- ทฤษฎี PI แบบหนึ่งมิติไม่ได้พิสูจน์ objective จำนวนจุดปลูกเชิงพื้นที่สองมิติโดยอัตโนมัติ


## 10. สิ่งที่ต้องใช้เพื่อดำเนินการเชื่อมเครื่องยนต์จริง

### สิ่งที่ยังทำต่อได้ในขั้นพัฒนา

- ปรับ Adapter contract, fixtures และ test cases ให้ครอบคลุม CRS, geometry handoff, source lineage และสถานะ gate
- ออกแบบ runner และ output manifest โดยยังไม่เปิดให้ใช้งานภาคสนาม
- เตรียม benchmark protocol และ verifier test harness แยกจาก UI

### สิ่งที่จำเป็นก่อน patch และรัน engine ซ้ำ

แพ็กเกจ PreField V0.3 ที่ตรวจพบมี Patch Notes และทะเบียนทดสอบ แต่ไม่มีไฟล์ต้นฉบับ `geometry_engine_v02.py`, `optimization_engine_v04.py` และ `independent_verifier.py` ใน ZIP นั้น ส่วนสำเนาซอร์สที่อ่านได้ในบริบทนี้เป็นข้อความที่ค้นคืนจาก Project files ไม่ใช่ raw source archive ที่ materialize เพื่อนำไปรันใน clean environment ได้ ดังนั้นการแก้และรายงานผลรันจริงต้องใช้ ZIP/source package ของ engine พร้อม fixtures, requirements และผล baseline เดิมที่ตรงรุ่น

### สิ่งที่ต้องมาจากผู้ใช้หรือผู้เชี่ยวชาญก่อน FTS-01

- ผู้ใช้: ขอบเขตสวน ภาพถ่าย/หมุดโดยประมาณ สิ่งกีดขวาง ทางเข้า และคำอธิบายสภาพพื้นที่
- ผู้สำรวจ: CRS/datum, independent checkpoints, GNSS/survey logs และความไม่แน่นอนของจุดอ้างอิง
- ผู้เชี่ยวชาญเกษตร: ชนิดพืช ระยะปลูก/ระยะระหว่างแถว จำนวนต้นต่อหลุม และข้อจำกัดการปฏิบัติงานที่เหมาะสม

จนกว่าจะครบข้อมูลเหล่านี้ FTS-01 ยังคงเป็น Candidate และผลที่ได้จาก sample files เป็นเพียง synthetic demonstration เท่านั้น
