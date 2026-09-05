"""Deterministic constraint scoring.

The LLM never does arithmetic and never decides whether a constraint holds. It
plans and it explains; Python scores. That is what makes the recorded demo run
reproducible instead of a coin flip (D-003).

Every score carries a `breakdown` so the UI can say *why* — a number nobody can
explain is worse than no number.
"""
from __future__ import annotations


def _num(v, default=0.0) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def _coerce(a, b):
    """Compare as datetimes when both parse, else numbers, else strings.

    Datetimes must be parsed, not string-compared: our times carry different UTC
    offsets (+08:00 departure, +07:00 arrival), and lexicographic order on ISO
    strings with mixed offsets is simply wrong.
    """
    da, db = _dt(a), _dt(b)
    if da and db:
        return da, db
    na, nb = _num(a, None), _num(b, None)
    if na is not None and nb is not None:
        return na, nb
    return str(a), str(b)


def _dt(v):
    from datetime import datetime
    try:
        return datetime.fromisoformat(str(v))
    except (TypeError, ValueError):
        return None


def check_constraints(option: dict, constraints: dict) -> tuple[bool, list[str]]:
    """Hard constraints. A miss disqualifies the option; it is not a penalty.

    Three generic forms, all resolved against the option's attributes:
        <attr>_before   attribute must be earlier / less than the value
        <attr>_after    attribute must be later / greater than the value
        max_<attr>      attribute must not exceed the value

    The engine does not know what any attribute *means* — that is what keeps it
    domain-neutral (D-015).
    """
    attrs = option.get("attributes", {})
    failures = []
    for key, want in (constraints or {}).items():
        if want is None or str(want).startswith("{"):
            continue                                  # unresolved slot: skip
        if key.endswith("_before"):
            field = key[: -len("_before")]
            got = attrs.get(field)
            if got is not None:
                a, b = _coerce(got, want)
                if a > b:
                    failures.append(f"{field} {got} is after {want}")
        elif key.endswith("_after"):
            field = key[: -len("_after")]
            got = attrs.get(field)
            if got is not None:
                a, b = _coerce(got, want)
                if a < b:
                    failures.append(f"{field} {got} is before {want}")
        elif key.startswith("max_"):
            field = key[4:]
            got = attrs.get(field) if field != "price" else option.get("price")
            if got is not None and _num(got) > _num(want):
                failures.append(f"{field} {got} exceeds {want}")
        elif key.startswith("min_"):
            field = key[4:]
            got = attrs.get(field)
            if got is not None and _num(got) < _num(want):
                failures.append(f"{field} {got} is below the required {want}")
        elif key.startswith("requires_"):
            # Boolean capability: the option must advertise it as true.
            field = key[len("requires_"):]
            if str(want).lower() in ("true", "1", "yes"):
                if not attrs.get(field):
                    failures.append(f"{field.replace('_', ' ')} not available")
    return (not failures), failures


def score(option: dict, *, step: dict, template: dict, profile: dict, cap: float) -> dict:
    """Score one option in [0,1] with an explainable breakdown."""
    weights = template["scoring"]["weights"]
    bonuses = template["scoring"].get("preference_bonus", {})
    prefs = profile.get("preferences", {})
    supplier = option.get("supplier", "")

    ok, failures = check_constraints(option, step.get("constraints", {}))

    price = _num(option.get("price"))
    cost_score = max(0.0, 1.0 - (price / cap)) if cap else 0.0
    reliability = _num(option.get("reliability"), 0.5)
    fit = 1.0 if ok else 0.0

    base = (
        weights.get("constraint_fit", 0) * fit
        + weights.get("cost", 0) * cost_score
        + weights.get("reliability", 0) * reliability
    )

    adjustments = []
    if supplier in prefs.get("preferred_suppliers", []):
        b = bonuses.get("preferred_suppliers", 0)
        base += b
        adjustments.append((f"preferred supplier {supplier}", b))
    if supplier in prefs.get("avoid_suppliers", []):
        b = bonuses.get("avoid_suppliers", 0)
        base += b
        adjustments.append((f"profile avoids {supplier}", b))
    for h in profile.get("history", []):
        if h.get("chose") == supplier:
            b = bonuses.get("repeat_choice_in_history", 0)
            base += b
            adjustments.append((f"chosen before ({h.get('because','')})", b))
            break

    return {
        "option": option,
        "score": round(max(0.0, min(1.0, base)), 4),
        "eligible": ok,
        "failures": failures,
        "breakdown": {
            "constraint_fit": round(fit, 3),
            "cost": round(cost_score, 3),
            "reliability": round(reliability, 3),
            "adjustments": adjustments,
        },
    }


def rank(options: list[dict], **kw) -> list[dict]:
    """Score every option, best first. Ineligible ones are kept, not dropped —
    showing a rejected option with its reason is the point."""
    scored = [score(o, **kw) for o in options]
    return sorted(scored, key=lambda s: (s["eligible"], s["score"]), reverse=True)
