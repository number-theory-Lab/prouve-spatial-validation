#!/usr/bin/env python3
"""Exact phase-arrangement prototype for a fixed-orientation rectangular lattice.

For a fixed orientation, transform the usable polygon into lattice coordinates.
The phase objective is the coverage multiplicity of the shifted polygon pieces
(P - (j,i)) intersected with the unit phase square [0,1]^2. The multiplicity is
constant on each open face of the boundary arrangement. We evaluate faces,
atomic edge interiors, and vertices, so boundary-only maxima are included under
closed-set `covers` semantics.

This is an exploratory computational-geometry prototype. Its combinatorial
argument is exact for a valid planar arrangement; actual topology is represented
by Shapely floating-point geometry and needs cross-implementation validation.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
import math
import time
import numpy as np
import shapely

from shapely import affinity
from shapely.geometry import Polygon, Point, box, LineString, MultiLineString, GeometryCollection
from shapely.ops import unary_union, polygonize


class PhaseArrangementError(ValueError):
    pass


def _iter_lines(g):
    if g.is_empty:
        return
    if g.geom_type in ("LineString", "LinearRing"):
        yield g
    elif hasattr(g, "geoms"):
        for child in g.geoms:
            yield from _iter_lines(child)


def _collect_boundary_geometries(g):
    """Collect all polygon boundaries and lower-dimensional pieces recursively."""
    if g.is_empty:
        return
    if g.geom_type == "Polygon":
        yield g.boundary
    elif g.geom_type in ("MultiPolygon", "GeometryCollection"):
        for child in g.geoms:
            yield from _collect_boundary_geometries(child)
    else:
        yield g


def _iter_points_from_linework(g):
    for line in _iter_lines(g):
        coords = list(line.coords)
        for a, b in zip(coords, coords[1:]):
            yield ((a[0]+b[0])/2.0, (a[1]+b[1])/2.0)
            yield (a[0], a[1])
            yield (b[0], b[1])


def _iter_isolated_points(g):
    if g.is_empty:
        return
    if g.geom_type == "Point":
        yield (float(g.x), float(g.y))
    elif hasattr(g, "geoms"):
        for child in g.geoms:
            yield from _iter_isolated_points(child)


@dataclass
class PhaseArrangementResult:
    status: str
    theta_deg: float
    max_count: int
    best_phase_a: float
    best_phase_b: float
    phase_pieces: int
    arrangement_faces: int
    arrangement_segments: int
    tested_phase_points: int
    elapsed_seconds: float
    scope: str
    numeric_note: str


def optimize_phase_fixed_orientation(usable: Polygon, spacing_a: float,
                                     spacing_b: float, theta_deg: float, *,
                                     max_boundary_fragments: int = 600,
                                     max_lattice_index_sites: int = 250000,
                                     time_budget_seconds: float | None = None):
    if usable is None or usable.is_empty or not usable.is_valid:
        raise PhaseArrangementError("usable polygon must be non-empty and valid")
    if not all(math.isfinite(x) and x > 0 for x in (spacing_a, spacing_b)):
        raise PhaseArrangementError("spacing values must be finite and positive")
    if not math.isfinite(theta_deg):
        raise PhaseArrangementError("theta must be finite")
    if isinstance(max_boundary_fragments, bool) or not isinstance(max_boundary_fragments, int) or max_boundary_fragments < 1:
        raise PhaseArrangementError("max_boundary_fragments must be a positive integer")
    if isinstance(max_lattice_index_sites, bool) or not isinstance(max_lattice_index_sites, int) or max_lattice_index_sites < 1:
        raise PhaseArrangementError("max_lattice_index_sites must be a positive integer")

    if time_budget_seconds is not None and (not math.isfinite(float(time_budget_seconds)) or float(time_budget_seconds) <= 0):
        raise PhaseArrangementError("time_budget_seconds must be finite and positive")
    started = time.perf_counter()
    def check_time():
        if time_budget_seconds is not None and time.perf_counter() - started >= float(time_budget_seconds):
            raise PhaseArrangementError("phase arrangement time budget exhausted; use grid fallback")
    theta = math.radians(theta_deg % 180.0)
    c, s = math.cos(theta), math.sin(theta)
    minx, miny, maxx, maxy = usable.bounds
    cx, cy = (minx+maxx)/2.0, (miny+maxy)/2.0
    # Inverse of the rectangular lattice basis, expressed as an affine transform.
    lattice_poly = affinity.affine_transform(
        usable,
        [c/spacing_a, s/spacing_a, -s/spacing_b, c/spacing_b,
         -cx*c/spacing_a-cy*s/spacing_a,
         cx*s/spacing_b-cy*c/spacing_b]
    )
    lminx, lminy, lmaxx, lmaxy = lattice_poly.bounds
    j0, j1 = math.floor(lminx)-1, math.ceil(lmaxx)+1
    i0, i1 = math.floor(lminy)-1, math.ceil(lmaxy)+1
    candidate_index_sites = (j1-j0+1) * (i1-i0+1)
    if candidate_index_sites > max_lattice_index_sites:
        raise PhaseArrangementError(
            f"phase arrangement requires {candidate_index_sites:,} lattice index sites, "
            f"exceeding max_lattice_index_sites={max_lattice_index_sites:,}; use grid/adaptive fallback"
        )
    phase_cell = box(0.0, 0.0, 1.0, 1.0)

    boundaries = [phase_cell.boundary]
    isolated_points = set()
    boundary_fragments = 0
    # Only translated polygon-boundary segments can change the phase count.
    # Clipping each segment to the phase square avoids intersecting every
    # translated polygonal interior (the previous method's dominant cost).
    for source_line in _iter_lines(lattice_poly.boundary):
        check_time()
        coords = list(source_line.coords)
        for p0, p1 in zip(coords, coords[1:]):
            check_time()
            x0, y0 = float(p0[0]), float(p0[1])
            x1, y1 = float(p1[0]), float(p1[1])
            sj0 = math.ceil(min(x0, x1) - 1.0)
            sj1 = math.floor(max(x0, x1))
            si0 = math.ceil(min(y0, y1) - 1.0)
            si1 = math.floor(max(y0, y1))
            if sj1 < sj0 or si1 < si0:
                continue
            for j in range(sj0, sj1 + 1):
                for i in range(si0, si1 + 1):
                    seg = LineString([(x0-j, y0-i), (x1-j, y1-i)])
                    clipped = seg.intersection(phase_cell)
                    if clipped.is_empty:
                        continue
                    boundary_fragments += 1
                    boundaries.append(clipped)
                    isolated_points.update(_iter_isolated_points(clipped))
                    if boundary_fragments > max_boundary_fragments:
                        raise PhaseArrangementError(
                            f"boundary arrangement exceeds {max_boundary_fragments} clipped fragments; "
                            "use grid/adaptive fallback for this geometry"
                        )

    linework = unary_union(boundaries)
    faces = list(polygonize(linework))
    phase_points = set()
    # Every open face has constant coverage multiplicity.
    for face in faces:
        check_time()
        rp = face.representative_point()
        if phase_cell.covers(rp):
            phase_points.add((float(rp.x), float(rp.y)))
    # Include every arrangement edge interior and every arrangement vertex to
    # capture maxima under boundary-inclusive covers() semantics.
    segments = 0
    for pt in _iter_points_from_linework(linework):
        check_time()
        if phase_cell.covers(Point(pt)):
            phase_points.add((float(pt[0]), float(pt[1])))
    for pt in isolated_points:
        if phase_cell.covers(Point(pt)):
            phase_points.add(pt)
    for pt in _iter_isolated_points(linework):
        if phase_cell.covers(Point(pt)):
            phase_points.add(pt)
    for line in _iter_lines(linework):
        segments += max(0, len(line.coords)-1)

    if not phase_points:
        phase_points.add((0.5, 0.5))
    # Re-evaluate candidate phases against the original usable polygon rather
    # than only the transformed clips. This avoids losing an inclusive boundary
    # point to a few ulps of affine-transform round-off. Use Shapely 2 vectorized
    # predicates to keep the exact-candidate evaluation practical.
    phase_list = sorted(phase_points)
    pa_all = np.asarray([p[0] for p in phase_list], dtype=float)
    pb_all = np.asarray([p[1] for p in phase_list], dtype=float)
    ii, jj = np.meshgrid(np.arange(i0, i1+1, dtype=float),
                         np.arange(j0, j1+1, dtype=float), indexing="ij")
    ii, jj = ii.ravel(), jj.ravel()
    best_count = -1
    best_phase = (0.0, 0.0)
    for start in range(0, len(phase_list), 128):
        check_time()
        end = min(len(phase_list), start+128)
        pa = pa_all[start:end, None]
        pb = pb_all[start:end, None]
        u = (jj[None, :] + pa) * spacing_a
        v = (ii[None, :] + pb) * spacing_b
        xs = cx + u*c - v*s
        ys = cy + u*s + v*c
        point_array = shapely.points(xs.ravel(), ys.ravel())
        mask = np.asarray(shapely.covers(usable, point_array), dtype=bool).reshape(end-start, -1)
        counts = np.count_nonzero(mask, axis=1)
        for offset, n in enumerate(counts.tolist()):
            phase = phase_list[start+offset]
            if (n, -phase[0], -phase[1]) > (best_count, -best_phase[0], -best_phase[1]):
                best_count, best_phase = n, phase

    result = PhaseArrangementResult(
        status="PHASE_ARRANGEMENT_COMPLETE_NUMERICAL_TOPOLOGY_UNVERIFIED",
        theta_deg=theta_deg % 180.0,
        max_count=best_count,
        best_phase_a=best_phase[0] % 1.0,
        best_phase_b=best_phase[1] % 1.0,
        phase_pieces=boundary_fragments,
        arrangement_faces=len(faces),
        arrangement_segments=segments,
        tested_phase_points=len(phase_points),
        elapsed_seconds=time.perf_counter()-started,
        scope="all phases in [0,1)^2 for one fixed orientation and one rectangular lattice family over the represented usable polygon; does not optimize orientation or arbitrary point placements",
        numeric_note=("Combinatorial arrangement argument covers face/edge/vertex maxima; floating-point topology and predicates are Shapely-dependent and require independent validation before formal exactness claims. "
                      f"Candidate index envelope size={candidate_index_sites}; configured caps are enforced."),
    )
    return asdict(result)
