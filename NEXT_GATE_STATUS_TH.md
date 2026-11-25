# PROUVÉ Spatial — Next Gate Status V0.3

| Gate | สถานะ | หลักฐาน/งานคงเหลือ |
|---|---|---|
| G1 Exact candidate feasibility | PASS in supported serialized-geometry scope | 12 verifier tests; sample 70/70 and MultiPolygon sample 150/150 |
| G2 Polygon holes / MultiPolygon | PASS in declared topology scope | 4 Geometry Engine topology tests; adapter and pipeline fixtures |
| G3 Rational lattice relation | PASS in declared rectangular lattice scope | exact orthogonal rational basis, lengths and unique indices |
| G4 Certified upper bound | IMPLEMENTED / TESTED | rational Steiner enclosure over decimalized represented usable geometry; examples still have positive optimality gaps |
| G5 Adaptive solver | IMPLEMENTED / EXPERIMENTAL | Grid incumbent/fallback; Arrangement/BnB gated and reconciled; BnB remains numerical research prototype |
| G6 App Result & Evidence Viewer | PROTOTYPE READY | offline HTML; no merge, device/browser/accessibility test pending |
| G7 Independent review | OPEN | independent review of proof, exact-topology implementation, assumptions, and source hashing |
| G8 CRS/survey/uncertainty | NOT STARTED FOR FTS-01 | needs surveyed boundary, obstacles, independent checkpoints, GNSS/source logs and uncertainty approvals |
| G9 Crop profile and agronomy | PENDING | crop species, spacing, access and buffer parameters need expert approval |
| G10 Farmer usability / app acceptance | NOT STARTED | real-device browser tests, user task studies and operational feedback |
| G11 Field deployment | BLOCKED | `field_deployment_authorized=false`; no field recommendation from synthetic fixtures |

## Exit criteria for next branch

1. Independent review of rational feasibility certificate and rational lattice construction.
2. Define a robust geometry serialization contract (CRS, units, coordinate quantization, topology, source provenance).
3. Decide whether GEOS buffer representation is acceptable or whether certified offset construction is required for the deployment use case.
4. Add directed-rounding / interval methods for BnB before any continuous proof claim.
5. Browser/device acceptance and schema validation of the result viewer before app integration.
6. Complete R7 field survey and uncertainty calibration gates for FTS-01.
7. Obtain agronomist-reviewed crop profile and operating clearances.
