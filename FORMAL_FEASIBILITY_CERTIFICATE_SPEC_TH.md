# PROUVÉ Spatial — Formal Feasibility Certificate V0.1

## 1. วัตถุประสงค์และขอบเขต

`engine/formal_feasibility_certificate.py` ตรวจว่าชุดตำแหน่งปลูกที่ส่งเข้ามา **แต่ละจุด** เป็นไปตามข้อจำกัดเรขาคณิตที่ประกาศไว้หรือไม่ โดยใช้ rational arithmetic สำหรับ topology และระยะห่าง

Certificate นี้ตอบคำถามว่า:

> “จุดที่ส่งมาตรวจ อยู่ในพื้นที่ที่อนุญาต และมีระยะจากขอบเขต/สิ่งกีดขวางไม่น้อยกว่าค่าที่กำหนดหรือไม่ ภายใต้พิกัดและระยะเผื่อที่ serialize มา?”

Certificate นี้ **ไม่ตอบ** ว่าแผนดีที่สุดหรือไม่ ไม่ตรวจความจริงของการสำรวจ ไม่รับรอง CRS/datum และไม่ตัดสินความเหมาะสมของพืช

## 2. รูปแบบ Geometry ที่รองรับ

รับ GeoJSON `Polygon` และ `MultiPolygon` รวม interior rings (holes)

- Ring ต้องปิดอย่างชัดเจน: จุดแรกเท่ากับจุดสุดท้าย
- Ring ต้องมีจุดยอดที่แตกต่างกันอย่างน้อย 3 จุด
- Ring ต้องไม่ self-intersect หรือ self-touch และไม่มี edge ซ้อนกลับ
- Hole ต้องอยู่ภายใน exterior ring โดยไม่แตะหรือข้าม
- Hole ต้องไม่ทับ ซ้อน หรือแตะ hole อื่น
- MultiPolygon components ต้องไม่แตะหรือข้ามกัน และ interior ต้องไม่ทับกัน

เพื่อหลีกเลี่ยงการตีความ topology กำกวม MultiPolygon ที่ component แตะกันจะถูก HOLD/ปฏิเสธ ไม่ normalize ให้เงียบ ๆ

## 3. การแทนค่าตัวเลข

- Integer และ decimal string ถูกแปลงเป็น `fractions.Fraction` แบบตรงตัว
- Finite float แปลงจาก shortest round-trip decimal string เช่น float `0.1` ถูกตีความเป็น rational `1/10`
- NaN, Infinity, boolean และ null ถูกปฏิเสธ
- การตัดสิน inside/outside, boundary และ squared distance ใช้ rational arithmetic ไม่มี epsilon

ดังนั้น certificate มีความหมายว่า “ถูกต้องแบบ exact เมื่อเทียบกับ canonical decimal representation ของ input ที่ serialize มา” ไม่ได้หมายความว่าค่าพิกัดที่วัดจากพื้นดินไม่มีความคลาดเคลื่อน

## 4. การตรวจจุดใน Ring

ใช้ ray-crossing แบบ exact rational:

1. ตรวจ point-on-segment ก่อน โดยตรวจ cross product เท่ากับศูนย์และอยู่ใน bounding interval
2. สำหรับแต่ละ edge ที่ระดับ y ของจุดตัดผ่านช่วง edge ให้คำนวณ x-coordinate ของจุดตัดรังสีด้วย rational division
3. สลับสถานะ inside เมื่อจุดตัดอยู่ทางขวาของจุดทดสอบ

สำหรับ Polygon: จุดต้องอยู่ใน shell และไม่อยู่ใน interior ของ hole; จุดบน ring ถือเป็น boundary
สำหรับ MultiPolygon: จุดต้องอยู่ใน interior หรือ boundary ของ component อย่างน้อยหนึ่งชิ้น

## 5. การตรวจระยะถึง segment โดยไม่ใช้ square root

ให้จุดทดสอบเป็น `P`, segment endpoints เป็น `A,B` และกำหนด

\[
D=B-A,\quad W=P-A,\quad L=D\cdot D,\quad t=W\cdot D.
\]

คำนวณ squared distance:

\[
d^2(P,AB)=
\begin{cases}
W\cdot W, & t\le 0,\\
(P-B)\cdot(P-B), & t\ge L,\\
\dfrac{(D_xW_y-D_yW_x)^2}{L}, & 0<t<L.
\end{cases}
\]

ทุกพจน์เป็น rational เมื่อ input เป็น rational จึงเปรียบเทียบกับระยะกำหนด `c` ได้โดยตรง:

\[
d^2(P,AB)\ge c^2.
\]

ไม่ต้องคำนวณ `sqrt` และไม่มี floating tolerance ในการตัดสิน pass/fail

## 6. เงื่อนไข feasibility

กำหนด:

- `b`: boundary setback
- `u_b`: boundary uncertainty allowance ที่ผู้ใช้/ผู้เชี่ยวชาญระบุ
- `o`: obstacle clearance
- `u_o`: obstacle uncertainty allowance ที่ผู้ใช้/ผู้เชี่ยวชาญระบุ

ระยะที่ใช้ตรวจคือ:

\[
b_{eff}=b+u_b,\qquad o_{eff}=o+u_o.
\]

สำหรับทุก candidate point `P`:

1. `P` ต้องอยู่ใน field Polygon/MultiPolygon และไม่อยู่ใน hole
2. ระยะต่ำสุดจาก `P` ถึงทุก boundary ring ต้องไม่น้อยกว่า `b_eff`
3. `P` ต้องไม่อยู่ใน interior ของ obstacle ใด
4. ระยะต่ำสุดจาก `P` ถึงทุก ring ของ obstacle ต้องไม่น้อยกว่า `o_eff`
5. หากระบุ `minimum_spacing_m` จะตรวจทุกคู่โดย exact squared-distance comparison

ระบบไม่ประเมิน uncertainty ให้เอง ค่า uncertainty ที่ไม่ส่งมาจะเป็นศูนย์ตาม schema; การใช้กับข้อมูลจริงจึงต้องผ่าน gate ที่ยืนยันว่า uncertainty calibration และค่าระยะเผื่อได้รับการอนุมัติแล้ว

## 7. Rational lattice relation

`engine/lattice_relation_certificate.py` แปลงมุมที่ได้จาก floating search เป็น rational rotation parameter `q` โดยใช้

\[
\cos\theta_q=\frac{1-q^2}{1+q^2},\qquad
\sin\theta_q=\frac{2q}{1+q^2}.
\]

จึงมี identity แบบ exact:

\[
\cos^2\theta_q+\sin^2\theta_q=1.
\]

สำหรับ rectangular lattice:

\[
A=(a\cos\theta_q,a\sin\theta_q),\quad
B=(-b\sin\theta_q,b\cos\theta_q).
\]

ได้ `A·B=0`, `|A|=a`, `|B|=b` แบบ exact rational จากนั้นสร้างทุกจุดจาก integer indices และ rational phases เดียวกัน และตรวจย้อนกลับทุกจุด

มุม `theta_source_deg_display_only` เป็นค่าจาก floating search เพื่อบอกที่มา; มุมที่ใช้ใน lattice certificate คือ rational rotation ที่นิยามจาก `q` ซึ่งอาจต่างจากมุมแสดงผลเล็กน้อย จุดที่สร้างใหม่ต้องผ่าน source-geometry และ usable-geometry feasibility certificate จึงจะถูกยอมรับ

## 8. การเชื่อมกับ Certified Upper Bound

`certified_upper_bound_v03.py` คำนวณ upper bound ของ rectangular lattice family เหนือ decimalized represented usable polygon ด้วย rational area/perimeter/radius enclosures

หาก:

- rational lattice relation ผ่าน
- ทุก candidate point ผ่าน source-constraint feasibility
- ทุก candidate point ผ่าน membership ใน represented usable polygon
- upper bound ผ่านและนับอยู่ใน lattice family เดียวกัน

จึงมี lower bound จากจำนวนจุดที่รับรองแล้ว และ upper bound จาก packing proof หากจำนวนทั้งสองเท่ากัน สามารถประกาศ optimum ได้ **เฉพาะภายใน rectangular lattice family และ represented usable geometry ที่ระบุ**

หาก upper bound มากกว่า best found ให้รายงาน gap และห้ามเรียก optimum

## 9. Hash และการทำซ้ำ

Certificate สร้าง SHA-256 สำหรับ normalized source geometry และ candidate set เพื่อระบุ bytes/ข้อมูลที่ตรวจจริง การแก้ geometry, points หรือ margins ต้องสร้าง certificate ใหม่

## 10. ข้อจำกัดที่ยังเหลือ

- ไม่ตรวจ CRS, datum, georeferencing หรือ survey accuracy
- ไม่สร้าง uncertainty จาก RMSE หรือโทรศัพท์ GPS; uncertainty ต้องถูกกำหนดจากงาน calibration และผู้เชี่ยวชาญ
- MultiPolygon components ที่แตะกันถูกปฏิเสธ
- Pairwise spacing cap ป้องกันงาน O(n²) ที่ใหญ่เกินไป; เมื่อเกิน cap จะ HOLD ไม่ certify
- Exact feasibility ของชุดจุดไม่ได้พิสูจน์ว่าค้นหาพบตำแหน่งทั้งหมด; optimality ต้องใช้ matching certified upper bound
- ไม่มีการรับรอง yield, plant health, root competition, irrigation, machine access หรือความเหมาะสมทางเกษตร
