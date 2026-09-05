"""Spending controls and constraint scoring.

These cover the claims the README makes about governance: caps hold, approval
escalates, duplicates are refused, and options are rejected for the specific
reason a reviewer will be shown.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import policy, scoring, templates  # noqa: E402

CAPS = {"envelope": "80000", "approval_threshold": "10000",
        "per_category": {"venue": "50000", "av": "15000"}}


def _ledger():
    return policy.Ledger(CAPS)


def test_category_cap_reported_before_envelope_cap():
    """When both are broken, the category rule is the more useful explanation.

    'More than we spend on venues' states a policy; 'running low' only describes
    a balance.
    """
    led = _ledger()
    v = led.check(amount="60000", category="venue", item_id="x")
    assert not v["allowed"]
    assert v["rule"] == "venue_cap"


def test_envelope_cap_applies_where_no_category_cap_exists():
    led = _ledger()
    v = led.check(amount="90000", category="misc", item_id="x")
    assert not v["allowed"] and v["rule"] == "envelope_cap"


def test_approval_escalates_above_threshold_without_blocking():
    led = _ledger()
    v = led.check(amount="42000", category="venue", item_id="x")
    assert v["allowed"] and v["needs_approval"]
    assert "auto-approve" in v["reason"]


def test_small_spend_is_autonomous():
    led = _ledger()
    v = led.check(amount="900", category="av", item_id="x")
    assert v["allowed"] and not v["needs_approval"]


def test_duplicate_purchase_guard():
    led = _ledger()
    led.commit(amount="1000", category="av", item_id="av_a")
    v = led.check(amount="1000", category="av", item_id="av_a")
    assert not v["allowed"] and v["rule"] == "duplicate_purchase_guard"


def test_spend_accumulates_within_a_category():
    led = _ledger()
    led.commit(amount="14000", category="av", item_id="a")
    v = led.check(amount="2000", category="av", item_id="b")
    assert not v["allowed"], "14k + 2k exceeds the 15k av cap"


# --- constraint scoring ---------------------------------------------------

def _opt(**attrs):
    return {"id": "o", "supplier": "S", "price": attrs.pop("price", "1000"),
            "reliability": 0.9, "attributes": attrs}


def test_capacity_floor_rejects_a_too_small_option():
    ok, fails = scoring.check_constraints(_opt(capacity=900), {"min_capacity": 1000})
    assert not ok and "below the required" in fails[0]


def test_missing_capability_rejects_the_option():
    """The venue rejected for inaccessible transport — the key demo frame."""
    ok, fails = scoring.check_constraints(
        _opt(public_transport=False), {"requires_public_transport": True})
    assert not ok and "public transport not available" in fails[0]


def test_price_ceiling_reads_the_option_price():
    ok, _ = scoring.check_constraints(_opt(price="60000"), {"max_price": 50000})
    assert not ok


def test_eligible_option_passes_every_constraint():
    ok, fails = scoring.check_constraints(
        _opt(capacity=1200, public_transport=True, av_support=True, price="42000"),
        {"min_capacity": 1000, "requires_public_transport": True,
         "requires_av_support": True, "max_price": 50000})
    assert ok and fails == []


def test_unresolved_slots_are_skipped_not_failed():
    """An unfilled template slot must not silently disqualify everything."""
    ok, _ = scoring.check_constraints(_opt(capacity=1200),
                                      {"min_capacity": "{profile.constraints.missing}"})
    assert ok


def test_ineligible_options_are_ranked_but_retained():
    tpl = templates.load("event-contingency")
    opts = [_opt(capacity=1200, price="42000"), {**_opt(capacity=900, price="28000"),
                                                 "id": "small"}]
    ranked = scoring.rank(opts, step={"constraints": {"min_capacity": 1000}},
                          template=tpl, profile={"preferences": {}}, cap=50000)
    assert len(ranked) == 2, "rejected options stay visible with their reason"
    assert ranked[0]["eligible"] and not ranked[-1]["eligible"]
