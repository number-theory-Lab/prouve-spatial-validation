"""Safety/status rules distilled from PATCH-01..PATCH-10; isolated from V0.4."""
from __future__ import annotations
import math


class EngineInputError(ValueError):
    pass


def _nonnegative_int(value, name):
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise EngineInputError(f"{name} must be a non-negative integer")
    return value


def classify_optimality(best_found, upper_bound, has_points, ub_certified, verifier_passed):
    """Conservative status classifier. `upper_bound` must be a certified integer UB."""
    bf = _nonnegative_int(best_found, "best_found")
    ub = _nonnegative_int(upper_bound, "upper_bound")
    if not all(isinstance(x, bool) for x in (has_points, ub_certified, verifier_passed)):
        raise EngineInputError("status flags must be booleans")
    if not has_points:
        return "NO_FEASIBLE_POINTS_IN_ENUMERATED_SEARCH"
    if bf > ub:
        return "BOUND_CONFLICT"
    if bf == 0 and ub == 0:
        return "NO_POSITIVE_SOLUTION"
    if bf == ub and ub > 0:
        if ub_certified and verifier_passed:
            return "OPTIMAL_WITHIN_DECLARED_LATTICE_FAMILY"
        return "EQUALITY_WITHOUT_CERTIFIED_UB_OR_VERIFICATION"
    if bf < ub:
        return "BEST_FOUND_NOT_PROVEN_OPTIMAL"
    return "NO_POSITIVE_SOLUTION"


def conservative_integer_upper_bound(q_upper, *, source_bound_certified: bool):
    """Convert an already-conservative quotient upper bound to integer UB.

    Uses ceil without epsilon subtraction. A floating quotient computed from
    unbounded/uncertified geometry must remain estimate-only.
    """
    if not isinstance(source_bound_certified, bool):
        raise EngineInputError("source_bound_certified must be boolean")
    try:
        q = float(q_upper)
    except (TypeError, ValueError) as exc:
        raise EngineInputError("quotient upper bound must be numeric") from exc
    if not math.isfinite(q) or q < 0:
        raise EngineInputError("quotient upper bound must be finite and non-negative")
    count = math.ceil(q)
    return {
        "upper_bound_count": count,
        "quotient_upper_bound": q,
        "status": "UB_CERTIFIED" if source_bound_certified else "UB_ESTIMATE_ONLY",
        "certified": source_bound_certified,
        "rounding_rule": "ceil(q_upper); no epsilon subtraction",
    }


def compare_verifier_results(result_a: dict, result_b: dict):
    """Return HOLD unless two verifier implementations agree on key outcomes."""
    keys = ("all_checks_passed", "verified_point_count", "status")
    if not isinstance(result_a, dict) or not isinstance(result_b, dict):
        return {"status": "HOLD", "reason": "VERIFIER_RESULT_NOT_OBJECT"}
    differences = {k: (result_a.get(k), result_b.get(k)) for k in keys
                   if result_a.get(k) != result_b.get(k)}
    if differences:
        return {"status": "HOLD", "reason": "VERIFIER_DISAGREEMENT", "differences": differences}
    return {"status": "AGREE", "differences": {}}
