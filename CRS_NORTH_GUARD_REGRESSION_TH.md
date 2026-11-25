# PROUVÉ Spatial CRS Guard Patch — Main Branch
Date: 25 November 2026

## Change committed
The WGS84-to-UTM transform in `index.html` now:
- rejects non-finite longitude and latitude values;
- restricts latitude to 0..84 degrees north for the supported UTM North target CRSs EPSG:32647 and EPSG:32648;
- retains zone 47 longitude range [96,102) and zone 48 range [102,108).

## JavaScript runtime regression
The exact guard and forward-transform function body were exercised in Node.js against 12 deterministic cases:
- zone 47 and 48 valid coordinates;
- longitude 102.0 assigned to zone 48 and rejected in zone 47;
- negative latitude rejected;
- equator and 84 degrees north accepted;
- latitude above 84 rejected;
- longitude outside each zone rejected;
- NaN longitude and infinite latitude rejected.

Result: 12/12 passed in Node.js.

## Scope
This is a JavaScript runtime regression, not a full-page Chromium browser test. The local browser launch was blocked by the execution environment. Actual Android/tablet browser and live map/device tests remain NOT RUN. The patch does not certify GNSS, imagery, cadastral, boundary, or field positional accuracy.
