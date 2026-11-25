# CRS North-Hemisphere Guard - Regression Plan
Date: 25 November 2026
Repository branch: fix/crs-utm-north-latitude-guard-2026-11-25

## Change
The app's WGS84-to-UTM guard now rejects non-finite longitude/latitude and restricts latitude to 0..84 degrees north. This matches the supported target CRSs EPSG:32647 and EPSG:32648 (UTM northern hemisphere). The supported longitude ranges remain zone 47 [96,102) and zone 48 [102,108); longitude 102 belongs to zone 48.

## Deterministic regression cases
| Input (lon, lat) | Zone | Expected |
|---|---:|---|
| (100.0, 7.0) | 47 | Accept |
| (103.0, 7.0) | 48 | Accept |
| (102.0, 7.0) | 48 | Accept |
| (102.0, 7.0) | 47 | Reject |
| (100.0, -0.0001) | 47 | Reject |
| (100.0, 0.0) | 47 | Accept |
| (100.0, 84.0) | 47 | Accept |
| (100.0, 84.0001) | 47 | Reject |
| (95.999, 7.0) | 47 | Reject |
| (108.0, 7.0) | 48 | Reject |
| (NaN, 7.0) | 47 | Reject |
| (100.0, Infinity) | 47 | Reject |

## Scope and limitations
- This guard does not establish GNSS, imagery, cadastral-boundary, or survey accuracy.
- EPSG:32747/32748 are not supported by this branch.
- CRS parity already tested in the local work package is limited to its documented Thailand-like envelope; it does not replace a browser regression test on the deployed app.
- This change is on a separate branch. The published main branch has not been changed or deployed.

## Manual browser gate
1. Open the branch preview or run the branch locally.
2. Import or enter each test pair through the geographic-coordinate path.
3. Record actual accept/reject outcome and console errors.
4. Confirm no project state is marked verified after a rejected input.
5. Only merge after a reviewer verifies all boundary cases.
