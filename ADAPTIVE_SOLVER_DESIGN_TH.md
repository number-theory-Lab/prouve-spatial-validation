# PROUVÉ Spatial — Adaptive Solver Architecture V0.1

## 1. Design principle

V0.3 ใช้ deterministic finite grid เป็น baseline และเรียกวิธีวิจัยเพิ่มเมื่อ geometry complexity และเวลาที่เหลือเหมาะสม ไม่บังคับใช้ solver เดียวกับทุกแปลง

## 2. Complexity features

คำนวณก่อนเลือกวิธี:

- จำนวน connected polygon components
- จำนวน holes
- จำนวน boundary edges
- จำนวน obstacle features
- usable area ต่อ bounding-box area (occupancy ratio)
- aspect ratio ของ bounding box
- estimated lattice-index envelope sites

ฟีเจอร์เหล่านี้เป็น heuristic สำหรับ scheduling ไม่ใช่หลักฐานความยากเชิงคณิตศาสตร์

## 3. Search stages

### Stage A — Grid incumbent

- กำหนด maximum layout evaluations และ phase divisions cap
- เลือกจำนวน phase divisions และ angle count ให้ไม่เกิน budget
- ตรวจเวลาใน loop เพื่อหยุดได้
- ผลที่ได้เป็น best-found ใน finite grid เท่านั้น

### Stage B — Fixed-orientation Phase Arrangement

เรียกเมื่อ edge count และ estimated lattice sites อยู่ใต้ configured caps และยังมีเวลา

- ใช้ orientation ที่ grid พบดีที่สุด
- จำกัด boundary fragments และ lattice-index sites
- มี time-budget guard ใน arrangement loops
- แปลง centered phase กลับเป็น global local-XY phase
- สร้าง layout กลับด้วย production enumerator
- หากจำนวนไม่ตรงกัน ให้ HOLD candidate นั้นและเก็บ grid incumbent
- Topology ยังอิง Shapely/GEOS floating representation; ไม่ใช้เป็น exact proof

### Stage C — Orientation/Phase BnB

เรียกเมื่อ geometry และ index envelope ไม่เกิน cap และยังมีเวลา

- จำกัด max nodes และ wall-time
- ผล BnB เป็น numerically conservative research result ไม่ใช่ formal continuous proof
- แปลง phase กลับ global local-XY แล้ว re-evaluate ด้วย production enumerator
- หาก count ไม่ตรงให้ HOLD candidate

## 4. Candidate selection

เลือกจำนวนจุดสูงสุดเฉพาะใน candidates ที่สร้างกลับแล้ว count ตรงกัน จากนั้น:

1. สร้าง rational orthogonal lattice จาก rational rotation parameter
2. ตรวจ lattice indices, basis lengths, orthogonality และ coordinates แบบ exact
3. ตรวจ source constraints แบบ exact-rational
4. ตรวจ candidate points อยู่ใน represented usable polygon แบบ exact-rational
5. คำนวณ certified upper bound ที่ scope เดียวกัน

ถ้า upper bound ต่ำกว่า feasible lower bound ให้ HOLD conflict; ถ้าเท่ากันจึงมี optimum ภายใน declared lattice family/represented usable polygon; ถ้าสูงกว่าให้แสดง gap

## 5. Budget behavior

Budget แยกเป็น:

- `max_wall_time_seconds`
- `max_grid_evaluations`
- `arrangement_max_fragments`
- `arrangement_max_sites`
- `bnb_max_nodes`
- `bnb_max_sites`

Time guard ใน Stage A, B และ C เป็น best-effort ภายในขั้นตอนปฏิบัติการของ Python/GEOS; เวลา wall-clock รวมอาจเกิน budget เล็กน้อยจาก operation ที่ไม่สามารถยกเลิกกลางคำสั่ง GEOS ได้ จึงต้องรายงาน `elapsed_seconds` จริง

## 6. Fallback policy

- Grid เป็น incumbent เสมอหากได้ผลอย่างน้อยหนึ่ง layout
- Arrangement/BnB error, timeout, complexity cap หรือ count mismatch ไม่ทำให้ pipeline ล้มทั้งชุด
- Candidate ที่ไม่ผ่าน exact feasibility จะไม่ถูกเลือก
- หากไม่มี feasible candidate ที่ cert ผ่าน ให้ output สถานะ HOLD

## 7. ข้อจำกัด

- V0.3 ใช้ rectangular crop-row lattice ใน adaptive production path
- Phase Arrangement เป็น fixed-orientation only
- BnB ใช้ floating interval heuristics; ไม่ถือเป็น formal proof
- Synthetic benchmark ไม่รับประกันเวลาบนแปลงจริงหรืออุปกรณ์มือถือ
- `selected_method` คือวิธีที่ให้จำนวนสูงสุดใน candidate ที่ได้ทดสอบและ verify ไม่ได้หมายความว่าเป็นวิธีที่ดีที่สุดในทุก input
