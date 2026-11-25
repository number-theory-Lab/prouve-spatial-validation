# PROUVÉ Spatial — สถานะประตูงานถัดไปหลัง V0.3.1

## สิ่งที่เสร็จในรอบนี้

- [x] ตรวจ source package V0.3 และแยก baseline V0.3.1
- [x] harden exact-rational feasibility input
- [x] harden rational lattice relation certificate
- [x] จัดการกรณี usable geometry ว่างแบบ HOLD
- [x] ทดสอบ Certified Upper Bound V0.3.1 โดยตรง
- [x] สุ่มตรวจ rectangular และ triangular lattice รวม 700 phase/orientation samples
- [x] รัน synthetic pipeline: rectangle, MultiPolygon-with-holes, empty usable geometry
- [x] จัดทำ audit report และ release notes

## ประตูที่ยังเปิดอยู่

| ลำดับ | งานถัดไป | ผู้รับผิดชอบหลัก | สิ่งที่ต้องใช้ |
|---|---|---|---|
| 1 | Independent mathematical review | ผู้เชี่ยวชาญ/ครูคณิตศาสตร์ ร่วมกับผู้พัฒนา | proof, source code, test evidence |
| 2 | CRS and survey protocol | ผู้พัฒนา + ผู้สำรวจ/ผู้เชี่ยวชาญ GIS | CRS, datum, หน่วย, survey method, control/checkpoints |
| 3 | FTS-01 site data | ผู้ใช้/ผู้สำรวจ | ขอบเขตสวน, obstacles, entrance, slope, ภาพและจุดตรวจวัด |
| 4 | Uncertainty budget | ผู้พัฒนา + ผู้สำรวจ | error source แต่ละชนิดและหลักฐานการวัด |
| 5 | Crop Profile approval | ผู้เชี่ยวชาญเกษตร | ระยะปลูก, ระยะเว้น, operational constraints, source references |
| 6 | App integration | ผู้พัฒนา | interface mapping, adapter, app-side validation |
| 7 | Device acceptance | ผู้ใช้/ผู้ทดสอบ | โทรศัพท์/แท็บเล็ตจริง, offline/online, export/import test |
| 8 | Field validation | ผู้ใช้ + ผู้เชี่ยวชาญ | จุดที่เสนอ, independent checkpoints, actual staking measurements |

## ข้อห้ามก่อนผ่าน Gate

- ห้ามใช้พิกัดแสดงผลที่ปัดเศษเป็นข้อมูล stake-out
- ห้ามเรียก best-found ว่า optimum หากยังไม่ผ่านเงื่อนไข equality กับ UB ใน scope เดียวกัน
- ห้ามแปลผล “ค้นหาไม่พบ” ว่า “ไม่มีคำตอบ”
- ห้ามใช้ข้อมูลพิกัด lat/long เป็นเมตรโดยไม่แปลงผ่าน CRS ที่ถูกต้อง
- ห้ามประกาศ field-ready หรือใช้กับแปลงจริงก่อน survey, uncertainty และ agronomy gates ผ่าน

**สถานะรวม:** Internal V0.3.1 milestone เสร็จแล้ว; FTS-01, expert review, app integration และ field deployment ยังไม่เริ่ม/ยังไม่ผ่าน
