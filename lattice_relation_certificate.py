#!/usr/bin/env python3
"""Exact rational description and verifier for a single rectangular lattice plan.

A rational parametrization of a rotation is used so the basis remains exactly
orthogonal in rational arithmetic: cos=(1-q^2)/(1+q^2), sin=2q/(1+q^2).
q is the canonical decimal rational approximation to tan(theta/2). This creates
an exact rational lattice whose angle is close to the engine's floating angle.
Exact point coordinates are stored as fraction strings; decimal values are
presentation-only and must be re-certified if re-rounded for deployment.
"""
from __future__ import annotations
from fractions import Fraction
import json
import math
from numbers import Integral
from typing import Any

from formal_feasibility_certificate import CertificateInputError, _q


def _frac_text(x: Fraction) -> str:
    return f"{x.numerator}/{x.denominator}"


def _decimal_approx(x: Fraction, places: int = 12) -> float:
    return round(x.numerator / x.denominator, places)


def _strict_index(value: Any, label: str) -> int:
    """Accept an actual integer index; never truncate floats or booleans."""
    if isinstance(value, bool) or not isinstance(value, Integral):
        raise CertificateInputError(f"{label}: lattice index must be an integer, not a coerced value")
    return int(value)


def _strict_positive_integer(value: Any, label: str) -> int:
    out = _strict_index(value, label)
    if out <= 0:
        raise CertificateInputError(f"{label}: must be a positive integer")
    return out


def build_rational_lattice_plan(best_layout: dict, spacing_a: Any, spacing_b: Any,
                                theta_deg: Any, plants_per_hole: int = 1) -> tuple[list[dict], dict]:
    theta = float(theta_deg)
    if not math.isfinite(theta):
        raise CertificateInputError("theta_deg must be finite")
    half_tan = math.tan(math.radians(theta % 180.0) / 2.0)
    q = _q(half_tan, "rational_rotation_parameter")
    a_len = _q(spacing_a, "spacing_a")
    b_len = _q(spacing_b, "spacing_b")
    def canonical_phase(value, label):
        raw = _q(value, label)
        simple = raw.limit_denominator(100000)
        # Snap only when the rational simplification is extremely close. The
        # resulting exact candidate is still re-verified against source geometry.
        if abs(float(raw - simple)) <= 1e-9:
            return simple
        return raw
    pa = canonical_phase(best_layout["phase_a"], "phase_a")
    pb = canonical_phase(best_layout["phase_b"], "phase_b")
    if a_len <= 0 or b_len <= 0 or not (0 <= pa < 1) or not (0 <= pb < 1):
        raise CertificateInputError("invalid lattice lengths or phase")
    cos_q = (1 - q*q) / (1 + q*q)
    sin_q = (2*q) / (1 + q*q)
    ax, ay = a_len*cos_q, a_len*sin_q
    bx, by = -b_len*sin_q, b_len*cos_q
    try:
        indices_i = [_strict_index(v, f"accepted_i[{idx}]") for idx, v in enumerate(best_layout["accepted_i"])]
        indices_j = [_strict_index(v, f"accepted_j[{idx}]") for idx, v in enumerate(best_layout["accepted_j"])]
        plants_per_hole = _strict_positive_integer(plants_per_hole, "plants_per_hole")
    except (KeyError, TypeError) as exc:
        raise CertificateInputError("best layout must include integer accepted_i/accepted_j arrays") from exc
    if len(indices_i) != len(indices_j):
        raise CertificateInputError("lattice index arrays have inconsistent length")
    if not indices_i:
        raise CertificateInputError("empty lattice plan cannot receive a lattice relation certificate")
    points = []
    ordered = sorted(zip(indices_i, indices_j))
    seen = set()
    for k, (i, j) in enumerate(ordered, start=1):
        if (i, j) in seen:
            raise CertificateInputError("duplicate lattice index pair")
        seen.add((i, j))
        u, v = Fraction(j, 1) + pa, Fraction(i, 1) + pb
        x, y = u*ax + v*bx, u*ay + v*by
        points.append({
            "plant_id": f"V03-P{k:05d}",
            "lattice_i": i,
            "lattice_j": j,
            "x_m": _frac_text(x),
            "y_m": _frac_text(y),
            "x_m_display": _decimal_approx(x),
            "y_m_display": _decimal_approx(y),
            "plants_in_hole": plants_per_hole,
        })
    metadata = {
        "schema": "prouve-rational-rectangular-lattice-v0.1",
        "basis_family": "rectangular_orthogonal",
        "theta_source_deg_display_only": theta,
        "rotation_parameter_q": _frac_text(q),
        "rotation_cos": _frac_text(cos_q),
        "rotation_sin": _frac_text(sin_q),
        "basis_a": {"x":_frac_text(ax), "y":_frac_text(ay)},
        "basis_b": {"x":_frac_text(bx), "y":_frac_text(by)},
        "spacing_a_m": _frac_text(a_len),
        "spacing_b_m": _frac_text(b_len),
        "phase_a": _frac_text(pa),
        "phase_b": _frac_text(pb),
        "origin_xy_m": ["0/1", "0/1"],
        "point_count": len(points),
        "coordinate_representation": "exact fractions in x_m/y_m; x_m_display/y_m_display are presentation-only",
        "angle_note": "The certified orientation is the exact rational rotation induced by q, which approximates theta_source_deg_display_only; it is not asserted to be mathematically identical to the floating search angle.",
    }
    return points, metadata


def verify_rational_lattice_relation(points: list[dict], metadata: dict) -> dict:
    """Independently verify the declared exact rectangular lattice relation.

    Invalid metadata, coerced/non-integral indices, non-positive spacings, or
    inconsistent rational-rotation fields produce HOLD rather than a pass.
    """
    failures = []
    try:
        if not isinstance(points, list) or not points:
            raise CertificateInputError("points must be a non-empty list")
        if not isinstance(metadata, dict):
            raise CertificateInputError("lattice metadata must be an object")
        ax = _q(metadata["basis_a"]["x"], "basis_a.x")
        ay = _q(metadata["basis_a"]["y"], "basis_a.y")
        bx = _q(metadata["basis_b"]["x"], "basis_b.x")
        by = _q(metadata["basis_b"]["y"], "basis_b.y")
        a_len = _q(metadata["spacing_a_m"], "spacing_a_m")
        b_len = _q(metadata["spacing_b_m"], "spacing_b_m")
        pa = _q(metadata["phase_a"], "phase_a")
        pb = _q(metadata["phase_b"], "phase_b")
        q = _q(metadata["rotation_parameter_q"], "rotation_parameter_q")
        cos_q = _q(metadata["rotation_cos"], "rotation_cos")
        sin_q = _q(metadata["rotation_sin"], "rotation_sin")
    except (KeyError, TypeError, CertificateInputError) as exc:
        return {"status":"HOLD_INVALID_LATTICE_METADATA", "certified":False, "reason":str(exc), "failures":[]}

    if a_len <= 0 or b_len <= 0:
        failures.append({"reason":"NON_POSITIVE_BASIS_LENGTH"})
    if not (0 <= pa < 1 and 0 <= pb < 1):
        failures.append({"reason":"PHASE_OUTSIDE_UNIT_INTERVAL"})

    expected_cos = (1 - q*q) / (1 + q*q)
    expected_sin = (2*q) / (1 + q*q)
    rotation_fields_ok = cos_q == expected_cos and sin_q == expected_sin
    basis_fields_ok = (ax == a_len*cos_q and ay == a_len*sin_q and
                       bx == -b_len*sin_q and by == b_len*cos_q)
    orthogonal = ax*bx + ay*by == 0
    a_length_ok = a_len > 0 and ax*ax + ay*ay == a_len*a_len
    b_length_ok = b_len > 0 and bx*bx + by*by == b_len*b_len
    if not rotation_fields_ok:
        failures.append({"reason":"ROTATION_PARAMETER_FIELDS_INCONSISTENT"})
    if not basis_fields_ok:
        failures.append({"reason":"BASIS_DOES_NOT_MATCH_DECLARED_RATIONAL_ROTATION"})
    if not orthogonal:
        failures.append({"reason":"BASIS_NOT_ORTHOGONAL"})
    if not a_length_ok or not b_length_ok:
        failures.append({"reason":"BASIS_LENGTH_MISMATCH"})

    indices = set()
    coords = set()
    for idx, point in enumerate(points):
        if not isinstance(point, dict):
            failures.append({"point_index":idx, "reason":"INVALID_POINT_RECORD"})
            continue
        try:
            i = _strict_index(point.get("lattice_i"), f"point[{idx}].lattice_i")
            j = _strict_index(point.get("lattice_j"), f"point[{idx}].lattice_j")
            x, y = _q(point["x_m"], "x_m"), _q(point["y_m"], "y_m")
        except (KeyError, TypeError, CertificateInputError) as exc:
            failures.append({"plant_id":point.get("plant_id"), "reason":f"INVALID_POINT_RECORD: {exc}"})
            continue
        if (i,j) in indices:
            failures.append({"plant_id":point.get("plant_id"), "reason":"DUPLICATE_LATTICE_INDEX"})
        indices.add((i,j))
        u, v = Fraction(j,1)+pa, Fraction(i,1)+pb
        expected_x, expected_y = u*ax + v*bx, u*ay + v*by
        if (x,y) != (expected_x,expected_y):
            failures.append({"plant_id":point.get("plant_id"), "reason":"COORDINATE_NOT_ON_DECLARED_RATIONAL_LATTICE"})
        if (x,y) in coords:
            failures.append({"plant_id":point.get("plant_id"), "reason":"DUPLICATE_COORDINATE"})
        coords.add((x,y))

    passed = (a_len > 0 and b_len > 0 and 0 <= pa < 1 and 0 <= pb < 1 and
              rotation_fields_ok and basis_fields_ok and orthogonal and
              a_length_ok and b_length_ok and len(failures)==0 and
              len(indices)==len(points) and len(points)>0)
    min_spacing_lower_bound = min(a_len, b_len) if a_len > 0 and b_len > 0 else None
    return {
        "schema":"prouve-rational-lattice-relation-certificate-v0.2",
        "status":"CERTIFIED_RATIONAL_LATTICE" if passed else "HOLD_LATTICE_RELATION_FAILED",
        "certified":passed,
        "point_count":len(points),
        "orthogonal_basis_exact":orthogonal,
        "basis_a_length_exact":a_length_ok,
        "basis_b_length_exact":b_length_ok,
        "rational_rotation_fields_consistent":rotation_fields_ok,
        "basis_matches_declared_rotation":basis_fields_ok,
        "phase_values_valid":0 <= pa < 1 and 0 <= pb < 1,
        "unique_index_pairs":len(indices)==len(points),
        "minimum_pairwise_spacing_lower_bound_m":None if min_spacing_lower_bound is None else _frac_text(min_spacing_lower_bound),
        "pairwise_spacing_property_certified":passed and len(indices)==len(points),
        "spacing_proof":"For distinct integer index pairs, exact orthogonality gives squared separation m^2*a^2+n^2*b^2, hence at least min(a,b)^2 for strictly positive basis lengths.",
        "failures":failures,
        "arithmetic":"exact rational arithmetic",
        "limitations":["This certifies membership in the declared rational orthogonal lattice, not CRS correctness or field feasibility."]
    }

