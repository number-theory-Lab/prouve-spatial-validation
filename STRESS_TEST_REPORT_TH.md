# PROUVÉ Spatial — Stress Test Report V0.2

**วันที่:** 25 พฤศจิกายน 2569  
**สถานะ:** ผ่านชุดทดสอบสังเคราะห์ที่ระบุ; ยังไม่ใช่ภาคสนามหรือ external audit

## 1. ผลสรุป

ทดสอบ stress geometry 12 ลักษณะ ครอบคลุม polygon เว้า รูปทรงหลายมุม สิ่งกีดขวางจำนวนมาก ช่องแคบ แปลงแถบบางมาก พิกัดฉายขนาดใหญ่ สเกลเล็ก และกรณีความละเอียด floating-point ไม่รองรับ

| สถานะ | จำนวน |
|---|---:|
| Geometry PASS มีพื้นที่ใช้ได้ | 10 |
| Geometry PASS แต่พื้นที่ใช้ได้ว่าง | 1 |
| SAFE_REJECT เพราะความละเอียดตัวเลขไม่พอ | 1 |
| รวม | **12** |

กรณี `very_large_offset` ถูกปฏิเสธโดยเจตนา เพราะ ULP ของพิกัด absolute offset ใหญ่กว่าค่า geometry tolerance ที่ประกาศไว้ ระบบแนะนำให้แปลงเป็น local XY แทนการคำนวณต่อด้วยความแม่นยำที่ไม่เพียงพอ

## 2. ชุด stress geometry

| กรณี | ประเด็นที่ทดสอบ | พื้นที่ใช้ได้ (m²) | ผล |
|---|---|---:|---|
| `concave_L` | แปลงเว้า L + สิ่งกีดขวาง 2 รายการ | 753.49 | PASS |
| `concave_U` | แปลงเว้า U + สิ่งกีดขวาง | 791.11 | PASS |
| `radial_concave_24` | แนวขอบเว้าหลายสลับ 24 vertices | 3,274.74 | PASS |
| `many_obstacles_25` | สิ่งกีดขวาง 25 ชิ้น | 9,119.12 | PASS |
| `obstacle_dense_36` | สิ่งกีดขวาง 36 ชิ้นแบบหนาแน่น | 1,995.90 | PASS |
| `narrow_corridor` | แปลงทางแคบ 100 × 1 m | 79.84 | PASS |
| `near_degenerate_sliver` | แถบแปลง 100 × 0.01 m | 0.799984 | PASS |
| `near_touching_obstacles` | สิ่งกีดขวางเกือบสัมผัสกัน | 832.99 | PASS |
| `large_projected_coords` | พิกัดประมาณ (500,000, 1,000,000) m | 9,752.85 | PASS |
| `tiny_scale` | แปลงขนาดเล็กระดับเซนติเมตร | 0.00028616 | PASS |
| `setback_erases_area` | setback ทำให้พื้นที่ปลูกว่าง | 0 | PASS_EMPTY |
| `very_large_offset` | absolute offset ประมาณ 10¹² m | — | SAFE_REJECT |

พื้นที่ด้านบนเป็นผลจาก synthetic fixture เท่านั้น ไม่ใช่พื้นที่สวนจริง

## 3. การปรับ candidate enumeration

ก่อน V0.2 การสร้าง candidate lattice indices จาก Cartesian product ของ projected bounding box อาจสร้าง candidate จำนวนมากเกินจำเป็น โดยเฉพาะรูปทรงยาวและแคบที่หมุนเฉียง

V0.2 เปลี่ยนมาใช้ scanline envelope ใน lattice-coordinate space และเพิ่ม guard:

- `int64` สำหรับ lattice indices แทน `int32`
- candidate lattice cells สูงสุด 5,000,000 ต่อ basis orientation
- scanline spans สูงสุด 1,000,000 ต่อการสร้าง candidate set
- ปฏิเสธเมื่อ index เกินช่วง `int64`

การตรวจความสอดคล้องของ scanline เทียบกับวิธี bounding-box เดิมทำใน `concave_L`, `concave_U`, `large_projected_coords`, `tiny_scale` ที่ 5 orientations และ 3 random phase samples ต่อ orientation โดยทุกกรณีมีจำนวน accepted points เท่ากัน และไม่มี accepted index ถูกตัดทิ้ง

กรณีแถบบางหมุน 45° สามารถสร้าง candidate indices ได้มากกว่า 100,000 แต่ต่ำกว่า 1,000,000 โดยไม่สร้าง full Cartesian bounding box

## 4. End-to-end stress verification

ทดสอบ Adapter → Geometry → Optimization → Reference Verifier → Shapely/GEOS Verifier ในกรณี `concave_L`, `concave_U`, `many_obstacles_25`, `large_projected_coords` ผล verifier ทั้งสองผ่านและจำนวนจุดตรงกัน

Reference Verifier ไม่ใช้ Shapely แต่ยังใช้ floating-point และรองรับ simple polygon rings ที่ไม่มีรู ส่วน Shapely Verifier ใช้ GEOS ร่วมกับ Geometry Engine จึงเป็น cross-check ไม่ใช่ independent geometry library audit

## 5. สิ่งที่ยังจำกัด

- `near_degenerate_sliver` ค้นหา 166,665 จุดใน finite search ที่กำหนด และใช้เวลาประมาณ 6 วินาทีต่อการรัน grid benchmark ใน environment นี้ แต่ BnB ถูกข้ามเพราะ orientation-independent candidate index envelope เกิน 1.66 พันล้าน
- Phase Arrangement ถูกข้ามเมื่อ boundary fragments เกิน 600 หรือ candidate lattice index sites เกิน 250,000
- absolute offset 10¹² m ไม่ใช่การทดสอบให้ผ่าน แต่เป็นการทดสอบ safe rejection
- ไม่มีภาพดาวเทียมจริง ข้อมูล GNSS จุดควบคุมสำรวจ หรือข้อมูลแปลงเกษตรจริง
- ไม่มีการพิสูจน์ agronomic feasibility หรือผลผลิต

## 6. สรุป

Stress Test ชุดนี้แสดงว่า branch จัดการกรณีสังเคราะห์ที่หลากหลายได้ และปฏิเสธกรณีที่ความละเอียดตัวเลขไม่รองรับแทนการสร้างผลลัพธ์ที่ไม่น่าเชื่อถือ อย่างไรก็ตามคำว่า PASS จำกัดอยู่ที่ fixtures, tolerance, library versions และ tests ที่ระบุเท่านั้น
