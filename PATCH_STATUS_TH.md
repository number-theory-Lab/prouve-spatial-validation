# PROUVÉ Spatial — Patch / Gate Status V0.3

**สถานะ:** Implemented in isolated Engine Branch V0.3; not merged to app/release.

| กลุ่ม | สิ่งที่เพิ่ม/แก้ | หลักฐาน | สถานะ |
|---|---|---|---|
| P0–P10 inherited | เก็บ safety behavior จาก V0.1/V0.2 เช่น best-found vs optimum, bound conflict, empty plan, invalid numeric inputs, boundary semantics และ verifier HOLD | `tests.test_engine_branch`, regression tests | PASS in declared tests |
| FV-01 | Exact-rational point-in-polygon สำหรับ Polygon shell/holes | `test_formal_feasibility_certificate.py` | PASS |
| FV-02 | Exact squared distance point-to-segment ไม่ใช้ sqrt/epsilon ตัดสิน | same test suite | PASS |
| FV-03 | Exact topology checks สำหรับ rings, holes และ disjoint MultiPolygon | same test suite | PASS in supported topology scope |
| FV-04 | ตรวจ candidate กับ source constraints และ represented usable geometry แยก certificate | pipeline fixtures | PASS |
| LR-01 | Rational orthogonal lattice relation, exact basis lengths, unique integer indices | `lattice_relation_certificate.py` tests and pipeline | PASS |
| LR-02 | Pairwise spacing lower bound from orthogonal lattice plus distinct indices | rational lattice certificate | PASS in declared rectangular-lattice scope |
| GE-01 | Geometry Engine accepts GeoJSON Polygon/MultiPolygon with holes and GeoJSON obstacles | `test_geometry_engine_v03_topology.py` | PASS |
| AD-01 | Grid incumbent/fallback; adaptive gating for Arrangement and BnB | `test_adaptive_solver.py` | PASS |
| AD-02 | Candidate reconciliation through production enumerator; mismatch not selected | adaptive solver tests | PASS |
| AD-03 | Time/complexity guards and explicit report of search vs total runtime | pipeline evidence | PASS; best-effort budget only |
| UI-01 | Offline App Result & Evidence Viewer for Evidence JSON/CSV/GeoJSON | static JS syntax + artifact review | Prototype only; browser acceptance pending |
| PIPE-01 | End-to-end handoff → geometry → adaptive optimization → certificates → evidence JSON/CSV | `test_pipeline_runner_v03.py` | PASS on synthetic fixtures |

## Full regression

- Full combined suite: **93/93 PASS** after latest code changes.
- This includes the prior V0.1/V0.2 regression tests and V0.3 formal-feasibility, MultiPolygon/hole, adaptive solver, adapter, and pipeline tests.
- `field_deployment_authorized` remains `false`.

## Important limits

- Certificate applies to canonical decimal serialized geometry/points; it does not certify the physical truth or positional accuracy of survey data.
- Geometry buffer/difference is still produced by Shapely/GEOS; exact certificate checks candidate points against the serialized geometry representations.
- Matching best-found and certified upper bound is required before any optimum claim. Current example runs have positive gaps.
- UI has not been merged into app V0.5.2 or tested on real user devices.
