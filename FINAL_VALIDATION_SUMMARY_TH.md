# Final Validation Summary — Engine Branch V0.3

**วันที่:** 25 พฤศจิกายน 2569

## 1. Automated tests

- Combined test suite: **93/93 PASS**
- Latest measured runtime: **6.274 s**
- Test log: `reports/all_tests_v0_3.log`
- HTML viewer inline JavaScript syntax: PASS via `node --check`

## 2. CLI pipeline runs

### Rectangular synthetic fixture

- Run ID: `8400f95860bde1c2`
- Pipeline: `SYNTHETIC_PIPELINE_PASS_FEASIBILITY_CERTIFIED_EXPLORATORY_ONLY`
- Best found: 70
- Certified upper bound: 77
- Gap: 9.09%
- Source/usable feasibility: PASS
- Optimality: not proven
- Field deployment: unauthorized
- Evidence: `reports/v0_3_release_validation/evidence_report.json`

### MultiPolygon with hole and obstacle

- Run ID: `9848599d9ca1418b`
- Pipeline: `SYNTHETIC_PIPELINE_PASS_FEASIBILITY_CERTIFIED_EXPLORATORY_ONLY`
- Best found: 150
- Certified upper bound: 209
- Gap: 28.23%
- Source/usable feasibility: PASS
- Optimality: not proven
- Field deployment: unauthorized
- Evidence: `reports/multipolygon_hole_release_validation/evidence_report.json`

## 3. Correct interpretation

The formal feasibility certificate is exact with respect to the canonical decimal representation of submitted geometry, candidate points, and declared margins. It does not validate the source survey, CRS/datum, positional accuracy, physical boundary, crop suitability or field operations.

The upper bound is for the declared rectangular lattice family over the decimalized represented usable geometry. Both example runs have positive gaps, so neither is certified optimal.

## 4. Release disposition

V0.3 is a research/development candidate. It is not merged into app V0.5.2, not published to GitHub, and not authorized for FTS-01 field recommendations.
