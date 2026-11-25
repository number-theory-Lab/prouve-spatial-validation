# Literature and Novelty Note — Engine Branch V0.3

**สถานะ:** Research caution note; ไม่ใช่ systematic literature review และไม่ใช่การรับรอง novelty

## 1. สิ่งที่ V0.3 ทำได้จริง

V0.3 รวมองค์ประกอบที่เป็นแนวคิดมาตรฐานใน computational geometry, exact arithmetic, lattice geometry และ optimization เข้ากับ pipeline เฉพาะของ PROUVÉ Spatial:

- rational point-in-polygon และ squared-distance comparisons;
- topology checks สำหรับ polygon shells, holes และ MultiPolygon;
- rational orthogonal lattice reconstruction;
- fundamental-cell / Steiner-type lattice upper bound;
- finite grid search, phase arrangement และ orientation/phase branch-and-bound;
- adaptive method gating, fallback, candidate reconciliation และ evidence reporting.

การนำแนวคิดเหล่านี้มาประกอบกันใน branch นี้เป็น engineering/research integration contribution ที่ผ่าน tests ตามขอบเขตที่ระบุ ไม่ใช่หลักฐานว่ามีทฤษฎีคณิตศาสตร์ใหม่หรืออัลกอริทึมใหม่ในระดับสากล

## 2. ข้ออ้างที่รองรับได้

สามารถกล่าวได้ว่า V0.3:

- มี verifier ที่ใช้ rational arithmetic ตัดสิน feasibility ของจุดต่อ canonical decimal representation ที่รับเข้า;
- รองรับ Polygon holes และ MultiPolygon ที่ components disjoint/non-touching ภายใน scope ที่ทดสอบ;
- สร้าง rational orthogonal lattice relation certificate และตรวจ source/usable geometries แยกกัน;
- คำนวณ rational certified upper bound สำหรับ declared rectangular lattice family บน decimalized represented usable geometry;
- เลือก Grid/Arrangement/BnB แบบ heuristic พร้อม caps, fallback และ re-evaluation;
- ส่งออก Evidence JSON/CSV และมี offline viewer prototype.

## 3. ข้ออ้างที่ยังไม่รองรับ

ยังห้ามกล่าวว่า:

- พบ theorem ใหม่หรืออัลกอริทึมใหม่โดยไม่มี systematic prior-art review;
- เป็น continuous/global optimizer สำหรับทุก orientation/phase;
- BnB มี rigorous interval proof;
- Geometry Engine offsets/buffers เป็น exact construction — buffers/differences ใช้ GEOS floating representation;
- certificate รับรอง CRS, datum, source imagery, cadastral truth หรือ survey accuracy;
- ผ่านการใช้งานจริงหรือเหมาะกับพืช/ผลผลิตโดยผู้เชี่ยวชาญแล้ว;
- viewer เป็น app release หรือผ่าน real-device usability.

## 4. สิ่งที่ต้องทำด้านวรรณกรรม

ก่อนประกาศ novelty ต้องค้นและจัดตารางเปรียบเทียบงานเดิมด้าน:

1. exact point-in-polygon / robust predicates / rational geometry;
2. polygonal offsets, Minkowski sums, medial-axis/clearance methods;
3. lattice packing bounds และ parallel-body / Steiner formulas;
4. fixed-orientation phase arrangements และ translation spaces;
5. continuous lattice optimization, branch-and-bound และ certified interval arithmetic;
6. spatial crop-layout / agricultural field planning systems.

ต้องบันทึกฐานข้อมูล วันที่ค้น คำค้น inclusion/exclusion criteria และ claim-to-source mapping พร้อมให้ผู้เชี่ยวชาญตรวจทาน ข้อความนี้ยังไม่ได้อ้างว่าการค้นดังกล่าวเสร็จแล้ว
