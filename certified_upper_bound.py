#!/usr/bin/env python3
"""Certified area-packing upper bound for 2-D lattice translations/orientations.

The arithmetic core uses exact Fractions over the binary floating-point values
that define the represented polygon vertices and lattice spacings. Square roots
are rounded upward/downward with integer arithmetic; pi is replaced by 355/113
(an established rational upper bound). No GEOS/Shapely area or buffer operation
is used by the bound calculation itself; Shapely is used only to read polygon
rings already produced by the geometry engine.

The certificate is for the ideal Euclidean lattice family with the stated basis
lengths/angle, and for the represented polygon whose vertices are passed in.
It is an upper bound, not a proof that a numerically generated candidate layout
is exactly feasible. A matching lower bound therefore still requires a separate
feasibility certificate before an optimality claim can be issued.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from fractions import Fraction
import math
from typing import Iterable, Sequence

PI_UPPER = Fraction(355, 113)
SQRT_SCALE = 10**12


class CertifiedBoundError(ValueError):
    """Raised when the bound's mathematical assumptions cannot be established."""


def _as_fraction(value: float | int) -> Fraction:
    if isinstance(value, bool):
        raise CertifiedBoundError("boolean is not a valid metric value")
    f = float(value)
    if not math.isfinite(f):
        raise CertifiedBoundError("coordinates and spacings must be finite")
    return Fraction.from_float(f)


def _sqrt_upper(q: Fraction, scale: int = SQRT_SCALE) -> Fraction:
    if q < 0:
        raise CertifiedBoundError("cannot take square root of a negative rational")
    if q == 0:
        return Fraction(0)
    scaled = q * scale * scale
    k = math.isqrt(scaled.numerator // scaled.denominator)
    if k * k * scaled.denominator < scaled.numerator:
        k += 1
    return Fraction(k, scale)


def _sqrt_lower(q: Fraction, scale: int = SQRT_SCALE) -> Fraction:
    if q < 0:
        raise CertifiedBoundError("cannot take square root of a negative rational")
    if q == 0:
        return Fraction(0)
    scaled = q * scale * scale
    k = math.isqrt(scaled.numerator // scaled.denominator)
    while (k + 1) * (k + 1) * scaled.denominator <= scaled.numerator:
        k += 1
    while k * k * scaled.denominator > scaled.numerator:
        k -= 1
    return Fraction(k, scale)


def _iter_polygon_rings(geom) -> Iterable[Sequence[tuple[float, float]]]:
    if geom is None or geom.is_empty:
        return
    gtype = geom.geom_type
    if gtype == "Polygon":
        yield geom.exterior.coords
        for ring in geom.interiors:
            yield ring.coords
    elif hasattr(geom, "geoms"):
        for child in geom.geoms:
            yield from _iter_polygon_rings(child)


def _extract_exact_points(geom) -> list[tuple[Fraction, Fraction]]:
    pts: set[tuple[Fraction, Fraction]] = set()
    for ring in _iter_polygon_rings(geom):
        for coord in ring:
            if len(coord) < 2:
                continue
            x = _as_fraction(coord[0])
            y = _as_fraction(coord[1])
            pts.add((x, y))
    if not pts:
        raise CertifiedBoundError("non-empty polygonal geometry has no polygon vertices")
    return sorted(pts)


def _cross(o, a, b) -> Fraction:
    return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])


def _convex_hull(points: list[tuple[Fraction, Fraction]]) -> list[tuple[Fraction, Fraction]]:
    if len(points) <= 1:
        return points
    lower: list[tuple[Fraction, Fraction]] = []
    for p in points:
        while len(lower) >= 2 and _cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)
    upper: list[tuple[Fraction, Fraction]] = []
    for p in reversed(points):
        while len(upper) >= 2 and _cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)
    hull = lower[:-1] + upper[:-1]
    if len(hull) < 3:
        raise CertifiedBoundError("polygonal convex hull is degenerate")
    return hull


def _hull_area_and_perimeter_upper(hull: list[tuple[Fraction, Fraction]]) -> tuple[Fraction, Fraction]:
    twice_area = Fraction(0)
    perimeter_upper = Fraction(0)
    for idx, p in enumerate(hull):
        q = hull[(idx + 1) % len(hull)]
        twice_area += p[0] * q[1] - q[0] * p[1]
        dx, dy = q[0] - p[0], q[1] - p[1]
        perimeter_upper += _sqrt_upper(dx * dx + dy * dy)
    area = abs(twice_area) / 2
    if area <= 0:
        raise CertifiedBoundError("convex hull area is not positive")
    return area, perimeter_upper


@dataclass(frozen=True)
class CertifiedUpperBoundResult:
    upper_bound_count: int
    certified: bool
    status: str
    area_upper_bound_m2: float
    cell_area_lower_bound_m2: float
    quotient_upper_bound: float
    hull_area_m2: float
    hull_perimeter_upper_m: float
    cell_covering_radius_upper_m: float
    hull_vertex_count: int
    arithmetic: str
    proof_scope: str
    proof_outline: str
    exact_area_upper_fraction: str
    exact_cell_area_lower_fraction: str
    exact_quotient_fraction: str


def certified_lattice_upper_bound(usable, spec) -> dict:
    """Return a mathematically conservative integer UB for a 2-D lattice.

    For each accepted lattice point, take its centered fundamental
    parallelogram. Such cells tile the plane (overlap only on zero-area
    boundaries), have area equal to the lattice determinant, and are contained
    in a disk of radius R around the lattice point. Since every accepted point
    is in U, all these cells lie in conv(U) expanded by radius R. The Steiner
    formula gives area(conv(U) (+) disk(R)) = A + P*R + pi*R^2 for convex U.
    Upper/lower rational enclosures yield an exact integer upper bound.
    """
    if usable is None:
        raise CertifiedBoundError("usable geometry is required")
    if usable.is_empty:
        return asdict(CertifiedUpperBoundResult(
            upper_bound_count=0, certified=True, status="CERTIFIED_EMPTY_SET_ZERO",
            area_upper_bound_m2=0.0, cell_area_lower_bound_m2=float(spec.cell_area),
            quotient_upper_bound=0.0, hull_area_m2=0.0,
            hull_perimeter_upper_m=0.0, cell_covering_radius_upper_m=0.0,
            hull_vertex_count=0, arithmetic="exact rational arithmetic over binary-float inputs",
            proof_scope="represented empty polygonal feasible set; any lattice has zero accepted points",
            proof_outline="U is empty, hence N=0 for every orientation and translation.",
            exact_area_upper_fraction="0/1", exact_cell_area_lower_fraction="not_required_empty_set",
            exact_quotient_fraction="0/1"))
    if not usable.is_valid:
        raise CertifiedBoundError("usable geometry must be valid before certification")

    a = _as_fraction(spec.a_length)
    b = _as_fraction(spec.b_length)
    if a <= 0 or b <= 0:
        raise CertifiedBoundError("lattice basis lengths must be positive")
    gamma = float(spec.gamma_deg)
    if gamma == 90.0:
        cell_area_lower = a * b
        radius_upper = _sqrt_upper((a * a + b * b) / 4)
    elif gamma == 60.0:
        sqrt3_lower = _sqrt_lower(Fraction(3, 1))
        cell_area_lower = a * b * sqrt3_lower / 2
        # Maximum diagonal of the centered 60-degree fundamental cell.
        radius_upper = _sqrt_upper((a * a + b * b + a * b) / 4)
    else:
        # For other basis angles, use the universal triangle-inequality radius
        # and a conservative determinant lower bound is not available here.
        raise CertifiedBoundError("only 60-degree and 90-degree lattice families are currently certified")
    if cell_area_lower <= 0:
        raise CertifiedBoundError("cell area lower bound must be positive")

    points = _extract_exact_points(usable)
    hull = _convex_hull(points)
    hull_area, hull_perimeter_upper = _hull_area_and_perimeter_upper(hull)
    area_upper = hull_area + hull_perimeter_upper * radius_upper + PI_UPPER * radius_upper * radius_upper
    quotient_upper = area_upper / cell_area_lower
    integer_upper = quotient_upper.numerator // quotient_upper.denominator

    return asdict(CertifiedUpperBoundResult(
        upper_bound_count=int(integer_upper), certified=True,
        status="CERTIFIED_RATIONAL_STEINER_ENCLOSURE",
        area_upper_bound_m2=float(area_upper),
        cell_area_lower_bound_m2=float(cell_area_lower),
        quotient_upper_bound=float(quotient_upper),
        hull_area_m2=float(hull_area),
        hull_perimeter_upper_m=float(hull_perimeter_upper),
        cell_covering_radius_upper_m=float(radius_upper),
        hull_vertex_count=len(hull),
        arithmetic="exact rational arithmetic over exact binary-float coordinate/spacing values; sqrt bounds use integer arithmetic at 1e-12 m; pi upper bound 355/113",
        proof_scope="all translations and orientations in the declared Euclidean 2-D lattice family, with lattice centers in the represented valid polygonal usable geometry; not arbitrary point placement",
        proof_outline=(
            "Centered fundamental cells of accepted lattice points are disjoint up to boundaries, "
            "each has area at least cell_area_lower_bound, and each lies in the radius-R "
            "parallel body of conv(U). Steiner's formula bounds that body's area by "
            "A_hull + P_hull*R + pi*R^2. All irrational terms are conservatively enclosed "
            "with rational bounds. Therefore N <= floor(area_upper/cell_area_lower)."
        ),
        exact_area_upper_fraction=f"{area_upper.numerator}/{area_upper.denominator}",
        exact_cell_area_lower_fraction=f"{cell_area_lower.numerator}/{cell_area_lower.denominator}",
        exact_quotient_fraction=f"{quotient_upper.numerator}/{quotient_upper.denominator}"
    ))
