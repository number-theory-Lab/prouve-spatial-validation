# PROUVÉ Spatial — รายงานตรวจสอบวิศวกรรมภายใน V0.3.1

**ประเภทเอกสาร:** รายงานตรวจสอบโค้ดและหลักฐานภายใน (Internal Engineering Audit)  
**รุ่น:** Engine Branch V0.3.1  
**วันที่จัดทำ:** 25 พฤศจิกายน 2569  
**ผลรวม:** ผ่านชุดทดสอบอัตโนมัติ 113/113 รายการ และผ่าน pipeline สังเคราะห์ 2 กรณี; กรณีพื้นที่ใช้ได้ว่างถูกหยุดด้วย HOLD ตามที่ออกแบบ  
**สถานะการใช้งาน:** ทดลองเชิงวิศวกรรมเท่านั้น — ยังไม่อนุญาตให้ใช้วางจุดปลูกจริง

---

## 1. บทสรุปผู้บริหาร

V0.3.1 เป็นรุ่นปรับความเข้มงวดของ Engine Branch V0.3 โดยเน้นสามเรื่องที่มีผลโดยตรงต่อความน่าเชื่อถือของผลลัพธ์ ได้แก่

1. **ใบรับรองความเป็นไปได้ (Formal Feasibility Certificate):** ตรวจจุดปลูกที่ส่งเข้ามาเทียบกับเรขาคณิตต้นทางและระยะเผื่อที่ประกาศไว้ ด้วยเลขตรรกยะ (rational arithmetic) แทนการตัดสินใจด้วย floating-point tolerance
2. **ใบรับรองความสัมพันธ์กับ lattice:** ตรวจว่าจุดแต่ละจุดอยู่บน lattice ที่ประกาศจริง มีดัชนีจำนวนเต็ม ไม่มีดัชนีซ้ำ และฐาน lattice เป็นฐานตั้งฉากที่สัมพันธ์กับพารามิเตอร์การหมุนอย่างถูกต้อง
3. **ขอบเขตบนที่รับรองได้ (Certified Upper Bound):** จำกัดจำนวนจุดสูงสุดของ lattice family ที่กำหนดด้วยการปูระนาบด้วย fundamental cells และ Steiner formula บน convex hull พร้อมการปัดขอบเขตแบบอนุรักษ์นิยมด้วยเลขตรรกยะ

การตรวจครั้งนี้ยืนยันได้ว่า implementation ที่อยู่ในแพ็กเกจผ่านชุดทดสอบที่ระบุและสร้างผลลัพธ์สังเคราะห์ซ้ำได้ อย่างไรก็ตาม **ยังไม่มีการตรวจโดยผู้เชี่ยวชาญภายนอก ไม่มีข้อมูลสำรวจภาคสนาม ไม่มีการปรับเทียบความคลาดเคลื่อนจาก GNSS/ภาพถ่าย และยังไม่ได้รับรอง Crop Profile โดยผู้เชี่ยวชาญเกษตร** จึงยังไม่ใช่ระบบพร้อมใช้งานจริง

## 2. ขอบเขตและคำจำกัดความของ PASS

คำว่า PASS ในรายงานนี้หมายถึงผ่านการตรวจภายในตามข้อกำหนดและชุดทดสอบของ branch เท่านั้น ไม่ได้หมายถึงผ่านการรับรองมาตรฐานภายนอก หรือพิสูจน์ความเหมาะสมทางเกษตร

| ส่วนงาน | สิ่งที่ตรวจได้ | สิ่งที่ยังไม่ได้รับรอง |
|---|---|---|
| Formal feasibility | จุดที่ส่งมาตรงตาม polygon และระยะเผื่อในข้อมูลตัวเลขที่ระบุ | ความจริงของพิกัดในโลกจริง, CRS/datum, ความแม่นยำการสำรวจ |
| Topology | Polygon/MultiPolygon, รูภายใน, การปฏิเสธวงแหวนหรือองค์ประกอบที่สัมผัส/ตัดกันตามข้อกำหนด | การแก้ topology อัตโนมัติ หรือ geometry ทุกชนิดของ GIS |
| Lattice relation | ฐานตั้งฉากแบบเลขตรรกยะ, phase, ดัชนีจำนวนเต็ม, ระยะห่างขั้นต่ำจากโครงสร้าง lattice | lattice เอียงทั่วไปที่ไม่มีฐานตั้งฉาก, point packing แบบอิสระ |
| Upper bound | ขอบเขตบนของจำนวนจุดใน lattice family ที่ระบุ | ค่าสูงสุดของการจัดจุดอิสระทุกแบบ |
| Adaptive solver | การค้นหา การรวมผล และ fallback แบบจำกัดงบประมาณ | global optimum ต่อเนื่องหรือคำตอบเร็วแบบ hard real-time |
| Field/agronomy | ไม่มีการรับรอง | ความเหมาะสมของชนิดพืช ผลผลิต การให้น้ำ ราก การระบายอากาศ ทางเดินเครื่องจักร |

## 3. ผลการทดสอบรอบสุดท้าย

### 3.1 ชุดทดสอบอัตโนมัติ

- จำนวนรายการทดสอบรวม: **113/113 PASS**
- เวลารันชุดทดสอบรวม: ประมาณ **6 วินาที** ในสภาพแวดล้อมการตรวจรอบนี้
- `compileall` สำหรับ `engine`, `adapter`, `prototype`, `tests`: ผ่าน
- ชุดทดสอบเพิ่มใหม่ของโมดูล Upper Bound V0.3.1: 6 รายการ
  - สุ่ม translation/phase/orientation ของ rectangular lattice 350 ชุด โดยไม่พบจำนวนจุดเกิน UB
  - สุ่ม translation/phase/orientation ของ triangular lattice 350 ชุด โดยไม่พบจำนวนจุดเกิน UB
  - MultiPolygon ที่มีรู: คำนวณ UB ได้และ hull ครอบพื้นที่จริง
  - ตรวจความสอดคล้องของ exact fraction ในผลลัพธ์
  - empty geometry คืน UB = 0
  - ปฏิเสธมุมฐานที่ยังไม่รองรับ

การสุ่ม 700 ชุดเป็น **การทดสอบเชิงประจักษ์เสริม** ไม่ใช่ข้อพิสูจน์ทางคณิตศาสตร์แทน proof ที่อธิบายในหัวข้อ 4

### 3.2 Pipeline สังเคราะห์

| กรณี | Best Found | Certified UB | Gap เทียบ UB | สถานะ | Optimality |
|---|---:|---:|---:|---|---|
| พื้นที่สี่เหลี่ยม | 70 | 77 | 9.09% | PASS — synthetic/exploratory | ยังไม่พิสูจน์ |
| MultiPolygon มีรูและ obstacle | 153 | 209 | 26.79% | PASS — synthetic/exploratory | ยังไม่พิสูจน์ |
| พื้นที่ใช้ได้ว่างหลังเว้นระยะ | 0 | 0 | ไม่คำนวณ | HOLD_EMPTY_USABLE_GEOMETRY | ไม่คำนวณ |

สูตร gap ที่แสดงคือ

\[
\text{Gap}=\frac{UB-\text{Best Found}}{UB}\times100\%.
\]

กรณีแรกและกรณีที่สองมี feasibility certificate ผ่านสำหรับจุดที่ระบบส่งออกในรันนั้น และมี lattice relation certificate ผ่าน แต่ผลที่ได้ยังเป็น **best-found ที่รับรอง feasibility** ไม่ใช่ optimum เพราะ Best Found ยังต่ำกว่า UB

กรณีพื้นที่ว่างถูกหยุดอย่างชัดเจนด้วย HOLD ไม่สร้างแผนปลูกปลอม และไม่ตีความว่าเป็นคำตอบ optimal โดยปริยาย

**ข้อควรระวัง:** เมื่อพื้นที่ใช้ได้ไม่ว่างแต่การค้นหาไม่พบจุด ระบบจะรายงานว่าไม่พบ candidate ภายใต้งบค้นหาที่ตั้งไว้เท่านั้น ไม่ได้พิสูจน์ว่าไม่มีการจัดวางที่เป็นไปได้

## 4. หลักคณิตศาสตร์ของ Certified Upper Bound

ให้ \(U\) เป็นพื้นที่ใช้ได้ที่แทนด้วย polygon และให้ lattice มีเวกเตอร์ฐาน \(a,b\) ซึ่งมีมุมระหว่างฐานเป็น 90° หรือ 60° ตาม family ที่ implementation รองรับ

สร้าง fundamental parallelogram ที่มีจุด lattice เป็นศูนย์กลาง

\[
C=\{sa+tb:-\tfrac12\le s,t\le\tfrac12\}.
\]

เมื่อเลื่อนเซลล์นี้ไปยังทุกจุด lattice เซลล์จะปูระนาบโดยทับซ้อนกันได้เฉพาะขอบซึ่งมีพื้นที่เป็นศูนย์ แต่ละเซลล์มีพื้นที่เท่ากับ determinant ของฐาน

\[
A_C=|\det(a,b)|.
\]

และทุกจุดในเซลล์อยู่ห่างจากศูนย์กลางไม่เกิน covering radius \(R\):

- ฐาน 90°:
  \[
  A_C=ab,\qquad R=\frac12\sqrt{a^2+b^2}.
  \]
- ฐาน 60°:
  \[
  A_C=\frac{\sqrt3}{2}ab,\qquad
  R=\frac12\sqrt{a^2+b^2+ab}.
  \]

หากมี lattice centers ที่ยอมรับได้จำนวน \(N\) จุด ทุกจุดอยู่ใน \(U\) ดังนั้นทุกเซลล์ที่มีศูนย์กลางเหล่านั้นจะอยู่ภายใน parallel body ของ convex hull ของพื้นที่ใช้ได้:

\[
\operatorname{conv}(U)\oplus B(R).
\]

เพราะเซลล์ไม่ทับซ้อนกันในพื้นที่ภายใน จึงได้

\[
N A_C\le \operatorname{Area}(\operatorname{conv}(U)\oplus B(R)).
\]

สำหรับ convex polygon ใช้ Steiner formula:

\[
\operatorname{Area}(K\oplus B(R))=A(K)+P(K)R+\pi R^2.
\]

จึงได้ขอบเขต

\[
N\le \frac{A_H+P_HR+\pi R^2}{A_C},
\]

โดย \(A_H,P_H\) คือพื้นที่และเส้นรอบรูปของ convex hull

### 4.1 ทำให้ขอบเขตเป็น rational outward enclosure

implementation `engine/certified_upper_bound_v03.py` ใช้แนวทางอนุรักษ์นิยมดังนี้

1. แปลงพิกัดตัวเลข finite และระยะ lattice เป็น Fraction จากข้อความทศนิยม canonical (สำหรับ float ใช้ shortest round-trip decimal string)
2. สร้าง convex hull และคำนวณพื้นที่ด้วย rational arithmetic / shoelace formula
3. คำนวณความยาวขอบด้วย rational square-root upper bounds โดย integer arithmetic ที่ scale \(10^{12}\)
4. ใช้ \(355/113\) เป็น upper bound แบบ rational ของ \(\pi\)
5. สำหรับฐาน 60° ใช้ lower bound แบบ rational ของ \(\sqrt3\) เพื่อให้ cell area ที่นำไปหารไม่สูงกว่าค่าจริง
6. หาร area upper ด้วย cell area lower เพื่อได้ rational quotient upper แล้วคืน
   \[
   UB=\left\lfloor Q_{upper}\right\rfloor.
   \]

เนื่องจากจำนวนจุด \(N\) เป็นจำนวนเต็มและ \(N\le Q_{upper}\) จึงได้ \(N\le\lfloor Q_{upper}\rfloor\)

### 4.2 ขอบเขตการรับรองของสูตร

สูตรนี้รับรอง upper bound ของจำนวนจุดสำหรับ **lattice family และระยะฐานที่ประกาศ** โดยศูนย์กลางจุดอยู่ใน polygon ที่แทนอยู่เท่านั้น ไม่ได้เป็น upper bound สำหรับการจัดจุดอิสระที่ไม่จำเป็นต้องอยู่บน lattice

การใช้ convex hull ทำให้ขอบเขตมักหลวมลงเมื่อพื้นที่เว้า มีรู หรือมีหลาย component แต่ไม่ทำให้ hull เล็กกว่าพื้นที่ต้นทาง จึงยังใช้เป็นพื้นที่ครอบเพื่อสร้าง upper bound ได้

## 5. หลักการของ Formal Feasibility Certificate

ไฟล์หลัก: `engine/formal_feasibility_certificate.py`

- รับ GeoJSON `Polygon` และ `MultiPolygon` แบบ 2D เท่านั้น
- ตรวจ ring ปิด มีจุดยอดเพียงพอ ไม่มีจุดซ้ำติดกัน และไม่มี self-intersection/self-touch ตามกติกา
- ตรวจ hole ต้องอยู่ภายใน exterior และไม่สัมผัส/ตัดกับวงแหวนอื่น
- ตรวจ MultiPolygon components ต้องแยกจากกัน ไม่สัมผัส ไม่ตัด และไม่ซ้อนทับ
- ตรวจ point-in-polygon ด้วย ray crossing แบบเลขตรรกยะ
- ตรวจระยะจากจุดถึง segment ด้วย squared distance แบบเลขตรรกยะ แล้วเทียบกับ squared clearance โดยไม่ใช้ epsilon
- ระยะเผื่อที่ใช้จริง = ระยะ clearance ที่ประกาศ + uncertainty allowance ที่ผู้ส่งข้อมูลระบุชัดเจน ระบบไม่เดา uncertainty ให้เอง
- ปฏิเสธพิกัด 3D, boolean, NaN/Infinity และ tuple ที่ไม่ใช่ [x,y]

ตัว certificate ตรวจเฉพาะ **candidate set ที่ส่งเข้ามา** ไม่ได้พิสูจน์ว่า candidate set ครบทุกตำแหน่งที่เป็นไปได้ และไม่พิสูจน์ global optimality

## 6. ใบรับรอง lattice relation และระยะระหว่างจุด

ไฟล์หลัก: `engine/lattice_relation_certificate.py`

สำหรับฐานตั้งฉากที่มีความยาวบวก \(a,b\) และดัชนีจำนวนเต็มที่ต่างกันอย่างน้อยหนึ่งตำแหน่ง ระยะระหว่างจุด lattice มีรูป

\[
\|\Delta i\,a+\Delta j\,b\|^2
=(\Delta i)^2a^2+(\Delta j)^2b^2
\ge \min(a,b)^2.
\]

ตัวตรวจจึงตรวจว่า

- basis vectors สัมพันธ์กับ rational rotation parameter ที่ประกาศ
- basis ตั้งฉากจริงในเลขตรรกยะ
- ความยาวฐานตรงกับค่าที่ประกาศ
- phase อยู่ในช่วง \([0,1)\)
- lattice indices เป็น integer จริง ไม่รับ boolean หรือ float ที่ถูกตัดเศษ
- ไม่มี index pair ซ้ำ และพิกัด rational ตรงกับสูตรจาก basis, phase และ indices

การรับรองนี้เป็นของ **rectangular orthogonal lattice** ไม่ใช่ lattice ทุกชนิด และไม่แทนการตรวจ CRS หรือการสำรวจพื้นที่จริง

## 7. การแก้ไขสำคัญใน V0.3.1

1. ปฏิเสธพิกัดที่มีมิติ 3 หรือจำนวนองค์ประกอบไม่ใช่ 2 อย่างชัดเจน
2. ปฏิเสธ boolean และดัชนี lattice ที่ไม่ใช่ integer แทนการ coercion หรือตัดเศษ
3. ตรวจ metadata ของ lattice ให้สัมพันธ์กันทั้ง rotation, basis, phase และความยาวฐาน
4. ป้องกันการออก lattice certificate ให้ candidate set ว่าง
5. เพิ่มการตรวจ input ของ crop spacing และจำนวนต้นต่อหลุมให้เข้มงวดขึ้น
6. เพิ่มการตรวจพิกัด GeoJSON ที่ Geometry Engine รับโดยตรง
7. แยกสถานะพื้นที่ใช้ได้ว่างออกจากกรณีค้นหาไม่พบจุด
8. กำหนดผล HOLD สำหรับกรณีไม่มี candidate แทนการ crash หรือทำให้เข้าใจผิดว่าเป็น optimum
9. เพิ่มการทดสอบ Upper Bound ของ V0.3.1 โดยตรง แยกจากโมดูลเก่าที่เก็บไว้เพื่อ compatibility
10. รักษาการทำงาน fallback และห้ามใช้ผลของ BnB/Arrangement เชิงตัวเลขเพียงอย่างเดียวเพื่ออ้าง optimality

## 8. Engineering Gates

| Gate | รายการ | สถานะ | เหตุผล |
|---|---|---|---|
| G1 | Exact candidate feasibility | **PASS (จำกัดขอบเขต)** | ผ่าน 2D decimal geometry และ clearance ที่ประกาศ |
| G2 | Polygon holes / MultiPolygon | **PASS (ตาม topology ที่รองรับ)** | รูต้องอยู่ภายใน; components ที่สัมผัส/ตัดกันถูก HOLD |
| G3 | Rational lattice relation | **PASS (rectangular orthogonal)** | ฐานตั้งฉากและดัชนีตรวจด้วย rational arithmetic |
| G4 | Certified lattice upper bound | **PASS (ตาม proof scope)** | 60°/90° family; convex-hull Steiner enclosure |
| G5 | Adaptive solver optimality | **HOLD** | BnB/Arrangement ยังเป็นตัวค้นหาเชิงทดลอง; ไม่มี global optimality claim |
| G6 | Result/evidence viewer | **HOLD** | เป็น HTML prototype; ตรวจ JavaScript syntax เท่านั้น ยังไม่ได้ทำ browser/device acceptance และไม่ merge เข้า app |
| G7 | Independent expert review | **OPEN** | ยังไม่มีผู้ตรวจอิสระลงนามรับรอง proof และ implementation |
| G8 | CRS / survey / uncertainty calibration | **NOT STARTED** | ยังไม่มีข้อมูลสำรวจ FTS-01 และ independent checkpoints |
| G9 | Agronomic Crop Profile | **PENDING** | ต้องมีแหล่งข้อมูลและผู้เชี่ยวชาญยืนยัน crop spacing, clearance และ operational constraints |
| G10 | FTS-01 field validation | **NOT STARTED** | ยังไม่มี geometry และข้อมูลภาคสนามจริง |
| G11 | Published app integration / device acceptance | **NOT STARTED** | V0.3.1 ยังไม่ merge กับ V0.5.2 หรือ GitHub Pages |
| G12 | Field deployment | **BLOCKED** | ต้องผ่าน G5–G11 ที่เกี่ยวข้องก่อน |

## 9. ข้อจำกัดที่ต้องเปิดเผย

1. **Geometry preprocessing:** Geometry Engine ใช้ Shapely/GEOS สำหรับ buffer, inset, union และ overlay ซึ่งเป็นการสร้าง geometry แบบ polygonal approximation ของ offset ไม่ใช่การคำนวณเส้นโค้ง offset แบบ exact-real
2. **ขอบเขต exactness:** Fraction certificate exact ต่อค่าทศนิยมที่ serialize แล้วเท่านั้น ไม่ได้ทำให้พิกัดสำรวจจริง exact และไม่รับรองความแม่นยำของอุปกรณ์
3. **CRS:** ระบบยังไม่พิสูจน์ว่า input ใช้ projected CRS หน่วยเมตรและ datum ถูกต้อง ห้ามป้อน longitude/latitude แล้วตีความว่าเป็นเมตร
4. **Uncertainty:** ยังไม่มีการสอบเทียบ RMSE หรือ uncertainty budget จากภาพถ่าย/GNSS/ขอบเขต/สิ่งกีดขวาง และ RMSE ไม่ใช่ maximum error
5. **Agronomy:** ยังไม่รับรองผลผลิต การแข่งขันของราก แสง น้ำ ปุ๋ย การระบายอากาศ ความลาดชัน การเข้าถึงของเครื่องจักร หรือระยะปลูกจริงของพืชใด
6. **พิกัดแสดงผล:** `x_m_display` และ `y_m_display` เป็นค่าปัดเศษเพื่อแสดงผลเท่านั้น พิกัด rational `x_m`/`y_m` ใช้ใน certificate แต่ทั้งสองยังไม่ใช่ stake-out file สำหรับนำไปปักหลักในแปลงจนกว่าจะกำหนดวิธี export และตรวจภาคสนาม
7. **ขอบเขต benchmark:** ตัวอย่างทั้งหมดเป็น synthetic fixtures ไม่ใช่ผลทดสอบกับสวนจริง ไม่ควรใช้เปรียบเทียบว่าเหนือกว่าโปรแกรมหรืออัลกอริทึม state of the art โดยไม่มี benchmark ที่เทียบกันอย่างยุติธรรม
8. **สถานะโครงการ:** ไม่มีการ merge branch นี้เข้ากับแอป V0.5.2 ที่เผยแพร่ หรือประกาศให้ผู้ใช้ภายนอกใช้จริง

## 10. ข้อสรุปและเกณฑ์ก่อนเข้าสู่ภาคสนาม

V0.3.1 ผ่าน internal engineering audit รอบนี้ในด้าน source-level tests, exact-rational candidate checks, rational lattice relation, และ upper-bound enclosure ตามสมมติฐานที่ประกาศไว้ ผล synthetic pipeline ทั้งสองกรณีสามารถตรวจ feasibility ได้ แต่ยังมี gap จาก UB และไม่ได้พิสูจน์ optimality

**สิ่งที่ต้องทำต่อก่อน field trial:**

1. ส่ง proof และ implementation ให้ผู้เชี่ยวชาญคณิตศาสตร์/geometry ตรวจอิสระ
2. กำหนด CRS ในหน่วยเมตรและจัดทำ survey protocol สำหรับ FTS-01
3. เก็บ boundary, obstacle, entrance, slope และ independent checkpoints
4. จัดทำ uncertainty budget พร้อมหลักฐานแหล่งที่มา ไม่กำหนดค่าเผื่อโดยคาดเดา
5. ให้ผู้เชี่ยวชาญเกษตรตรวจ Crop Profile และข้อจำกัดเชิงปฏิบัติ
6. เชื่อม Engine V0.3.1 เข้ากับ app ผ่าน interface contract และทดสอบบนอุปกรณ์จริง
7. ทำ field validation โดยเทียบจุดที่ระบบเสนอ กับการวัดภาคสนามที่เป็นอิสระ

**คำตัดสิน:** V0.3.1 เป็น milestone วิศวกรรมภายในที่ตรวจสอบซ้ำได้ ไม่ใช่ผลิตภัณฑ์พร้อมใช้งานจริง และไม่ใช่หลักฐานว่าผลงานชนะการแข่งขันระดับประเทศแล้ว
