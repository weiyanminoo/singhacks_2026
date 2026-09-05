"""Plan comparison and selection.

The load-bearing test is `test_cheapest_plan_can_still_lose`: an agent that
merely minimises cost is not making a decision, it is sorting. Rejecting a
cheaper plan because a hard constraint forbids it is the behaviour worth
protecting.
"""
import sys
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import plans, profiles, templates  # noqa: E402

TPL = templates.load("event-contingency")
PROFILE = profiles.load("organizer-01")

ESTIMATES = {"relocate": {
    "replacement_venue": {"price": 42000, "reliability": 0.95},
    "av": {"price": 13000, "reliability": 0.94},
    "catering": {"price": 11000, "reliability": 0.93},
    "transport": {"price": 9000, "reliability": 0.60},
}}


def _evaluate(estimates=None, profile=None):
    return plans.evaluate(TPL, profile or PROFILE, estimates or ESTIMATES)


def _by_id(evaluated, plan_id):
    return next(p for p in evaluated if p["id"] == plan_id)


def test_cheapest_plan_can_still_lose():
    """Postpone is cheapest and must still be rejected: the deadline is fixed."""
    ev = _evaluate()
    postpone, relocate = _by_id(ev, "postpone"), _by_id(ev, "relocate")

    assert postpone["total"] < relocate["total"], "postpone should be the cheaper plan"
    assert not postpone["feasible"]
    assert "moves the date" in " ".join(postpone["rejected_because"])

    chosen, _ = plans.select(ev)
    assert chosen["id"] == "relocate"


def test_deadline_constraint_can_be_relaxed():
    """Feasibility comes from the profile, not from the plan id."""
    relaxed = {**PROFILE, "constraints": {**PROFILE["constraints"], "deadline_fixed": False}}
    chosen, _ = plans.select(_evaluate(profile=relaxed))
    assert chosen["id"] == "postpone", "with a movable date, the cheapest plan wins"


def test_budget_checks_cash_not_risk():
    """The budget is a cash ceiling. Risk weighting must not be charged against it.

    Regression: charging expected risk against the cash cap rejected a plan whose
    actual commitment was S$75,000 against an S$80,000 budget.
    """
    relocate = _by_id(_evaluate(), "relocate")
    assert relocate["costs"]["direct_recovery"] == Decimal("75000")
    assert relocate["costs"]["total_expected_cost"] > Decimal("80000")
    assert relocate["feasible"], "cash spend is within budget, so the plan is affordable"


def test_budget_rejects_genuinely_unaffordable_plan():
    over = {"relocate": {"replacement_venue": {"price": 95000, "reliability": 1.0}}}
    relocate = _by_id(_evaluate(estimates=over), "relocate")
    assert not relocate["feasible"]
    assert "exceeds" in " ".join(relocate["rejected_because"])


def test_unreliable_supplier_costs_more_than_its_price():
    """Risk weighting makes a cheap unreliable option honestly more expensive."""
    cheap_flaky = plans.cost_of({"costs": {}}, step_estimates={
        "x": {"price": 10000, "reliability": 0.5}}, terms=TPL.get("cost_terms"))
    dearer_solid = plans.cost_of({"costs": {}}, step_estimates={
        "x": {"price": 12000, "reliability": 1.0}}, terms=TPL.get("cost_terms"))
    assert cheap_flaky["total_expected_cost"] > dearer_solid["total_expected_cost"]


def test_cost_terms_come_from_the_template():
    """Refund/delay classification is domain data, not engine knowledge."""
    plan = {"costs": {"attendee_refunds": 100, "venue_penalty": 50}}
    with_terms = plans.cost_of(plan, terms=TPL["cost_terms"])
    assert with_terms["expected_refunds"] == Decimal("100")
    assert with_terms["direct_recovery"] == Decimal("50")

    without = plans.cost_of(plan, terms=None)
    assert without["expected_refunds"] == Decimal("0")
    assert without["direct_recovery"] == Decimal("150")


def test_avoided_loss_measured_against_a_feasible_alternative():
    """Comparing against an infeasible plan would flatter the number."""
    ev = _evaluate()
    chosen, avoided = plans.select(ev)
    assert avoided["versus"] == "cancel"
    assert _by_id(ev, avoided["versus"])["feasible"]
    assert avoided["avoided_loss"] == _by_id(ev, "cancel")["total"] - chosen["total"]


def test_rejected_plans_are_kept_not_dropped():
    ev = _evaluate()
    assert len(ev) == len(TPL["plans"]), "every plan must remain visible with its reason"
    assert any(not p["feasible"] for p in ev)
