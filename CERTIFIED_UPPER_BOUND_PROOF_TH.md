# PROUVÉ Spatial — Certified Lattice Upper Bound

**Engine Branch:** V0.2  
**สถานะ:** คำอธิบายเชิงพิสูจน์สำหรับ upper bound ของ lattice family ที่ระบุ — ไม่ใช่ใบรับรองว่าแผนที่ค้นพบเป็น optimum  
**ขอบเขต:** rectangular/square lattice ที่มุมฐาน 90° และ triangular lattice ที่มุมฐาน 60°

## 1. ปัญหาที่ต้องการจำกัด

ให้ \(U\subset\mathbb{R}^2\) เป็นพื้นที่รูปหลายเหลี่ยมที่ใช้ได้ตาม geometry engine และให้ lattice มีเวกเตอร์ฐาน \(a,b\) ซึ่งไม่ขนานกัน จุด lattice มีรูป

\[
\Lambda=\{j a+i b: i,j\in\mathbb{Z}\}.
\]

เราต้องการหาจำนวนจุด lattice ที่อยู่ใน \(U\) เมื่อเลื่อน phase และหมุน lattice ได้ โดยต้องการค่า integer \(N_{UB}\) ที่รับประกันว่า

\[
\#( (t+R_\theta\Lambda)\cap U)\le N_{UB}
\]

สำหรับทุก translation \(t\) และทุก orientation \(\theta\) ใน lattice family ที่กำหนด

## 2. สร้าง fundamental cell รอบแต่ละจุด

กำหนด fundamental parallelogram ที่มีจุด lattice เป็นศูนย์กลาง

\[
C=\{s a+u b:-\tfrac12\le s,u\le\tfrac12\}.
\]

เซลล์ \(q+C\) เมื่อ \(q\) วิ่งผ่าน lattice จะปูระนาบโดยมีส่วนทับซ้อนกันเฉพาะขอบที่มีพื้นที่เป็นศูนย์ และแต่ละเซลล์มีพื้นที่เท่ากับ determinant ของ lattice:

\[
A_C=|\det(a,b)|.
\]

ให้ \(R_C\) เป็นระยะไกลสุดจากศูนย์กลางของเซลล์ถึงมุมเซลล์ ในกรณีฐาน 90° และ 60° ได้

- **ฐาน 90°** (rectangular/square):
  \[
  R_C=\frac12\sqrt{a^2+b^2},\qquad A_C=ab.
  \]
- **ฐาน 60°** (triangular):
  \[
  R_C=\frac12\sqrt{a^2+b^2+ab},\qquad
  A_C=\frac{\sqrt3}{2}ab.
  \]

ดังนั้นทุกเซลล์อยู่ภายใน disk รัศมี \(R_C\) รอบจุด lattice ของเซลล์นั้น

## 3. ใช้ convex hull และ Steiner formula

สมมติว่ามีจุด lattice ที่ยอมรับได้จำนวน \(N\) จุด ซึ่งทุกจุดอยู่ใน \(U\) เซลล์ทั้ง \(N\) จึงอยู่ภายใน parallel body

\[
\operatorname{conv}(U)\oplus B(R_C),
\]

โดย \(\operatorname{conv}(U)\) คือ convex hull ของพื้นที่ใช้ได้ และ \(B(R_C)\) คือ disk รัศมี \(R_C\)

เพราะเซลล์ภายในไม่ทับซ้อนกันและแต่ละเซลล์มีพื้นที่ \(A_C\)

\[
N A_C\le
\operatorname{Area}(\operatorname{conv}(U)\oplus B(R_C)).
\]

สำหรับ convex polygon ใช้ Steiner formula:

\[
\operatorname{Area}(K\oplus B(R))=A(K)+P(K)R+\pi R^2,
\]

เมื่อ \(A(K)\) คือพื้นที่ convex hull และ \(P(K)\) คือเส้นรอบรูป ดังนั้น

\[
N\le
\frac{A_H+P_HR_C+\pi R_C^2}{A_C}.
\]

สูตรนี้อาจหลวมเมื่อ \(U\) เว้า มีรู หรือมีหลาย component เพราะ convex hull เติมบริเวณที่ไม่ใช่พื้นที่ใช้ได้ แต่ยังเป็นขอบเขตบนที่ถูกต้องสำหรับกรอบสมมติฐานข้างต้น

## 4. ทำให้การคำนวณเป็น rational outward bounds

ไฟล์ `engine/certified_upper_bound.py` ไม่ใช้ GEOS buffer/area ในการคำนวณ certificate โดยตรง แต่ดึงพิกัดจุดยอดของ polygon ที่ส่งเข้ามา แล้วทำดังนี้

1. แปลง floating-point coordinates และ spacing เป็น `Fraction` ซึ่งแทนค่าบิตไบนารีของอินพุตที่ได้รับอย่างตรงตัว
2. คำนวณ convex hull และพื้นที่ด้วย rational arithmetic / shoelace formula
3. คำนวณความยาวแต่ละด้านด้วย rational square-root upper bound โดย integer arithmetic ที่ scale \(10^{12}\) แล้วรวมเป็น \(P_H^{upper}\)
4. ใช้ \(355/113\) เป็น rational upper bound ของ \(\pi\)
5. สำหรับ triangular lattice ใช้ rational lower bound ของ \(\sqrt3\) เพื่อไม่ให้พื้นที่ cell ต่ำกว่าค่าจริงที่แท้จริง
6. ได้ rational quotient upper bound \(Q^{upper}\) และคืนค่า
   \[
   N_{UB}=\lfloor Q^{upper}\rfloor.
   \]
   เนื่องจากจำนวนจุดเป็นจำนวนเต็มและ \(N\le Q^{upper}\) จึงได้ \(N\le\lfloor Q^{upper}\rfloor\)

ค่า exact fractions ถูกเก็บไว้ใน JSON (`exact_area_upper_fraction`, `exact_cell_area_lower_fraction`, `exact_quotient_fraction`) เพื่อให้ตรวจย้อนกลับได้

## 5. ความหมายของคำว่า certified ใน branch นี้

คำว่า `CERTIFIED_RATIONAL_STEINER_ENCLOSURE` หมายถึง **การคำนวณ integer upper bound ถูกครอบด้วย rational outward bounds ภายใต้ polygon vertices และ spacing ที่แทนอยู่ในไฟล์** เท่านั้น

ยังไม่ใช่การรับรองสิ่งต่อไปนี้:

- ความถูกต้องทางสำรวจของขอบเขตสวนหรือสิ่งกีดขวางต้นทาง
- ความถูกต้องแบบ exact-real ของ polygon ที่ GEOS สร้างจาก buffer/overlay
- ความเป็นไปได้ของ candidate layout ที่สร้างด้วย floating-point ทั้งหมดแบบ exact geometry
- การพิสูจน์ว่า best-found candidate มีจำนวนจุดเท่ากับ upper bound
- ความเหมาะสมทางเกษตร ผลผลิต สุขภาพพืช ทางเดินเครื่องจักร หรือการให้น้ำ

เพราะฉะนั้นแม้ `best_found_count == upper_bound_count` ใน V0.2 ก็ยังไม่อนุญาตให้แสดงว่า optimum ถูกพิสูจน์แล้ว หากยังไม่มี formal candidate-feasibility certificate เพิ่มเติม

## 6. ผลทดสอบที่มีใน V0.2

- baseline synthetic fixture: certified UB = 77, best found = 63
- ทดสอบ translation/orientation แบบสุ่ม 350 ชุด: count ไม่เกิน certified UB ทุกชุด
- square และ triangular lattice: ผ่านชุดทดสอบ bound
- MultiPolygon และ polygon ที่มี hole: ผ่านการสร้าง bound
- empty geometry: certified upper bound = 0

การทดสอบเหล่านี้เพิ่มความมั่นใจใน implementation แต่ไม่แทนที่การทบทวนพิสูจน์โดยผู้เชี่ยวชาญหรือ formal verification อิสระ

## 7. ข้อจำกัดของ lattice family

ปัจจุบันรับรองเฉพาะ basis angle 60° และ 90° เท่านั้น หากเพิ่ม lattice ที่มุมอื่น ต้องสร้าง lower bound ของ determinant และ covering radius ที่พิสูจน์ได้สำหรับ basis นั้นก่อน ห้าม fallback ไปใช้สูตรนี้แล้วติดป้าย certified โดยอัตโนมัติ
