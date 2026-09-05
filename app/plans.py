"""Plan comparison — the layer above steps (D-018).

The engine picks the best *option per step*. This picks the best *plan* first:
cancel, postpone or relocate. Only the winning plan's steps are executed.

Two rules, in this order, because they answer different questions:

1. **Feasibility.** Does the plan violate a hard organizer constraint? A plan
   that breaks the deadline is not "expensive", it is *not available*, however
   cheap it looks. This is why postpone loses here despite costing less than
   relocate — the organizer's constraints say the date is fixed.
2. **Expected cost.** Among feasible plans, lowest total expected cost wins.

        total_expected_cost = direct_recovery
                            + expected_refunds
                            + supplier_failure_risk
                            + expected_delay_penalty

Everything is deterministic. The LLM narrates the result; it never computes it.
"""
from __future__ import annotations

from decimal import Decimal

# The four terms are the model. WHICH cost component feeds which term is domain
# knowledge, so the template declares it (`cost_terms:`) and the engine reads it.
DEFAULT_TERMS: dict[str, tuple] = {"expected_refunds": (), "expected_delay_penalty": ()}


def _d(v) -> Decimal:
    return Decimal(str(v or 0))


def feasibility(plan: dict, profile: dict) -> tuple[bool, list[str]]:
    """Hard constraints at the plan level. Returns (feasible, reasons_against)."""
    cons = profile.get("constraints", {})
    eff = plan.get("effects", {})
    against = []

    if cons.get("deadline_fixed") and eff.get("preserves_deadline") is False:
        against.append(
            f"organizer requires the event to stay within "
            f"{cons.get('deadline_hours', '?')}h; this plan moves the date"
        )
    if cons.get("event_must_proceed") and eff.get("preserves_event") is False:
        against.append("organizer requires the event to go ahead")
    return (not against), against


def cost_of(plan: dict, *, step_estimates: dict[str, dict] | None = None,
            terms: dict | None = None) -> dict:
    """Total expected cost, broken into the four terms of the model.

    A plan with explicit `costs` uses them. A plan with `steps` derives its cost
    from what those steps would actually buy — passed in as `step_estimates`,
    keyed by step id, each `{"price": ..., "reliability": ...}`.
    """
    direct = refunds = delay = risk = Decimal("0")

    t = {**DEFAULT_TERMS, **(terms or {})}
    refund_keys = set(t.get("expected_refunds") or ())
    delay_keys = set(t.get("expected_delay_penalty") or ())
    for key, val in (plan.get("costs") or {}).items():
        amt = _d(val)
        if key in refund_keys:
            refunds += amt
        elif key in delay_keys:
            delay += amt
        else:
            direct += amt

    for est in (step_estimates or {}).values():
        price = _d(est.get("price"))
        direct += price
        # A supplier that fails costs you the payment and the scramble to replace
        # it. Weighting by (1 - reliability) makes an unreliable cheap option
        # honestly more expensive than its sticker price.
        risk += price * (Decimal("1") - _d(est.get("reliability", 1)))

    total = direct + refunds + risk + delay
    return {
        "direct_recovery": direct,
        "expected_refunds": refunds,
        "supplier_failure_risk": risk,
        "expected_delay_penalty": delay,
        "total_expected_cost": total,
    }


def evaluate(template: dict, profile: dict,
             step_estimates: dict[str, dict[str, dict]] | None = None) -> list[dict]:
    """Score every plan. Returns them ordered: feasible first, cheapest first.

    Infeasible plans are kept, never dropped — showing what was rejected and why
    is the evidence that a decision was made rather than a default taken.
    """
    budget = _d(template["caps"]["envelope"])
    out = []
    for plan in template["plans"]:
        ok, against = feasibility(plan, profile)
        costs = cost_of(plan, step_estimates=(step_estimates or {}).get(plan["id"]),
                        terms=template.get("cost_terms"))

        # Budget feasibility is checked against DIRECT cash spend, not against
        # total expected cost. The S$80,000 contingency budget is a cash ceiling
        # — you cannot commit more than that. Supplier-failure risk is an
        # expected-value adjustment used for *ranking*; it is not money leaving
        # the account, and charging it against the cash cap wrongly rejects
        # plans the organizer can actually afford.
        if ok and plan.get("steps") and costs["direct_recovery"] > budget:
            ok = False
            against.append(
                f"S${costs['direct_recovery']:,.0f} of committed spend exceeds the "
                f"S${budget:,.0f} contingency budget"
            )

        out.append({
            "plan": plan,
            "id": plan["id"],
            "label": plan.get("label", plan["id"]),
            "feasible": ok,
            "rejected_because": against,
            "costs": costs,
            "total": costs["total_expected_cost"],
        })

    out.sort(key=lambda p: (not p["feasible"], p["total"]))
    return out


def select(evaluated: list[dict]) -> tuple[dict | None, dict]:
    """Cheapest feasible plan, plus the avoided loss it justifies.

    Avoided loss is measured against the most expensive *feasible* alternative —
    what the organizer would have been forced into otherwise. Comparing against
    an infeasible plan would flatter the number.
    """
    feasible = [p for p in evaluated if p["feasible"]]
    if not feasible:
        return None, {"avoided_loss": Decimal("0"), "versus": None}
    chosen = feasible[0]
    worst = max(feasible, key=lambda p: p["total"])
    return chosen, {
        "avoided_loss": worst["total"] - chosen["total"],
        "versus": worst["id"],
    }
