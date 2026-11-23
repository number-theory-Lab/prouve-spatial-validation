# PROUVÉ Spatial — Validation Log (2026-11-23)

> Scope: Development Copy only. This is a record of preliminary validation evidence, not a release declaration.
> Research Baseline V0.4.1 and the original V0.5.2 release are not modified by this log.

## Current implementation reference

- Development repository: `number-theory-Lab/prouve-spatial-validation`
- Development site: https://number-theory-Lab.github.io/prouve-spatial-validation/
- Latest application change reviewed: [`5835176` — Add farmer-facing delete boundary control](https://github.com/number-theory-Lab/prouve-spatial-validation/commit/583517640473e745126c223e25d1c9908390eba8)
- Latest application change modifies `index.html`; the service worker file `sw.js` was not changed by that commit.
- The interface still identifies itself as experimental version 0.5.2. No V0.5.3 release is declared.

## Evidence recorded from real-device use

Device and environment reported by the user: Android Samsung tablet; browser/site served over HTTPS.

| Test | Result | Evidence / qualification |
|---|---|---|
| Open HTTPS development site | Preliminary pass | User opened the site on the Android device. |
| Display and zoom the Leaflet map | Preliminary pass | User confirmed the map appeared and zoom worked. |
| Retain project name after online reload | Preliminary pass | User confirmed the project name remained. |
| Re-open the app in airplane mode | Preliminary pass | User confirmed the app reopened offline. This is not a first-install/empty-cache test. |
| Retain project name after offline reload | Preliminary pass | User confirmed the name remained in airplane mode. |
| Import and display synthetic GeoTIFF | Preliminary pass | Synthetic test raster displayed and could be zoomed. It is not real field imagery. |
| Retain synthetic GeoTIFF after online reload | Preliminary pass | User confirmed the overlay remained. |
| Retain synthetic GeoTIFF after offline reload | Preliminary pass | User confirmed the overlay remained in airplane mode. This validates persistence of a previously imported local overlay, not offline basemap tile availability. |
| Delete a drawn boundary using the main farmer-facing control | Preliminary pass | User directly tested the new red “ลบพื้นที่ที่วาด” control and confirmed deletion worked. |

All entries above are user-reported device results. They are not automated test results or independent accuracy measurements.

## Static code review notes

### Delete-boundary control

The latest change exposes a delete action in the main farmer-facing drawing controls. It is disabled when there are no source vertices and asks for confirmation before clearing the boundary. The clear handler resets the drawn/source vertices and associated survey/confirmation state, records the edit, renders the updated project, and displays a message that the map background and imported GeoTIFF remain.

The handler also calls the farmer summary update. Static inspection confirms the button, confirmation text, disabled-state update, and event wiring are present in the current `main` branch.

Not yet device-tested: cancelling the confirmation, deleting while a local GeoTIFF overlay is active, undo/recovery after deletion, and persistence of the deleted state after reload.

### Offline behaviour

The current service worker (`sw.js`) caches the app shell: `index.html`, the manifest, and app icons.

- Leaflet JavaScript/CSS are cached on demand after successful online requests.
- GeoTIFF and projection libraries are cached on demand after successful online requests.
- The external basemap tile services are not included in the service-worker cache list.
- A first-time offline visit on a device with no existing app-shell/library cache is not proven and is not expected to work reliably.
- A previously imported local GeoTIFF Field Pack is stored separately in IndexedDB and can be restored as a local image overlay.

Therefore, current offline evidence supports reopening a previously cached app and restoring previously saved project/Field Pack data. It does not establish offline access to fresh satellite imagery or map tiles.

### GeoTIFF Field Pack limitations found in code

The browser workflow converts the imported GeoTIFF into a PNG overlay for map display and saves a Field Pack. The manifest explicitly notes that the original GeoTIFF is not retained inside the Field Pack. The renderer limits the output to 1536 pixels per side and the generated PNG to 20 MB; the Field Pack JSON is limited to 35 MB.

The current declared support is limited to unrotated GeoTIFFs using EPSG:4326, EPSG:32647, EPSG:32648, or EPSG:3857, with required georeferencing tags. Rotation/ModelTransformation, GCP/RPC, complete NoData masking, and complex multiband/multipage selection remain unsupported or limited. A visually clear overlay is not evidence of positional accuracy.

## Tests still pending

1. Test delete confirmation cancellation: the boundary must remain unchanged.
2. Test confirmed deletion while a previously imported local GeoTIFF overlay is visible: only the boundary and its vertices should disappear; the overlay should remain.
3. Check that the delete button becomes disabled after deletion and becomes enabled again after a new boundary is drawn.
4. Reload after deletion (online, then offline where possible) and confirm the deleted boundary does not reappear.
5. Test undo/recovery after deletion, if the advanced undo control is part of the intended user workflow.
6. Test export and re-import of a Field Pack backup, including offline display on the same device.
7. Test GeoTIFF from a real target field, checking metadata, control points, and alignment against independent GNSS/GPS measurements. Do not use a synthetic raster to claim field accuracy.
8. Test a fresh browser profile/device with no prior cache if first-use offline setup is a required product capability.
9. Decide and document whether offline basemap tiles are a product requirement. If yes, design a lawful, bounded tile/area-pack workflow with attribution, storage limits, and explicit coverage before implementing it.

## Code-level smoke checks performed during review

After the validation log was committed, the current `index.html` and `sw.js` were fetched again from the Development Copy and checked:

- The single inline application JavaScript block parses successfully.
- The service-worker JavaScript parses successfully.
- No duplicate static HTML `id` attributes were found.
- The farmer-facing delete button, its click listener, its no-boundary disabled state, and its confirmation prompt are present.
- The app-shell and on-demand geospatial library cache entries are present in the service worker.
- No external basemap tile cache rule was found.
- GitHub returned no commit status checks for the application change; this is not evidence of a passing CI pipeline.

These are static/code-level checks only. They do not simulate a browser, device storage, touch interaction, real imagery alignment, or actual offline network behaviour.

## Gate status

- Synthetic/demo and preliminary real-device evidence: recorded above.
- Real-field imagery and positional-accuracy validation: **pending**.
- Fresh-install offline validation: **pending**.
- Full offline basemap-tile availability: **not implemented / not validated**.
- Pre-Validation Gate: **NOT PASSED**.
- V0.5.3: **NOT DECLARED**.

This log may be updated when further evidence is collected. Do not change a pending item to pass without recording the test conditions and observed result.
